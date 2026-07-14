# -*- coding: utf-8 -*-
"""
SAT Math Mock — Telegram bot
=============================
Foydalanuvchilar ro'yxatdan o'tadi (ism-familiya), keyin istalgan mockni
tanlab, Module 1 va Module 2 javoblarini yuboradi. Bot ularni avtomatik
tekshirib, taxminiy 200-800 ball va xato savollar ro'yxatini qaytaradi.
Admin barcha ro'yxatdan o'tganlar va natijalarni ko'ra oladi.

Ishga tushirish:
    pip install -r requirements.txt
    export BOT_TOKEN="123456:ABC-DEF..."
    export ADMIN_IDS="111111111,222222222"
    python bot.py
"""

import asyncio
import io
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    BufferedInputFile, WebAppInfo,
)
from aiohttp import web
from PIL import Image

import db
import scoring
import report

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("satbot")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8921780483:AAFp9vw40nscfpLgB5po1YQ-R1WgTigOgQI")
ADMIN_IDS = set(
    int(x) for x in os.environ.get("ADMIN_IDS", "6643058448").replace(" ", "").split(",") if x
)
TOTAL_MOCKS = int(os.environ.get("TOTAL_MOCKS", "1"))
QUESTIONS_PER_MODULE = 22
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@Bilimnur_edu")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")  # masalan https://satbot-production.up.railway.app
PORT = int(os.environ.get("PORT", "8080"))

with open(os.path.join(os.path.dirname(__file__), "answer_keys.json"), encoding="utf-8") as f:
    ANSWER_KEYS = json.load(f)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ---------------------------------------------------------------- FSM holatlari
class Reg(StatesGroup):
    waiting_name = State()


class Submit(StatesGroup):
    choosing_mock = State()
    waiting_m1 = State()
    waiting_m2 = State()


