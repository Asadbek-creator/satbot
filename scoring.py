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
    44: 800, 43: 790, 42: 780, 41: 770, 40: 760, 39: 750, 38: 740, 37: 730,
    36: 720, 35: 710, 34: 700, 33: 690, 32: 680, 31: 670, 30: 660, 29: 650,
    28: 640, 27: 630, 26: 620, 25: 610, 24: 600, 23: 590, 22: 570, 21: 560,
    20: 550, 19: 540, 18: 530, 17: 520, 16: 510, 15: 500, 14: 490, 13: 480,
    12: 470, 11: 460, 10: 450, 9: 440, 8: 430, 7: 410, 6: 400, 5: 390,
    4: 370, 3: 350, 2: 330, 1: 310, 0: 200,
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
      "A B C D ..."               (probel bilan)
      "A,B,C,D,..."               (vergul bilan)
      "1-A 2-B 3-C ..."           (raqam-javob)
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
            f"B C A D B C D A B C A D B C A D B C A D B C  (jami {expected_count} ta, tartib bo'yicha)"
        )
    return tokens, None
