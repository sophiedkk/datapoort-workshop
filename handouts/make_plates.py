#!/usr/bin/env python3
"""Structure pieces for the template: an Encounter baseplate (COMPOSITION) and write-on
Ad hoc heading strips (SECTION), on one A4 page: out/plates.pdf. Also used by make_print.py.

    uv run make_plates.py
"""

import html
import json

from make_bricks import (A4, COLORS_FILE, EXPORT_DIR, FONT_FAMILY, OUT_DIR, is_light, parse_terms, shade,
                         name_and_kind, sheet_header)

COMPOSITION = "openEHR-EHR-COMPOSITION.encounter.v1"
SECTION = "openEHR-EHR-SECTION.adhoc.v1"
PLATE_COLORS = {COMPOSITION: ("Bright Green", "#4B9F4A"), SECTION: ("Light Bluish Gray", "#A0A5A9")}
STRIPS = 5
INK = "#1B1B1B"

esc = html.escape


def ensure_colors():
    colors = json.loads(COLORS_FILE.read_text())
    for aid, (name, hex_) in PLATE_COLORS.items():
        if aid not in colors:
            colors[aid] = {"name": name, "hex": hex_}
    COLORS_FILE.write_text(json.dumps(colors, indent=2) + "\n")
    return colors


def concept(aid):
    path = next(EXPORT_DIR.rglob(f"{aid}.adl"))
    return parse_terms(path.read_text(encoding="utf-8-sig"), "en")["at0000"]


def plate(x, y, w, h, color, header, note, field_label, studs_per_row):
    """A long building-block plate in mm: top face with studs, front face with a write-on sticker."""
    dx, dy = 5.5, -9
    top, side, edge = shade(color, 1.25), shade(color, 0.72), shade(color, 0.55)
    head_ink = INK if is_light(color) else "#FFFFFF"
    p = [
        f'<polygon points="{x},{y} {x + dx},{y + dy} {x + w + dx},{y + dy} {x + w},{y}" fill="{top}" '
        f'stroke="{edge}" stroke-width="0.3" stroke-linejoin="round"/>',
        f'<polygon points="{x + w},{y} {x + w + dx},{y + dy} {x + w + dx},{y + h + dy} {x + w},{y + h}" '
        f'fill="{side}" stroke="{edge}" stroke-width="0.3" stroke-linejoin="round"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="{edge}" stroke-width="0.3"/>',
    ]
    rx, ry, sh = 3.1, 1.2, 1.7
    for t in (0.75, 0.27):                      # back row first
        for i in range(studs_per_row):
            cx = x + w * (i + 0.5) / studs_per_row + dx * t
            cy = y + dy * t - sh + 0.5
            p.append(f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + sh} A{rx},{ry} 0 0 0 {cx + rx},{cy + sh} '
                     f'L{cx + rx},{cy} Z" fill="{side}" stroke="{edge}" stroke-width="0.2"/>')
            p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{top}" stroke="{edge}" '
                     f'stroke-width="0.2"/>')
    # sticker
    sx, sy, sw, sh_ = x + 2.2, y + 2.2, w - 4.4, h - 4.4
    p += [
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh_}" rx="1.6" fill="#fff" stroke="{edge}" '
        f'stroke-width="0.25"/>',
        f'<path d="M{sx},{sy + 5.4} V{sy + 1.6} a1.6,1.6 0 0 1 1.6,-1.6 H{sx + sw - 1.6} '
        f'a1.6,1.6 0 0 1 1.6,1.6 V{sy + 5.4} Z" fill="{color}"/>',
        name_and_kind(header, sx + 3, sy + 3.9, 2.6, head_ink),
        f'<text x="{sx + sw - 3}" y="{sy + 3.9}" font-size="2.1" font-weight="600" fill="{head_ink}" '
        f'text-anchor="end">{esc(note)}</text>',
        f'<text x="{sx + 3}" y="{sy + 9.6}" font-size="2.1" font-weight="800" fill="#555">{esc(field_label)}</text>',
        f'<line x1="{sx + 3}" y1="{sy + sh_ - 3}" x2="{sx + sw - 3}" y2="{sy + sh_ - 3}" stroke="#9A9A9A" '
        f'stroke-width="0.3"/>',
    ]
    return p


def plates_page():
    colors = ensure_colors()
    comp_name, _ = concept(COMPOSITION)
    sect_name, sect_desc = concept(SECTION)
    x, w = 12, A4[0] - 24 - 5.5
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
         f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">',
         '<rect width="100%" height="100%" fill="#fff"/>']
    y = 32
    p.append(sheet_header("Template structure: Encounter and Ad hoc headings", colors[SECTION]["hex"], x - 2))
    p += plate(x, y, w, 30, colors[COMPOSITION]["hex"], (comp_name, "Composition"),
               "Stick this at the top of a flipchart sheet and build downwards", "TEMPLATE NAME", 12)
    y += 30 + 18
    for _ in range(STRIPS):
        p += plate(x, y, w, 22, colors[SECTION]["hex"], (sect_name, "Section"),
                   sect_desc.split(" which")[0] + ": rename it", "SECTION NAME", 12)
        p.append(f'<rect x="{x - 2}" y="{y - 12}" width="{w + 9.5}" height="{22 + 14}" fill="none" '
                 f'stroke="#666" stroke-width="0.3" stroke-dasharray="1.5 1.5"/>')
        y += 22 + 18
    p.append(f'<rect x="{x - 2}" y="{32 - 12}" width="{w + 9.5}" height="{30 + 14}" fill="none" '
             f'stroke="#666" stroke-width="0.3" stroke-dasharray="1.5 1.5"/>')
    p.append("</svg>")
    return "\n".join(p)


def main():
    from make_print import render
    pdf = OUT_DIR / "plates.pdf"
    render([plates_page()], pdf)
    print(f"-> {pdf}")


if __name__ == "__main__":
    main()
