#!/usr/bin/env python3
"""
Greetro OG share-card generator.

Renders images/og-default.png (1200x630): near-black brand background with a
soft violet/cyan aurora, the waveform logo mark, the "Greetro" wordmark filled
with the brand violet->cyan gradient, tagline beneath, and a subtle border.

Everything is drawn at 2x and downsampled for crisp edges. Text-only + vector
shapes; no external assets. Requires Pillow.

Usage:  python3 tools/make_og.py
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "images", "og-default.png")

W, H = 1200, 630
S = 2  # supersampling factor
CW, CH = W * S, H * S

BG = (5, 5, 16)          # --bg  #050510
VIOLET = (162, 155, 254)  # --violet #a29bfe
CYAN = (0, 240, 255)      # --cyan   #00f0ff
TEXT_SOFT = (255, 255, 255)

WORDMARK = "Greetro"
TAGLINE = "The AI voice receptionist — every call answered, 24/7"
FOOTER = "greetro.com"


def find_font(candidates, size):
    """Return the first loadable font, probing .ttc face indexes by name."""
    for path, wanted in candidates:
        if not os.path.exists(path):
            continue
        for index in range(18):
            try:
                font = ImageFont.truetype(path, size, index=index)
            except (OSError, ValueError):
                break
            family, style = font.getname()
            if wanted is None or style.lower() == wanted.lower():
                return font
    return ImageFont.load_default(size)


def display_font(size):
    return find_font([
        ("/System/Library/Fonts/Avenir Next.ttc", "Bold"),
        ("/System/Library/Fonts/HelveticaNeue.ttc", "Bold"),
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
    ], size)


def body_font(size):
    return find_font([
        ("/System/Library/Fonts/Avenir Next.ttc", "Medium"),
        ("/System/Library/Fonts/HelveticaNeue.ttc", "Regular"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", None),
    ], size)


def horizontal_gradient(size, left_rgb, right_rgb):
    """An RGB image blending left_rgb -> right_rgb across the width."""
    width, height = size
    grad = Image.new("RGB", (width, 1))
    px = grad.load()
    for x in range(width):
        t = x / max(width - 1, 1)
        px[x, 0] = tuple(round(a + (b - a) * t) for a, b in zip(left_rgb, right_rgb))
    return grad.resize((width, height))


def paint_aurora(base):
    """Two soft radial glows, heavily blurred, at low opacity."""
    glow = Image.new("RGB", (CW, CH), (0, 0, 0))
    draw = ImageDraw.Draw(glow)
    # Violet glow, upper left
    draw.ellipse([-CW * 0.25, -CH * 0.55, CW * 0.55, CH * 0.55],
                 fill=(44, 38, 92))
    # Cyan glow, lower right
    draw.ellipse([CW * 0.55, CH * 0.55, CW * 1.3, CH * 1.5],
                 fill=(0, 56, 66))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=170 * S))
    # Additive blend keeps the near-black ground while the glows lift softly
    from PIL import ImageChops
    return ImageChops.add(base, glow)


def draw_waveform_mark(canvas, cx, cy, bar_h, grad_left, grad_right):
    """The 4-bar Greetro waveform mark, gradient-filled, centered on (cx, cy)."""
    heights = [0.36, 1.0, 0.64, 0.30]  # relative bar heights, matches the SVG mark
    bar_w = int(bar_h * 0.135)
    gap = int(bar_h * 0.20)
    total_w = 4 * bar_w + 3 * gap
    mask = Image.new("L", (CW, CH), 0)
    mdraw = ImageDraw.Draw(mask)
    x = cx - total_w // 2
    for rel in heights:
        h = int(bar_h * rel)
        y0 = cy - h // 2
        mdraw.rounded_rectangle([x, y0, x + bar_w, y0 + h], radius=bar_w // 2, fill=255)
        x += bar_w + gap
    grad = horizontal_gradient((CW, CH), grad_left, grad_right)
    canvas.paste(grad, (0, 0), mask)
    return total_w


def draw_gradient_text(canvas, text, font, cy, grad_left, grad_right):
    """Draw text centered horizontally, filled with a horizontal gradient."""
    mask = Image.new("L", (CW, CH), 0)
    mdraw = ImageDraw.Draw(mask)
    left, top, right, bottom = mdraw.textbbox((0, 0), text, font=font)
    tw, th = right - left, bottom - top
    x = (CW - tw) // 2 - left
    y = cy - top
    mdraw.text((x, y), text, font=font, fill=255)
    # Gradient spans just the text width so both hues always show
    grad_row = horizontal_gradient((tw, 1), grad_left, grad_right)
    grad = Image.new("RGB", (CW, CH), grad_left)
    grad.paste(grad_row.resize((tw, CH)), ((CW - tw) // 2, 0))
    canvas.paste(grad, (0, 0), mask)
    return th


def main():
    canvas = Image.new("RGB", (CW, CH), BG)
    canvas = paint_aurora(canvas)
    draw = ImageDraw.Draw(canvas)

    # --- Waveform mark ---
    mark_cy = int(CH * 0.30)
    draw_waveform_mark(canvas, CW // 2, mark_cy, bar_h=int(96 * S),
                       grad_left=VIOLET, grad_right=CYAN)

    # --- Wordmark in brand gradient ---
    wm_font = display_font(150 * S)
    draw_gradient_text(canvas, WORDMARK, wm_font, int(CH * 0.415), VIOLET, CYAN)

    # --- Tagline ---
    tg_font = body_font(34 * S)
    l, t, r, b = draw.textbbox((0, 0), TAGLINE, font=tg_font)
    draw.text(((CW - (r - l)) // 2 - l, int(CH * 0.685) - t), TAGLINE,
              font=tg_font, fill=(214, 216, 232))

    # --- Footer domain ---
    ft_font = body_font(24 * S)
    l, t, r, b = draw.textbbox((0, 0), FOOTER, font=ft_font)
    draw.text(((CW - (r - l)) // 2 - l, int(CH * 0.845) - t), FOOTER,
              font=ft_font, fill=(122, 126, 152))

    # --- Subtle border ---
    inset = 14 * S
    draw.rounded_rectangle([inset, inset, CW - inset, CH - inset],
                           radius=20 * S, outline=(255, 255, 255, 36), width=2 * S)
    # A faint second line just inside, tinting toward the brand hues
    inset2 = inset + 3 * S
    draw.rounded_rectangle([inset2, inset2, CW - inset2, CH - inset2],
                           radius=18 * S, outline=(60, 62, 92), width=1 * S)

    out = canvas.resize((W, H), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    out.save(OUT_PATH, "PNG", optimize=True)
    print("Wrote %s (%dx%d)" % (OUT_PATH, W, H))


if __name__ == "__main__":
    main()
