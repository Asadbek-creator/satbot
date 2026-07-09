# -*- coding: utf-8 -*-
"""
Har bir natija uchun 'sertifikat' — Bilimnur Learning Center brendi bilan
SAT Math Score Report rasmi yaratadi.
Faqat domain (mavzu) ma'lumoti mavjud bo'lgan mocklar uchun ishlaydi
(hozircha domains.json'da faqat Mock 1 bor).
"""

import io
import os
import json
import math
import datetime
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(__file__)

with open(os.path.join(HERE, "domains.json"), encoding="utf-8") as f:
    DOMAINS = json.load(f)

DOMAIN_ORDER = [
    "Algebra",
    "Advanced Math",
    "Problem-Solving and Data Analysis",
    "Geometry and Trigonometry",
]
DOMAIN_PERCENT = {
    "Algebra": 35,
    "Advanced Math": 35,
    "Problem-Solving and Data Analysis": 15,
    "Geometry and Trigonometry": 15,
}
MATH_3YR_AVERAGE = 512  # College Board's publicly reported 3-year average Math score
TOTAL_QUESTIONS = 44
MATH_SECTIONS = 2
TOTAL_TIME_MIN = 70  # official Digital SAT Math timing (35 min x 2 modules)

FONT_DIR = os.path.join(HERE, "fonts")
FONT_CANDIDATES_REGULAR = [
    os.path.join(FONT_DIR, "DejaVuSans.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
FONT_CANDIDATES_BOLD = [
    os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
LOGO_PATH = os.path.join(HERE, "assets", "bilimnur_logo.png")

GREEN = (34, 139, 76)
DARK_GREEN = (21, 87, 48)
GOLD = (232, 172, 39)
DARK = (33, 37, 41)
GRAY = (110, 118, 125)
LIGHT_BG = (240, 248, 242)
CARD_BORDER = (214, 232, 219)


def _load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def has_domain_data(mock_number: int) -> bool:
    return str(mock_number) in DOMAINS


def _band_for(pct: float):
    if pct >= 0.8:
        return (680, 800)
    if pct >= 0.6:
        return (560, 680)
    if pct >= 0.4:
        return (440, 560)
    if pct >= 0.2:
        return (320, 440)
    return (200, 320)


def compute_domain_stats(mock_number, m1_answers, m2_answers, key_m1, key_m2, scoring_module):
    d = DOMAINS[str(mock_number)]
    stats = {name: [0, 0] for name in DOMAIN_ORDER}
    for u, c, dom in zip(m1_answers, key_m1, d["M1"]):
        if c is None:
            continue
        stats[dom][1] += 1
        if scoring_module.answers_match(u, c):
            stats[dom][0] += 1
    for u, c, dom in zip(m2_answers, key_m2, d["M2"]):
        if c is None:
            continue
        stats[dom][1] += 1
        if scoring_module.answers_match(u, c):
            stats[dom][0] += 1
    result = {}
    for name in DOMAIN_ORDER:
        correct, total = stats[name]
        pct = correct / total if total else 0
        result[name] = {"correct": correct, "total": total, "pct": pct, "band": _band_for(pct)}
    return result


def _percentile_text(scaled_score, other_scores):
    """Boshqa haqiqiy foydalanuvchilar natijalari asosida (agar yetarli bo'lsa)."""
    if len(other_scores) < 3:
        return None
    lower = sum(1 for s in other_scores if s < scaled_score)
    return round(100 * lower / len(other_scores))


def _draw_badge(draw, cx, cy, r, fill):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    points = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rad = r * 0.55 if i % 2 == 0 else r * 0.22
        points.append((cx + rad * math.cos(ang), cy - rad * math.sin(ang)))
    draw.polygon(points, fill=(255, 255, 255))


def render_report(student_name, mock_number, scaled_score, domain_stats,
                   other_scores=None, out_path=None):
    other_scores = other_scores or []
    W, H = 1000, 1180
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    f_brand = _load_font(FONT_CANDIDATES_BOLD, 26)
    f_sub = _load_font(FONT_CANDIDATES_REGULAR, 14)
    f_h2 = _load_font(FONT_CANDIDATES_BOLD, 20)
    f_h3 = _load_font(FONT_CANDIDATES_BOLD, 16)
    f_score = _load_font(FONT_CANDIDATES_BOLD, 60)
    f_score_sub = _load_font(FONT_CANDIDATES_REGULAR, 18)
    f_small = _load_font(FONT_CANDIDATES_REGULAR, 14)
    f_small_b = _load_font(FONT_CANDIDATES_BOLD, 14)
    f_body_b = _load_font(FONT_CANDIDATES_BOLD, 16)
    f_footer = _load_font(FONT_CANDIDATES_BOLD, 19)
    f_footer_sub = _load_font(FONT_CANDIDATES_REGULAR, 15)

    # ---- Header ----
    _draw_badge(draw, 55, 45, 26, GREEN)
    draw.text((95, 20), "SAT Math Score Report", font=f_brand, fill=DARK)
    draw.text((95, 55), "Your Score. Your Potential.", font=f_sub, fill=GRAY)

    if os.path.exists(LOGO_PATH):
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((80, 80))
            img.paste(logo, (W - 40 - logo.width, 15), logo)
        except Exception:
            pass

    today = datetime.date.today().strftime("%B %d, %Y")
    info_lines = [f"Student: {student_name}", f"Mock: {mock_number}", f"Date: {today}"]
    iy = 100
    for line in info_lines:
        w = draw.textlength(line, font=f_small)
        draw.text((W - 40 - w, iy), line, font=f_small, fill=GRAY)
        iy += 18

    draw.line([(40, 165), (W - 40, 165)], fill=CARD_BORDER, width=2)

    # ---- Two cards: welcome + score ----
    card_top = 185
    card_h = 165

    draw.rounded_rectangle([40, card_top, 480, card_top + card_h], radius=14,
                            fill=LIGHT_BG, outline=CARD_BORDER, width=1)
    _draw_badge(draw, 80, card_top + 45, 22, GREEN)
    draw.text((60, card_top + 80), student_name, font=f_h2, fill=DARK)
    draw.text((60, card_top + 108),
              "You've taken an important step on your path.", font=f_small, fill=GRAY)
    draw.text((60, card_top + 128),
              "Keep building your skills toward your goals.", font=f_small, fill=GRAY)

    draw.rounded_rectangle([500, card_top, W - 40, card_top + card_h], radius=14, fill=DARK_GREEN)
    draw.text((525, card_top + 18), "YOUR MATH SCORE", font=f_h3, fill=(220, 235, 225))
    draw.text((525, card_top + 42), str(scaled_score), font=f_score, fill="white")
    score_w = draw.textlength(str(scaled_score), font=f_score)
    draw.text((525 + score_w + 10, card_top + 78), "/ 800", font=f_score_sub, fill=(220, 235, 225))
    _draw_badge(draw, W - 90, card_top + 55, 26, GOLD)

    draw.text((525, card_top + 120), f"3-Year Average (all testers): {MATH_3YR_AVERAGE}",
               font=f_small, fill=(220, 235, 225))

    # ---- Knowledge and Skills (left column) ----
    y0 = card_top + card_h + 35
    col_left_x = 40
    col_left_w = 430
    draw.text((col_left_x, y0), "Knowledge and Skills", font=f_h2, fill=DARK)
    draw.text((col_left_x, y0 + 26), "Your performance across the 4 Math domains.",
              font=f_small, fill=GRAY)

    y = y0 + 62
    segments = 8
    gap = 3
    seg_w = (col_left_w - gap * (segments - 1)) / segments
    best_domain = max(DOMAIN_ORDER, key=lambda n: domain_stats[n]["pct"])
    worst_domain = min(DOMAIN_ORDER, key=lambda n: domain_stats[n]["pct"])

    for name in DOMAIN_ORDER:
        st = domain_stats[name]
        band_low, band_high = st["band"]
        draw.text((col_left_x, y), name, font=f_body_b, fill=DARK)
        y += 20
        sub = f"{DOMAIN_PERCENT[name]}% of test  \u00b7  {st['correct']}/{st['total']} correct"
        draw.text((col_left_x, y), sub, font=f_small, fill=GRAY)
        y += 22
        mid = (band_low + band_high) / 2
        filled_frac = max(0, min(1, (mid - 200) / 600))
        filled_segments = round(filled_frac * segments)
        for s in range(segments):
            x0 = col_left_x + s * (seg_w + gap)
            x1 = x0 + seg_w
            fill = GREEN if s < filled_segments else CARD_BORDER
            draw.rounded_rectangle([x0, y, x1, y + 14], radius=3, fill=fill)
        y += 22
        draw.text((col_left_x, y), f"Performance: {band_low}-{band_high}", font=f_small_b, fill=DARK_GREEN)
        y += 32

    # ---- Performance Summary + Test Info (right column) ----
    col_right_x = 520
    ry = y0

    def summary_item(icon_fill, title, body_lines):
        nonlocal ry
        _draw_badge(draw, col_right_x + 14, ry + 12, 12, icon_fill)
        draw.text((col_right_x + 36, ry), title, font=f_body_b, fill=DARK)
        ry += 22
        for line in body_lines:
            draw.text((col_right_x + 36, ry), line, font=f_small, fill=GRAY)
            ry += 19
        ry += 14

    draw.text((col_right_x, ry), "Performance Summary", font=f_h2, fill=DARK)
    ry += 36
    summary_item(GREEN, "Strength", [f"{best_domain} \u2014 keep practicing", "consistently to hold this level."])
    summary_item(GOLD, "Area for Improvement", [f"{worst_domain}.", "Focus extra practice here next."])
    summary_item(DARK_GREEN, "Recommended Study Plan",
                 ["2-3 focused sessions per week on", f"{worst_domain} for the next 2 weeks."])

    ry += 6
    draw.line([(col_right_x, ry), (W - 40, ry)], fill=CARD_BORDER, width=1)
    ry += 18
    draw.text((col_right_x, ry), "Test Information", font=f_h3, fill=DARK)
    ry += 26
    info_rows = [
        ("Total Questions", str(TOTAL_QUESTIONS)),
        ("Math Test Sections", str(MATH_SECTIONS)),
        ("Total Time", f"{TOTAL_TIME_MIN} minutes"),
    ]
    for label, val in info_rows:
        draw.text((col_right_x, ry), label, font=f_small, fill=GRAY)
        val_w = draw.textlength(val, font=f_small_b)
        draw.text((W - 40 - val_w, ry), val, font=f_small_b, fill=DARK)
        ry += 22

    # ---- Your Next Steps banner ----
    steps_top = max(y, ry) + 30
    steps_h = 130
    draw.rounded_rectangle([40, steps_top, W - 40, steps_top + steps_h], radius=14, fill=LIGHT_BG,
                            outline=CARD_BORDER, width=1)
    draw.text((60, steps_top + 16), "Your Next Steps", font=f_h2, fill=DARK)
    steps = [
        ("Review Your Answers", "Go over your practice test to understand your results."),
        ("Strengthen Your Skills", "Focus on weak areas and master key concepts."),
        ("Practice Regularly", "Take full-length practice tests and mock exams."),
        ("Achieve Your Goal", "Stay consistent and believe in yourself."),
    ]
    step_w = (W - 80 - 60) / 4
    for i, (title, body) in enumerate(steps):
        sx = 60 + i * (step_w + 20)
        _draw_badge(draw, sx + 16, steps_top + 60, 16, GREEN)
        draw.text((sx, steps_top + 85), title, font=f_small_b, fill=DARK)
        words = body.split()
        line1, line2 = "", ""
        for w_ in words:
            if draw.textlength(line1 + w_, font=f_small) < step_w:
                line1 += w_ + " "
            else:
                line2 += w_ + " "
        draw.text((sx, steps_top + 103), line1.strip(), font=f_small, fill=GRAY)
        if line2:
            draw.text((sx, steps_top + 119), line2.strip(), font=f_small, fill=GRAY)

    # ---- Footer promo ----
    footer_y = steps_top + steps_h + 25
    draw.rectangle([0, footer_y, W, footer_y + 80], fill=DARK_GREEN)
    msg = "Want more mock tests like this?"
    msg2 = "Subscribe to our channel \u2014 @Bilimnur_edu"
    msg_w = draw.textlength(msg, font=f_footer)
    msg2_w = draw.textlength(msg2, font=f_footer_sub)
    draw.text(((W - msg_w) / 2, footer_y + 15), msg, font=f_footer, fill="white")
    draw.text(((W - msg2_w) / 2, footer_y + 45), msg2, font=f_footer_sub, fill=(210, 230, 215))

    final_h = footer_y + 80 + 20
    img = img.crop((0, 0, W, final_h))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    if out_path:
        with open(out_path, "wb") as fh:
            fh.write(buf.getbuffer())
    return buf
