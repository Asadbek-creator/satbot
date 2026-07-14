# -*- coding: utf-8 -*-
"""
Balni hisoblash: javoblarni solishtirish va raw -> scaled (200-800) konvertatsiya.

MUHIM ESLATMA: College Board Digital SAT uchun oldindan e'lon qilingan yagona
rasmiy raw->scaled jadval yo'q (har bir test formasi uchun "equating" orqali
picha farq qiladi, testning o'zi ham adaptiv). Quyidagi jadval keng tarqalgan
taxminiy (approximate) jadval bo'lib, real ball bilan +-10-20 ball farq qilishi
mumkin. Bu shunchaki mashq/prognoz uchun, RASMIY BALL EMAS.
"""

import re

# Taxminiy Math bo'limi uchun raw (0-44) -> scaled (200-800) jadval.
RAW_TO_SCALED_MATH = {
    44: 800, 43: 790, 42: 780, 41: 770, 40: 750, 39: 740, 38: 720, 37: 710,
    36: 700, 35: 680, 34: 670, 33: 650, 32: 640, 31: 620, 30: 600, 29: 585,
    28: 570, 27: 555, 26: 540, 25: 525, 24: 510, 23: 495, 22: 480, 21: 465,
    20: 450, 19: 435, 18: 420, 17: 407, 16: 393, 15: 380, 14: 368, 13: 356,
    12: 344, 11: 332, 10: 320, 9: 308, 8: 296, 7: 284, 6: 272, 5: 260,
    4: 248, 3: 236, 2: 224, 1: 212, 0: 200,
}


def raw_to_scaled(raw_score: int) -> int:
    raw_score = max(0, min(44, raw_score))
    return RAW_TO_SCALED_MATH[raw_score]


def _normalize(ans: str) -> str:
    """Javobni solishtirish uchun normalizatsiya qiladi."""
    if ans is None:
        return ""
    a = str(ans).strip().upper()
    a = a.replace(" ", "")
    a = a.replace(",", ".")  # ba'zi davlatlarda vergul kasr belgisi
    a = a.rstrip(".")
    return a


def _to_float(s: str):
    """Agar mumkin bo'lsa, javobni songa (fraction ham) aylantiradi."""
    s = s.replace("−", "-")
    try:
        if "/" in s:
            num, den = s.split("/")
            return float(num) / float(den)
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


def answers_match(user_ans: str, correct_ans: str) -> bool:
    """
    Bitta savolning javobini solishtiradi.
    - Harfiy javoblar (A/B/C/D): katta-kichik harfga qaramay solishtiriladi.
    - Raqamli (grid-in) javoblar: '13/5' va '2.6' kabi teng qiymatlarni ham
      to'g'ri deb hisoblaydi (kichik tolerantlik bilan).
    - Agar to'g'ri javob bir nechta variantli bo'lsa ('|' bilan ajratilgan,
      masalan "A|B" yoki "2.6|13/5"), ulardan BIRIGA mos kelsa yetarli.
    """
    if correct_ans is None:
        return None  # javob kaliti kiritilmagan

    options = [o for o in str(correct_ans).split("|")]
    u = _normalize(user_ans)
    if not u:
        return False

    for opt in options:
        c = _normalize(opt)
        if u == c:
            return True
        uf, cf = _to_float(u), _to_float(c)
        if uf is not None and cf is not None and abs(uf - cf) < 1e-6:
            return True

    return False


def parse_answer_list(text: str, expected_count: int):
    """
    Foydalanuvchi yuborgan xabarni javoblar ro'yxatiga aylantiradi.
    Qo'llab-quvvatlanadigan formatlar:
      "A B C D ..."           (probel bilan)
      "A,B,C,D,..."           (vergul bilan)
      "1-A 2-B 3-C ..."       (raqam-javob)
      har birini alohida qatorda

    Qaytaradi: (answers_list, error_message_or_None)
    """
    if not text:
        return None, "Xabar bo'sh bo'lmasligi kerak."

    raw = text.strip()
    # "N-JAVOB" yoki "N.JAVOB" yoki "N) JAVOB" formatlarini olib tashlaymiz
    cleaned = re.sub(r"\b\d{1,2}\s*[\.\)\-:]\s*", " ", raw)
    tokens = re.split(r"[\s,;\n]+", cleaned.strip())
    tokens = [t for t in tokens if t != ""]

    if len(tokens) != expected_count:
        return None, (
            f"❗️ {expected_count} ta javob kutilgan edi, lekin {len(tokens)} ta topildi.\n"
            f"Javoblarni shunday yuboring (masalan):\n"
            f"B C A D B C D A B C A D B C A D B C A D B C (jami {expected_count} ta, tartib bo'yicha)"
        )

    return tokens, None
