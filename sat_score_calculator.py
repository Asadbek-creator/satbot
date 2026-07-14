"""
Digital SAT Score Calculator
=============================
Adaptive (2-module) raw score -> scaled score (200-800) konvertatsiyasi.

Mantiq:
1. Module 1 natijasiga qarab talaba Hard yoki Easy Module 2'ga yo'naltiriladi.
2. Ikkala moduldagi to'g'ri javoblar (raw score) yig'iladi.
3. Raw score piecewise-linear jadval orqali scaled score'ga o'giriladi.
4. Easy Module 2'ga tushganlar uchun max ball cheklanadi (real Digital SAT'dagidek,
   chunki Easy modulda eng qiyin savollar yo'q).

Eslatma: Bu College Board'ning rasmiy jadvali emas (ular buni e'lon qilmaydi),
balki ochiq manbalardagi tasdiqlangan raqamlar asosida qurilgan yaqinlashtirish.
Haqiqiy natijadan +-10-30 ball farq qilishi mumkin - xuddi Albert.io, PrepScholar
va boshqa barcha 3-tomon kalkulyatorlari kabi.
"""

# ---------------------------------------------------------------------------
# Raw -> Scaled jadvallar (ochiq manbalardagi Digital SAT ma'lumotlari asosida)
# ---------------------------------------------------------------------------

MATH_TABLE = [
    (0, 200), (5, 260), (10, 320), (15, 380), (18, 420), (20, 450),
    (22, 480), (24, 495), (26, 510), (28, 535), (30, 570), (31, 590),
    (32, 610), (33, 630), (34, 650), (35, 670), (36, 690), (37, 710),
    (38, 720), (39, 740), (40, 750), (41, 770), (42, 780), (43, 790), (44, 800),
]

RW_TABLE = [
    (0, 200), (10, 280), (15, 330), (20, 380), (24, 420), (27, 450),
    (30, 490), (32, 510), (34, 540), (36, 560), (38, 590), (40, 620),
    (42, 650), (43, 660), (44, 670), (45, 690), (46, 700), (47, 710),
    (48, 730), (49, 740), (50, 750), (51, 770), (52, 780), (53, 790), (54, 800),
]

# Module 1'da Hard Module 2'ga o'tish uchun bo'sag'a (threshold)
MATH_ROUTING_THRESHOLD = 15   # 22 tadan
RW_ROUTING_THRESHOLD = 18     # 27 tadan

# Easy Module 2'ga tushganlar uchun max scaled score (real SAT taxminiga ko'ra)
EASY_PATH_CAP = 660


def _interpolate(raw: int, table: list) -> int:
    """Piecewise-linear interpolatsiya orqali raw score'ni scaled score'ga o'giradi."""
    raw = max(0, min(raw, table[-1][0]))
    for i in range(len(table) - 1):
        r1, s1 = table[i]
        r2, s2 = table[i + 1]
        if r1 <= raw <= r2:
            if r2 == r1:
                return s1
            frac = (raw - r1) / (r2 - r1)
            return round(s1 + frac * (s2 - s1))
    return table[-1][1]


def calculate_section_score(module1_correct: int, module2_correct: int,
                             section: str) -> dict:
    """
    section: "math" yoki "rw"
    Qaytaradi: {"scaled_score": int, "raw_score": int, "path": "hard"/"easy"}
    """
    section = section.lower()
    if section == "math":
        table = MATH_TABLE
        threshold = MATH_ROUTING_THRESHOLD
        max_q1 = 22
    elif section in ("rw", "reading_writing", "reading"):
        table = RW_TABLE
        threshold = RW_ROUTING_THRESHOLD
        max_q1 = 27
    else:
        raise ValueError("section 'math' yoki 'rw' bo'lishi kerak")

    module1_correct = max(0, min(module1_correct, max_q1))
    module2_correct = max(0, min(module2_correct, max_q1))
    raw_score = module1_correct + module2_correct

    path = "hard" if module1_correct >= threshold else "easy"
    scaled_score = _interpolate(raw_score, table)

    if path == "easy":
        scaled_score = min(scaled_score, EASY_PATH_CAP)

    # scaled score har doim 200 dan past bo'lmasin
    scaled_score = max(200, scaled_score)

    return {
        "scaled_score": scaled_score,
        "raw_score": raw_score,
        "path": path,
    }


def calculate_total_sat_score(math_m1: int, math_m2: int,
                               rw_m1: int, rw_m2: int) -> dict:
    """To'liq SAT balini hisoblaydi (Math + Reading&Writing)."""
    math_result = calculate_section_score(math_m1, math_m2, "math")
    rw_result = calculate_section_score(rw_m1, rw_m2, "rw")
    total = math_result["scaled_score"] + rw_result["scaled_score"]

    return {
        "total_score": total,
        "math": math_result,
        "reading_writing": rw_result,
    }


if __name__ == "__main__":
    # Rasmda ko'rsatilgan misol: Math Module1=15/22, Module2=11/22 -> 510
    result = calculate_section_score(15, 11, "math")
    print(f"Math: {result}")  # kutilayotgan: scaled_score ~510, path=hard

    # To'liq SAT misoli
    total = calculate_total_sat_score(math_m1=15, math_m2=11, rw_m1=20, rw_m2=18)
    print(f"\nTotal SAT: {total}")
