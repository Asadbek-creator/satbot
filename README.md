# SAT Math Mock — Telegram bot

Bu bot orqali o'quvchilar ro'yxatdan o'tadi, xohlagan mock uchun Module 1 va
Module 2 javoblarini yuboradi, bot ularni javob kaliti bilan solishtirib
avtomatik baholaydi (taxminiy 200-800 ball) va xato savollarni ko'rsatadi.
Siz (admin) barcha ro'yxatdan o'tganlarni va barcha natijalarni ko'ra olasiz.

**Hozirgi holat: faqat Mock 1 ishlaydi** (`TOTAL_MOCKS=1`). Qolgan mocklarni
birma-bir yechib, `answer_keys.json`ga qo'shib boraman — tayyor bo'lganda
aytaman, siz `TOTAL_MOCKS` sonini oshirasiz va botni qayta ishga tushirasiz.

## ENG OSON YO'L — kod yozmasdan (~5 daqiqa)

Token va Telegram ID allaqachon kodning ichiga kiritilgan — sizga faqat
yuklash va deploy qilish qoladi.

1. **GitHub'ga yuklang**: https://github.com da bepul akkaunt oching → "New
   repository" → nom bering (masalan `satbot`) → "Create" → "Add file" →
   "Upload files" orqali shu papkadagi barcha fayllarni yuklang → "Commit".
2. **Railway'ga ulang**: https://railway.app ga GitHub bilan kiring → "New
   Project" → "Deploy from GitHub repo" → repo'ni tanlang.
3. **"Settings" → Start Command**: `python bot.py`
4. Tayyor — bot doimiy ishlaydi. Telegramda `/start` deb sinab ko'ring.

Keyinchalik yangi mock qo'shilganda, yangilangan `answer_keys.json`ni
GitHub'da eskisining ustidan qayta yuklaysiz va `bot.py`dagi `TOTAL_MOCKS`
qiymatini oshirasiz (yoki men yangilab beraman).

## Kompyuterda ishga tushirish (dasturlash bilan tanish bo'lsangiz)

1. Telegramda **@BotFather** ga yozing → `/newbot` → nom bering → **token** oling
   (masalan `123456789:AAH...`).
2. O'zingizning Telegram ID'ingizni bilish uchun shu botni ishga tushirgach
   unga `/whoami` deb yozing.

## 2. Kompyuterda ishga tushirish (sinov uchun)

```bash
cd satbot
pip install -r requirements.txt
export BOT_TOKEN="sizning_tokeningiz"
export ADMIN_IDS="sizning_telegram_id"      # bir nechta bo'lsa vergul bilan: "111,222"
python bot.py
```

Endi Telegramda botingizga `/start` yozib sinab ko'rishingiz mumkin.

## 3. Doimiy ishlab turishi uchun (bepul variantlar)

Kompyuteringiz o'chsa bot ham to'xtaydi. Doimiy ishlashi uchun serverga qo'yish kerak:

**Railway.app (eng oson, bepul boshlanish balansi bor):**
1. https://railway.app da ro'yxatdan o'ting, GitHub akkauntingiz bilan kiring.
2. Shu `satbot` papkani GitHub'ga yuklang (yangi repo yarating).
3. Railway'da "New Project" → "Deploy from GitHub repo" → shu repo'ni tanlang.
4. "Variables" bo'limida `BOT_TOKEN` va `ADMIN_IDS` ni kiriting.
5. Railway avtomatik `pip install -r requirements.txt` va `python bot.py` ishga tushiradi
   (agar tushirmasa, "Settings → Start Command" ga `python bot.py` deb yozing).

**Yoki oddiy VPS (masalan Timeweb, Contabo, DigitalOcean):**
```bash
sudo apt install python3-pip
pip3 install -r requirements.txt
# doimiy ishlashi uchun:
sudo apt install screen
screen -S satbot
export BOT_TOKEN="..."; export ADMIN_IDS="..."
python3 bot.py
# Ctrl+A keyin D bosing (screen'dan chiqish, bot orqada ishlayveradi)
```

