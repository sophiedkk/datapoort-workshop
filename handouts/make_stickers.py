#!/usr/bin/env python3
"""A4 sheet of template override stickers for the archetype bricks.

Yellow = a template constraint, stuck on top of what the archetype allows:
  - cardinality stickers cover the cardinality chip (templates can only narrow it)
  - rename stickers cover the field name or an archetype plate's name (exercise renames + blank write-on ones)

Usage:
    uv run make_stickers.py              # out/stickers.pdf: one page, the same for every group
"""

import argparse
import html
import subprocess
from pathlib import Path

from make_bricks import FONT_FAMILY, OUT_DIR, text_width

A4 = (210, 297)
MARGIN = 10
YELLOW, EDGE, INK = "#FFE14D", "#5C4A00", "#1B1B1B"

# (label, how many per group); counts cover the exercises plus spares
CARDINALITY = [
    ("1..1 required", 6),          # 1.2 Systolic + Diastolic, 1.3 Reaction, plus spares
    (None, 6),                     # blank: write your own
]
RENAMES = [                        # element renames in exercise 1.3 and 1.4; blanks for the rest, plates too
    ("Allergy", 1), ("Reaction", 1), ("Directions", 1),
    (None, 6),
]

CARD_W, CARD_H = 28, 9
NAME_W, NAME_H = 75, 10            # fits the header of an archetype plate
GAP = 4


def fit(text, size, max_w, weight=800):
    """Largest font size (mm) <= size at which text fits max_w (mm)."""
    while size > 1.5 and text_width(text, 100, weight) / 100 * size > max_w:
        size -= 0.1
    return round(size, 2)


def card_sticker(x, y, label):
    p = [f'<rect x="{x}" y="{y}" width="{CARD_W}" height="{CARD_H}" rx="{CARD_H / 2}" fill="{YELLOW}" '
         f'stroke="{EDGE}" stroke-width="0.35"/>']
    if label:
        size = fit(label, 3.4, CARD_W - 4)
        p.append(f'<text x="{x + CARD_W / 2}" y="{y + CARD_H / 2 + size * 0.36}" font-size="{size}" '
                 f'font-weight="800" fill="{INK}" text-anchor="middle">{html.escape(label)}</text>')
    else:
        cy = y + CARD_H / 2 + 1.6
        for lx in (x + 4, x + CARD_W / 2 + 2):
            p.append(f'<line x1="{lx}" y1="{cy}" x2="{lx + 8}" y2="{cy}" stroke="{INK}" stroke-width="0.3"/>')
        p.append(f'<text x="{x + CARD_W / 2}" y="{cy}" font-size="3.4" font-weight="800" fill="{INK}" '
                 f'text-anchor="middle">..</text>')
    return p


def name_sticker(x, y, label):
    p = [f'<rect x="{x}" y="{y}" width="{NAME_W}" height="{NAME_H}" rx="2" fill="{YELLOW}" '
         f'stroke="{EDGE}" stroke-width="0.35"/>',
         f'<text x="{x + 3}" y="{y + 3.1}" font-size="2" font-weight="800" fill="{EDGE}" '
         f'letter-spacing="0.15">RENAMED IN TEMPLATE</text>']
    if label:
        size = fit(label, 5.2, NAME_W - 6)
        p.append(f'<text x="{x + 3}" y="{y + NAME_H - 1.9}" font-size="{size}" font-weight="800" '
                 f'fill="{INK}">{html.escape(label)}</text>')
    else:
        p.append(f'<line x1="{x + 3}" y1="{y + NAME_H - 1.6}" x2="{x + NAME_W - 3}" y2="{y + NAME_H - 1.6}" '
                 f'stroke="{EDGE}" stroke-width="0.25" stroke-dasharray="1 1"/>')
    return p


def heading(x, y, text, sub):
    return [f'<text x="{x}" y="{y}" font-size="4.2" font-weight="800" fill="{INK}">{html.escape(text)}</text>',
            f'<text x="{x}" y="{y + 4.5}" font-size="2.8" font-weight="600" fill="#666">{html.escape(sub)}</text>']


def page_svg():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
         f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">',
         '<rect width="100%" height="100%" fill="#fff"/>']
    x0, y = MARGIN, MARGIN + 4
    p += heading(x0, y, "Template override stickers",
                 "Yellow = changed in the template. Templates can only narrow what the archetype allows.")
    y += 14
    p += heading(x0, y, "Cardinality", "Stick over the cardinality chip of a building block. Archetype cardinality goes "
                                       "on its plate.")
    y += 9
    cols = int((A4[0] - 2 * MARGIN + GAP) // (CARD_W + GAP))
    stickers = [label for label, n in CARDINALITY for _ in range(n)]
    for i, label in enumerate(stickers):
        r, c = divmod(i, cols)
        p += card_sticker(x0 + c * (CARD_W + GAP), y + r * (CARD_H + GAP), label)
    y += ((len(stickers) - 1) // cols + 1) * (CARD_H + GAP) + 6

    p += heading(x0, y, "Rename", "Stick over the field name, or over the name of an archetype plate. "
                                  "Blank ones: write the new name yourself.")
    y += 9
    cols = int((A4[0] - 2 * MARGIN + GAP) // (NAME_W + GAP))
    stickers = [label for label, n in RENAMES for _ in range(n)]
    rows = int((A4[1] - MARGIN - y + GAP) // (NAME_H + GAP))
    stickers += [None] * (rows * cols - len(stickers))      # fill the page with blank spares
    for i, label in enumerate(stickers):
        r, c = divmod(i, cols)
        p += name_sticker(x0 + c * (NAME_W + GAP), y + r * (NAME_H + GAP), label)
    p.append("</svg>")
    return "\n".join(p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    page = OUT_DIR / ".stickers.svg"
    page.write_text(page_svg(), encoding="utf-8")
    pdf = OUT_DIR / "stickers.pdf"
    subprocess.run(["magick", "-density", "300", str(page), "-units", "PixelsPerInch", "-density", "300", str(pdf)],
                   check=True)
    page.unlink()
    print(f"-> {pdf}")


if __name__ == "__main__":
    main()
