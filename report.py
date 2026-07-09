# -*- coding: utf-8 -*-
"""
Har bir natija uchun 'sertifikat' — SAT skor hisobotiga o'xshash rasm yaratadi.
Faqat domain (mavzu) ma'lumoti mavjud bo'lgan mocklar uchun ishlaydi
(hozircha domains.json'da faqat Mock 1 bor).
"""

import io
import os
import json
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

FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


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
    """0..1 to'g'ri javob nisbati -> (past, yuqori) ball oralig'i (200-800)."""
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
    """Har bir domain uchun (to'g'ri, jami, foiz, band) hisoblaydi."""
    d = DOMAINS[str(mock_number)]
    stats = {name: [0, 0] for name in DOMAIN_ORDER}  # [correct, total]
    for i, (u, c, dom) in enumerate(zip(m1_answers, key_m1, d["M1"])):
        if c is None:
            continue
        stats[dom][1] += 1
        if scoring_module.answers_match(u, c):
            stats[dom][0] += 1
    for i, (u, c, dom) in enumerate(zip(m2_answers, key_m2, d["M2"])):
        if c is None:
            continue
        stats[dom][1] += 1
        if scoring_module.answers_match(u, c):
            stats[dom][0] += 1
    result = {}
    for name in DOMAIN_ORDER:
        correct, total = stats[name]
        pct = correct / total if total else 0
        result[name] = {
            "correct": correct,
            "total": total,
            "pct": pct,
            "band": _band_for(pct),
        }
    return result


def render_report(student_name, mock_number, scaled_score, domain_stats, out_path=None):
    W, H = 1000, 760
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    f_title = _load_font(FONT_CANDIDATES_BOLD, 34)
    f_h2 = _load_font(FONT_CANDIDATES_BOLD, 20)
    f_score = _load_font(FONT_CANDIDATES_BOLD, 52)
    f_small = _load_font(FONT_CANDIDATES_REGULAR, 15)
    f_small_b = _load_font(FONT_CANDIDATES_BOLD, 15)
    f_body = _load_font(FONT_CANDIDATES_REGULAR, 17)
    f_body_b = _load_font(FONT_CANDIDATES_BOLD, 17)

    navy = (27, 79, 138)
    dark = (30, 30, 30)
    gray = (110, 110, 110)
    light_border = (225, 225, 225)

    # Header
    draw.text((40, 30), "SAT Math Score Report", font=f_title, fill=dark)
    draw.text((40, 75), f"{student_name}   |   Mock {mock_number}", font=f_body, fill=gray)
    draw.line([(40, 105), (W - 40, 105)], fill=light_border, width=2)

    # Big score box
    draw.text((40, 130), "MATH SCORE", font=f_h2, fill=gray)
    draw.text((40, 155), str(scaled_score), font=f_score, fill=navy)
    draw.text((175, 190), "/ 800", font=f_body, fill=gray)
    draw.text((40, 240), f"3-Year Average Score (all testers): {MATH_3YR_AVERAGE}", font=f_small, fill=gray)

    draw.line([(40, 275), (W - 40, 275)], fill=light_border, width=2)

    # Knowledge and Skills header
    draw.text((40, 295), "Knowledge and Skills", font=f_h2, fill=dark)
    draw.text((40, 322), "Your performance across the 4 content domains measured in Math.",
              font=f_small, fill=gray)

    y = 370
    bar_x0 = 40
    bar_w = W - 80
    segments = 8
    seg_w = bar_w / segments

    for name in DOMAIN_ORDER:
        st = domain_stats[name]
        pct_section = DOMAIN_PERCENT[name]
        band_low, band_high = st["band"]

        draw.text((bar_x0, y), name, font=f_body_b, fill=dark)
        label = f"({pct_section}% of test section, {st['correct']}/{st['total']} correct)"
        draw.text((bar_x0, y + 22), label, font=f_small, fill=gray)

        bar_y = y + 46
        bar_h = 16
        # segmented bar background
        for s in range(segments):
            x0 = bar_x0 + s * seg_w
            x1 = x0 + seg_w - 3
            draw.rectangle([x0, bar_y, x1, bar_y + bar_h], fill=(230, 230, 230))
        # filled portion based on midpoint of band on 200-800 scale
        mid = (band_low + band_high) / 2
        filled_frac = max(0, min(1, (mid - 200) / 600))
        filled_segments = round(filled_frac * segments)
        for s in range(filled_segments):
            x0 = bar_x0 + s * seg_w
            x1 = x0 + seg_w - 3
            draw.rectangle([x0, bar_y, x1, bar_y + bar_h], fill=navy)

        draw.text((bar_x0, bar_y + 24), f"Performance: {band_low}-{band_high}",
                   font=f_small_b, fill=navy)
        y += 100

    # Footer / promo
    draw.line([(40, y + 5), (W - 40, y + 5)], fill=light_border, width=2)
    draw.text((40, y + 25), "Want more mock tests like this?", font=f_body_b, fill=dark)
    draw.text((40, y + 50), "Subscribe to our channel: @Bilimnur_edu", font=f_body, fill=navy)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    if out_path:
        with open(out_path, "wb") as fh:
            fh.write(buf.getbuffer())
    return buf
