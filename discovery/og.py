"""OG share card generator using Pillow."""
import io
import os
import textwrap
import logging

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 630
PADDING = 60
BG_TOP = (22, 27, 34)        # GitHub dark
BG_BOT = (13, 17, 23)
ACCENT = (88, 166, 255)
ACCENT_PURPLE = (188, 140, 255)
YELLOW = (210, 153, 34)
TEXT = (230, 237, 243)
MUTED = (139, 148, 158)
GREEN = (63, 185, 80)


FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_REG_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _font(size, bold=False):
    paths = FONT_BOLD_CANDIDATES if bold else FONT_REG_CANDIDATES
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_bg():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_BOT)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return img


def _circle_avatar(url, size):
    try:
        resp = requests.get(url, timeout=6)
        resp.raise_for_status()
        av = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        av = av.resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(av, (0, 0), mask)
        return out
    except Exception:
        return None


def _wrap(text, font, max_w, draw):
    if not text:
        return []
    words = text.split()
    if len(words) <= 1:
        return [text]
    lines = []
    current = []
    for w in words:
        trial = " ".join(current + [w])
        if draw.textlength(trial, font=font) <= max_w:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def render_card(repo):
    img = _gradient_bg()
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (WIDTH, 8)], fill=ACCENT_PURPLE)

    f_name = _font(64, bold=True)
    f_owner = _font(28)
    f_desc = _font(28)
    f_meta = _font(26, bold=True)
    f_brand = _font(22, bold=True)

    if repo.owner_avatar:
        avatar = _circle_avatar(repo.owner_avatar, 96)
        if avatar:
            img.paste(avatar, (PADDING, PADDING), avatar)
    text_x = PADDING + (110 if repo.owner_avatar else 0)

    draw.text((text_x, PADDING + 5), repo.owner_login, font=f_owner, fill=MUTED)
    draw.text((text_x, PADDING + 40), repo.name, font=f_name, fill=TEXT)

    desc = repo.readme_summary or repo.description or ""
    desc_y = PADDING + 160
    if desc:
        lines = _wrap(desc, f_desc, WIDTH - 2 * PADDING, draw)[:4]
        for line in lines:
            draw.text((PADDING, desc_y), line, font=f_desc, fill=MUTED)
            desc_y += 38

    if repo.topics:
        topic_y = max(desc_y + 10, PADDING + 320)
        x = PADDING
        for t in repo.topics[:5]:
            label = f"#{t}"
            w = draw.textlength(label, font=_font(22)) + 24
            if x + w > WIDTH - PADDING:
                break
            draw.rounded_rectangle([(x, topic_y), (x + w, topic_y + 36)],
                                   radius=18,
                                   outline=ACCENT, width=1)
            draw.text((x + 12, topic_y + 4), label, font=_font(22), fill=ACCENT)
            x += w + 10

    meta_y = HEIGHT - PADDING - 50
    x = PADDING

    stars_label = f"★ {_stars_display(repo.stars)}"
    draw.text((x, meta_y), stars_label, font=f_meta, fill=YELLOW)
    x += draw.textlength(stars_label, font=f_meta) + 30

    fork_label = f"⑂ {repo.forks}"
    draw.text((x, meta_y), fork_label, font=f_meta, fill=MUTED)
    x += draw.textlength(fork_label, font=f_meta) + 30

    if repo.language:
        lang_label = repo.language
        draw.ellipse([(x, meta_y + 10), (x + 18, meta_y + 28)], fill=ACCENT)
        draw.text((x + 26, meta_y), lang_label, font=f_meta, fill=TEXT)

    brand = "GitSeeker"
    bw = draw.textlength(brand, font=f_brand)
    draw.text((WIDTH - PADDING - bw, HEIGHT - PADDING - 10), brand, font=f_brand, fill=ACCENT_PURPLE)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _stars_display(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)