# ---------------------------------------------------------------- Yordamchi funksiyalar
def main_menu_kb():
    buttons = [[KeyboardButton(text="📝 Natija yuborish")]]
    if WEBAPP_URL:
        buttons.append([KeyboardButton(text="🚀 Ilovada topshirish", web_app=WebAppInfo(url=WEBAPP_URL))])
    buttons.append([KeyboardButton(text="📊 Mening natijalarim"), KeyboardButton(text="👤 Profil")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def mocks_kb():
    buttons = []
    row = []
    for i in range(1, TOTAL_MOCKS + 1):
        row.append(InlineKeyboardButton(text=str(i), callback_data=f"mock:{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def key_for(mock_number: int, module: str):
    """Javob kalitini qaytaradi (ba'zi savollar hali kiritilmagan bo'lishi mumkin —
    ular ro'yxatda None bo'ladi va baholashda o'tkazib yuboriladi)."""
    entry = ANSWER_KEYS.get(str(mock_number))
    if not entry:
        return None
    arr = entry.get(module)
    if not arr:
        return None
    return arr


def question_types_for(mock_number: int):
    """Har bir savol 'mc' (A/B/C/D) yoki 'num' (grid-in) ekanini javob kaliti asosida aniqlaydi.
    Bu faqat kirish maydonining TURINI aniqlash uchun, to'g'ri javobning o'zi ochilmaydi."""
    def types(arr):
        result = []
        for v in (arr or [None] * QUESTIONS_PER_MODULE):
            if v is not None and str(v).strip().upper() in ("A", "B", "C", "D"):
                result.append("mc")
            else:
                result.append("mc" if v is None else "num")
        return result

    entry = ANSWER_KEYS.get(str(mock_number))
    if not entry:
        return None
    return {"m1": types(entry.get("M1")), "m2": types(entry.get("M2"))}


async def notify_admins(text: str):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            log.warning("Admin %s ga xabar yuborilmadi: %s", admin_id, e)


def subscribe_kb():
    channel_url = f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga o'tish", url=channel_url)],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim, tekshirish", callback_data="check_sub")],
    ])


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning("Obunani tekshirishda xato (bot kanalga admin qilib qo'shilganmi?): %s", e)
        # Xato bo'lsa (masalan bot kanalga qo'shilmagan), foydalanuvchini bloklamaymiz
        return True


# ---------------------------------------------------------------- Baholash (umumiy funksiya)
def grade_submission(mock_number: int, m1_answers: list, m2_answers: list):
    """
    Javoblarni javob kaliti bilan solishtirib, to'liq natija lug'atini qaytaradi.
    Bu funksiya ham Telegram xabar oqimidan, ham Mini App'ning /api/grade
    endpoint'idan chaqiriladi — mantiq bitta joyda saqlanadi.

    Qaytaradi: dict yoki None (agar javob kaliti hali kiritilmagan bo'lsa)
    """
    key_m1 = key_for(mock_number, "M1")
    key_m2 = key_for(mock_number, "M2")
    if key_m1 is None or key_m2 is None:
        return None

    def grade_module(user_answers, key):
        per_q = []
        correct_count = 0
        wrong, skipped = [], []
        for i, (u, c) in enumerate(zip(user_answers, key)):
            qnum = i + 1
            if c is None:
                skipped.append(qnum)
                per_q.append({"number": qnum, "status": "skipped",
                               "user_answer": u, "correct_answer": None})
                continue
            is_correct = scoring.answers_match(u, c)
            if is_correct:
                correct_count += 1
                per_q.append({"number": qnum, "status": "correct",
                               "user_answer": u, "correct_answer": c})
            else:
                wrong.append(qnum)
                per_q.append({"number": qnum, "status": "wrong",
                               "user_answer": u, "correct_answer": c})
        return correct_count, wrong, skipped, per_q

    m1_correct, wrong_m1, skipped_m1, per_q_m1 = grade_module(m1_answers, key_m1)
    m2_correct, wrong_m2, skipped_m2, per_q_m2 = grade_module(m2_answers, key_m2)

    graded_total = (QUESTIONS_PER_MODULE - len(skipped_m1)) + (QUESTIONS_PER_MODULE - len(skipped_m2))
    raw_score = m1_correct + m2_correct
    projected_raw = round(raw_score * 44 / graded_total) if graded_total else 0
    scaled = scoring.raw_to_scaled(projected_raw)

    return {
        "m1_correct": m1_correct, "wrong_m1": wrong_m1, "skipped_m1": skipped_m1,
        "m2_correct": m2_correct, "wrong_m2": wrong_m2, "skipped_m2": skipped_m2,
        "raw_score": raw_score, "graded_total": graded_total,
        "projected_raw": projected_raw, "scaled_score": scaled,
        "per_question": {"m1": per_q_m1, "m2": per_q_m2},
    }


# ---------------------------------------------------------------- /start va ro'yxatdan o'tish
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if not await is_subscribed(message.from_user.id):
        await message.answer(
            f"Botdan foydalanish uchun avval {CHANNEL_USERNAME} kanaliga a'zo bo'ling.\n\n"
            f"A'zo bo'lgach, pastdagi tugmani bosing 👇",
            reply_markup=subscribe_kb(),
        )
        return

    user = db.get_user(message.from_user.id)
    if user:
        await message.answer(
            f"Salom, {user['full_name']}! 👋\nQuyidagilardan birini tanlang:",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(Reg.waiting_name)
    await message.answer(
        "Assalomu alaykum! SAT Math mock natijalarini yuborish botiga xush kelibsiz.\n\n"
        "Iltimos, Ism va Familiyangizni yuboring (masalan: <i>Aziz Karimov</i>).",
        parse_mode="HTML",
    )


@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    if not await is_subscribed(callback.from_user.id):
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmagansiz.", show_alert=True)
        return

    await callback.answer("✅ Rahmat! Obuna tasdiqlandi.")
    await callback.message.delete()

    user = db.get_user(callback.from_user.id)
    if user:
        await callback.message.answer(
            f"Salom, {user['full_name']}! 👋\nQuyidagilardan birini tanlang:",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(Reg.waiting_name)
    await callback.message.answer(
        "Iltimos, Ism va Familiyangizni yuboring (masalan: <i>Aziz Karimov</i>).",
        parse_mode="HTML",
    )


@dp.message(Reg.waiting_name)
async def process_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name.split()) < 2:
        await message.answer("Iltimos, ism VA familiyangizni birga yuboring (masalan: Aziz Karimov).")
        return

    db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        full_name,
    )
    await state.clear()
    await message.answer(
        f"Rahmat, {full_name}! Ro'yxatdan muvaffaqiyatli o'tdingiz. ✅",
        reply_markup=main_menu_kb(),
    )
    await notify_admins(f"🆕 Yangi foydalanuvchi ro'yxatdan o'tdi: {full_name} (@{message.from_user.username})")


# ---------------------------------------------------------------- Natija yuborish oqimi
@dp.message(F.text == "📝 Natija yuborish")
async def start_submit(message: Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosib ro'yxatdan o'ting.")
        return
    await state.set_state(Submit.choosing_mock)
    await message.answer("Nechinchi mock uchun javob yubormoqchisiz?", reply_markup=mocks_kb())


@dp.callback_query(Submit.choosing_mock, F.data.startswith("mock:"))
async def choose_mock(callback: CallbackQuery, state: FSMContext):
    mock_number = int(callback.data.split(":")[1])
    await state.update_data(mock_number=mock_number)
    await state.set_state(Submit.waiting_m1)
    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"✅ Mock {mock_number} tanlandi.\n\n"
        f"Endi <b>Module 1</b> javoblarini yuboring — jami {QUESTIONS_PER_MODULE} ta, 1-savoldan boshlab tartib bilan.\n\n"
        f"Masalan:\n<code>B C A D B C D A B C A D B C A D B C A D B C</code>\n\n"
        f"Grid-in (variantsiz) savollar uchun raqamni yozing (masalan <code>18.5</code> yoki <code>7/2</code>).",
        parse_mode="HTML",
    )
    await callback.answer()


@dp.message(Submit.waiting_m1)
async def process_m1(message: Message, state: FSMContext):
    answers, err = scoring.parse_answer_list(message.text, QUESTIONS_PER_MODULE)
    if err:
        await message.answer(err)
        return
    await state.update_data(m1_answers=answers)
    await state.set_state(Submit.waiting_m2)
    await message.answer(
        f"👍 Module 1 qabul qilindi.\n\nEndi <b>Module 2</b> javoblarini xuddi shunday yuboring "
        f"(jami {QUESTIONS_PER_MODULE} ta).",
        parse_mode="HTML",
    )


async def grade_and_respond(message: Message, tg_id: int, mock_number: int,
                             m1_answers: list, m2_answers: list):
    """Javoblarni baholab, natija matni + sertifikat rasmi + PDF yuboradi.
    Ham oddiy chat-javob oqimidan, ham Mini App'dan chaqiriladi."""
    result = grade_submission(mock_number, m1_answers, m2_answers)

    if result is None:
        await message.answer(
            f"⚠️ Kechirasiz, Mock {mock_number} uchun javob kaliti hali botga kiritilmagan.\n"
            f"Javoblaringiz qabul qilindi va saqlandi, lekin ball hisoblanmadi — admin javob "
            f"kalitini kiritgach, sizga natija yuboriladi.",
            reply_markup=main_menu_kb(),
        )
        db.save_submission(tg_id, mock_number, m1_answers, m2_answers,
                            None, None, None, None, [], [])
        await notify_admins(f"📩 Yangi javob (KALIT YO'Q): mock {mock_number}, foydalanuvchi {tg_id}")
        return

    m1_correct = result["m1_correct"]
    m2_correct = result["m2_correct"]
    wrong_m1, skipped_m1 = result["wrong_m1"], result["skipped_m1"]
    wrong_m2, skipped_m2 = result["wrong_m2"], result["skipped_m2"]
    raw_score = result["raw_score"]
    graded_total = result["graded_total"]
    scaled = result["scaled_score"]

    db.save_submission(tg_id, mock_number, m1_answers, m2_answers,
                        m1_correct, m2_correct, raw_score, scaled, wrong_m1, wrong_m2)

    def fmt_wrong(lst):
        return ", ".join(str(x) for x in lst) if lst else "yo'q 🎉"

    def checklist(n_questions, wrong_set, skipped_set):
        lines = []
        row = []
        for i in range(1, n_questions + 1):
            if i in skipped_set:
                mark = f"{i}⬜"
            elif i in wrong_set:
                mark = f"{i}❌"
            else:
                mark = f"{i}✅"
            row.append(mark)
            if len(row) == 6:
                lines.append(" ".join(row))
                row = []
        if row:
            lines.append(" ".join(row))
        return "\n".join(lines)

    skip_note = ""
    if skipped_m1 or skipped_m2:
        skip_note = "\n⬜ = hali javob kaliti kiritilmagan (hisobga olinmagan)\n"

    result_text = (
        f"📊 <b>Mock {mock_number} — natija</b>\n\n"
        f"<b>Module 1: {m1_correct}/{QUESTIONS_PER_MODULE - len(skipped_m1)} to'g'ri</b>\n"
        f"{checklist(QUESTIONS_PER_MODULE, set(wrong_m1), set(skipped_m1))}\n\n"
        f"<b>Module 2: {m2_correct}/{QUESTIONS_PER_MODULE - len(skipped_m2)} to'g'ri</b>\n"
        f"{checklist(QUESTIONS_PER_MODULE, set(wrong_m2), set(skipped_m2))}\n\n"
        f"🎯 <b>Math bali: {scaled}/800</b> <i>(taxminiy)</i>"
        f"{skip_note}"
    )
    await message.answer(result_text, parse_mode="HTML", reply_markup=main_menu_kb())

    if report.has_domain_data(mock_number):
        try:
            key_m1 = key_for(mock_number, "M1")
            key_m2 = key_for(mock_number, "M2")
            stats = report.compute_domain_stats(mock_number, m1_answers, m2_answers,
                                                 key_m1, key_m2, scoring)
            user = db.get_user(tg_id)
            other_scores = db.get_scores_for_mock(mock_number, exclude_tg_id=tg_id)
            buf = report.render_report(user["full_name"], mock_number, scaled, stats,
                                        other_scores=other_scores)

            # PNG sertifikatni rasm sifatida yuboramiz
            buf.seek(0)
            png_bytes = buf.getvalue()
            photo = BufferedInputFile(png_bytes, filename=f"mock{mock_number}_report.png")
            await message.answer_photo(photo, caption="📄 Sizning batafsil natija sertifikatingiz")

            # Xuddi shu rasmni PDF hujjat sifatida ham yuboramiz
            img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            pdf_buf = io.BytesIO()
            img.save(pdf_buf, format="PDF")
            pdf_buf.seek(0)
            pdf_doc = BufferedInputFile(pdf_buf.getvalue(), filename=f"mock{mock_number}_report.pdf")
            await message.answer_document(pdf_doc, caption="📎 PDF ko'rinishida")
        except Exception as e:
            log.warning("Report yaratishda xato: %s", e)

    user = db.get_user(tg_id)
    await notify_admins(
        f"📩 {user['full_name']} — Mock {mock_number}: {raw_score}/{graded_total} (≈{scaled}/800)\n"
        f"Xato M1: {fmt_wrong(wrong_m1)} | Xato M2: {fmt_wrong(wrong_m2)}"
    )


@dp.message(Submit.waiting_m2)
async def process_m2(message: Message, state: FSMContext):
    answers, err = scoring.parse_answer_list(message.text, QUESTIONS_PER_MODULE)
    if err:
        await message.answer(err)
        return
    data = await state.get_data()
    mock_number = data["mock_number"]
    m1_answers = data["m1_answers"]
    m2_answers = answers
    await state.clear()
    await grade_and_respond(message, message.from_user.id, mock_number, m1_answers, m2_answers)


@dp.message(F.web_app_data)
async def process_webapp_data(message: Message, state: FSMContext):
    """Mini App'dan 'Yakunlash va yopish' bosilganda kelgan ma'lumotni qabul qiladi."""
    try:
        payload = json.loads(message.web_app_data.data)
        mock_number = int(payload["mock_number"])
        m1_answers = payload["m1_answers"]
        m2_answers = payload["m2_answers"]
        if len(m1_answers) != QUESTIONS_PER_MODULE or len(m2_answers) != QUESTIONS_PER_MODULE:
            raise ValueError("javoblar soni noto'g'ri")
    except Exception as e:
        log.warning("Mini App ma'lumotini o'qishda xato: %s", e)
        await message.answer("⚠️ Ilovadan kelgan ma'lumotni o'qib bo'lmadi. Qaytadan urinib ko'ring.")
        return

    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosib ro'yxatdan o'ting.")
        return

    await state.clear()
    await grade_and_respond(message, message.from_user.id, mock_number, m1_answers, m2_answers)


# ---------------------------------------------------------------- Foydalanuvchi o'z natijalarini ko'rishi
@dp.message(F.text == "📊 Mening natijalarim")
async def my_results(message: Message):
    subs = db.get_user_submissions(message.from_user.id)
    if not subs:
        await message.answer("Siz hali hech qanday natija yubormagansiz.")
        return
    lines = ["📊 <b>Sizning natijalaringiz:</b>\n"]
    for s in subs:
        if s["scaled_score"] is None:
            lines.append(f"Mock {s['mock_number']}: kalit kutilmoqda ⏳")
        else:
            lines.append(f"Mock {s['mock_number']}: {s['raw_score']}/44 (≈{s['scaled_score']}/800)")
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(F.text == "👤 Profil")
async def my_profile(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosib ro'yxatdan o'ting.")
        return
    subs = db.get_user_submissions(message.from_user.id)
    graded = [s for s in subs if s["scaled_score"] is not None]
    reg_date = user["registered_at"][:10] if user.get("registered_at") else "—"
    lines = [
        "👤 <b>Profil</b>\n",
        f"Ism: <b>{user['full_name']}</b>",
        f"Username: @{user['username']}" if user.get("username") else "Username: —",
        f"Ro'yxatdan o'tgan sana: {reg_date}",
        f"Telegram ID: <code>{user['tg_id']}</code>\n",
        f"Jami yuborilgan natijalar: <b>{len(subs)}</b>",
    ]
    if graded:
        best = max(graded, key=lambda s: s["scaled_score"])
        avg = round(sum(s["scaled_score"] for s in graded) / len(graded))
        lines.append(f"Eng yaxshi ball: <b>{best['scaled_score']}/800</b> (Mock {best['mock_number']})")
        lines.append(f"O'rtacha ball: <b>{avg}/800</b>")
    await message.answer("\n".join(lines), parse_mode="HTML")


# ---------------------------------------------------------------- Admin buyruqlari
def is_admin(user_id):
    return user_id in ADMIN_IDS


@dp.message(Command("students"))
async def admin_students(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = db.get_all_users()
    if not users:
        await message.answer("Hali hech kim ro'yxatdan o'tmagan.")
        return
    lines = [f"👥 Jami: {len(users)} ta foydalanuvchi\n"]
    for u in users:
        uname = f"@{u['username']}" if u["username"] else "(username yo'q)"
        lines.append(f"• {u['full_name']} — {uname} — id:{u['tg_id']}")
    # Telegram xabar uzunligi cheklovi uchun bo'lib yuboramiz
    text = "\n".join(lines)
    for i in range(0, len(text), 3500):
        await message.answer(text[i:i + 3500])


@dp.message(Command("results"))
async def admin_results(message: Message):
    if not is_admin(message.from_user.id):
        return
    subs = db.get_all_submissions()
    if not subs:
        await message.answer("Hali hech qanday natija yo'q.")
        return
    lines = [f"📊 Jami: {len(subs)} ta natija\n"]
    for s in subs:
        name = s["full_name"] or f"id:{s['tg_id']}"
        if s["scaled_score"] is None:
            lines.append(f"• {name} — Mock {s['mock_number']} — kalit yo'q ⏳")
        else:
            lines.append(f"• {name} — Mock {s['mock_number']} — {s['raw_score']}/44 (≈{s['scaled_score']}/800)")
    text = "\n".join(lines)
    for i in range(0, len(text), 3500):
        await message.answer(text[i:i + 3500])


@dp.message(Command("whoami"))
async def whoami(message: Message):
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


# ---------------------------------------------------------------- Mini App uchun veb-server
WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "webapp")


async def webapp_index(request):
    # Avval webapp/index.html ni, topilmasa repo ROOT'dagi index.html ni sinaymiz
    candidates = [
        os.path.join(WEBAPP_DIR, "index.html"),
        os.path.join(os.path.dirname(__file__), "index.html"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return web.Response(text="index.html topilmadi", status=500)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{TOTAL_MOCKS}}", str(TOTAL_MOCKS))
    return web.Response(text=html, content_type="text/html")


async def webapp_mock_types(request):
    mock_number = int(request.match_info["mock_number"])
    types = question_types_for(mock_number)
    if types is None:
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response(types)


async def webapp_grade(request):
    """Mini App ichida 'Javoblarni yuborish' bosilganda chaqiriladi.
    Natijani (ball + har bir savol to'g'ri/xato) darhol ilovaning o'ziga qaytaradi,
    lekin bazaga saqlash va Telegram xabar/PDF yuborish hali sodir bo'lmaydi —
    bu faqat foydalanuvchi 'Yakunlash va yopish' bosgach, tg.sendData orqali amalga oshadi."""
    mock_number = int(request.match_info["mock_number"])
    try:
        data = await request.json()
        m1_answers = data["m1_answers"]
        m2_answers = data["m2_answers"]
    except Exception:
        return web.json_response({"error": "invalid payload"}, status=400)

    result = grade_submission(mock_number, m1_answers, m2_answers)
    if result is None:
        return web.json_response({"error": "answer key not available"}, status=404)

    return web.json_response(result)


async def start_webserver():
    app = web.Application()
    app.router.add_get("/", webapp_index)
    app.router.add_get("/api/mock/{mock_number}", webapp_mock_types)
    app.router.add_post("/api/grade/{mock_number}", webapp_grade)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info("Mini App veb-server ishga tushdi: port %s", PORT)


# ---------------------------------------------------------------- Ishga tushirish
async def main():
    db.init_db()

    # O'z-o'zini tekshirish: fonts/logo to'g'ri yuklanganini Railway logida ko'rsatadi
    import os as _os
    font_ok = any(_os.path.exists(p) for p in report.FONT_CANDIDATES_BOLD)
    logo_ok = _os.path.exists(report.LOGO_PATH)
    log.info("Self-check: bold font found = %s, Bilimnur logo found = %s", font_ok, logo_ok)
    log.info("Self-check details:\n%s", report.debug_paths())
    if not font_ok:
        log.warning("DIQQAT: shrift fayllari topilmadi — DejaVuSans-Bold.ttf va DejaVuSans.ttf "
                    "repo ROOT papkasida (fonts/ ichida emas) borligini tekshiring!")
    if not logo_ok:
        log.warning("DIQQAT: bilimnur_logo.png topilmadi — repo ROOT papkasida borligini tekshiring!")
    if not WEBAPP_URL:
        log.warning("DIQQAT: WEBAPP_URL o'rnatilmagan — Mini App tugmasi menyuda ko'rinmaydi!")

    await start_webserver()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