## 4. Javob kalitlarini kiritish / to'g'rilash — `answer_keys.json`

Bu faylda har bir mock uchun Module 1 va Module 2'ning 22 tadan to'g'ri javoblari
turadi. Format:

```json
"20": {
  "M1": ["D", 188, "A", "C", null, 768, ...],
  "M2": ["A", null, 648, "D", ...]
}
```

- Variantli savollar uchun: `"A"`, `"B"`, `"C"`, `"D"` (katta harf bilan, lekin
  bot kichik harfni ham tushunadi).
- Grid-in (variantsiz) savollar uchun: son yoki kasr, masalan `188`, `"7/13"`,
  `"5.5"`.
- Agar bir nechta javob to'g'ri hisoblanishi kerak bo'lsa: `"2.6|13/5"` kabi
  `|` bilan ajratib yozing.
- **`null`** — bu savol uchun javob kaliti hali kiritilmagan degani. Bot bunday
  savollarni hisoblashda o'tkazib yuboradi va foydalanuvchiga "bu savollar hali
  tekshirilmagan" deb ko'rsatadi, ball esa qolgan savollar asosida taxmin qilinadi.

**Hozirgi holat:**
- **Mock 22 (March US-B)** — to'liq va aniq (asl javob kaliti jadvalidan olindi) ✅
- **Mock 20 (Dec US-B), Mock 21 (June US-C)** — men o'zim yechib chiqdim, deyarli
  hammasi to'liq; faqat quyidagi savollar figuraga bog'liq bo'lgani yoki OCR
  matni buzilgani sababli tasdiqlanmagan (`null`):
  - Mock 20 Module 1: 5, 11, 15, 19
  - Mock 20 Module 2: 2, 8, 21
- **Mock 1–19** — bu mocklarning javob kaliti menda umuman yo'q (men faqat
  kitobning dizaynini tuzatgan edim). Agar sizda alohida javob-kalit sahifalari/
  PDF bo'lsa, ularni menga yuboring — men to'g'ridan-to'g'ri shu faylga
  kiritib beraman. Aks holda `answer_keys.json`da o'zingiz to'ldirishingiz mumkin
  (format yuqorida ko'rsatilgan).

Faylni o'zgartirgach, botni qayta ishga tushirish kifoya (Railway'da avtomatik
qayta yuklaydi, kompyuterda `Ctrl+C` bosib qaytadan `python bot.py`).

## 5. Ball haqida muhim eslatma

College Board Digital SAT Math uchun oldindan e'lon qilingan **yagona rasmiy**
raw→scaled (200-800) jadval yo'q — bu har bir test formasi uchun picha farq
qiladi va asl test moslashuvchan (adaptive: Module 2 qiyinligi Module 1
natijasiga qarab o'zgaradi). `scoring.py` faylidagi jadval keng tarqalgan
**taxminiy** jadval — natija real balldan ±10-20 ball farq qilishi mumkin.
Bu botning har bir javobida ham aytib o'tiladi.

## 6. Admin buyruqlari

- `/students` — ro'yxatdan o'tgan barcha foydalanuvchilar ro'yxati
- `/results` — barcha yuborilgan natijalar ro'yxati
- `/whoami` — o'z Telegram ID'ingizni ko'rsatadi

Har bir yangi ro'yxatdan o'tish va har bir yuborilgan natija haqida sizga
(admin) avtomatik xabar keladi — botni doim kuzatib turishingiz shart emas.

## Fayllar tuzilishi

```
satbot/
├── bot.py             ← asosiy bot kodi
├── db.py               ← SQLite ma'lumotlar bazasi (avtomatik yaratiladi: satbot.db)
├── scoring.py          ← javoblarni solishtirish + ball hisoblash
├── answer_keys.json    ← javob kalitlari (bu yerni to'ldirib boring)
└── requirements.txt
```
