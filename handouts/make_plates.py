#!/usr/bin/env python3
"""Structure pieces for the template: the Encounter baseplates (COMPOSITION), eight per A0 sheet
(out/baseplates_A0.pdf), and write-on Ad hoc heading plates (SECTION) on one A4 page (out/plates.pdf).
Also the worked example: where every piece of the answer goes on the baseplate (make_print.py and
make_demo.py draw it).

Everything stands on one stud grid, front view: a building block is 4 studs wide, an archetype plate
and a heading 8, the baseplate 55: six parts of the form of 8 studs side by side, a stud between
two parts and at both ends (cut out, every piece keeps a little white paper around it).

    uv run make_plates.py
"""

import html
import json
import re

from make_bricks import (A4, COLORS_FILE, DX, DY, EXPORT_DIR, FH, FONT_FAMILY, FW, FX, FY, MM_PER_BRICK, OUT_DIR,
                         PH, PLATE_FH, PLATE_FY, PLATE_HB, PW, STUD, STUD_H, STUD_RX, STUD_RY, W, is_light,
                         name_and_kind, parse_terms, shade, sheet_header)

COMPOSITION = "openEHR-EHR-COMPOSITION.encounter.v1"
SECTION = "openEHR-EHR-SECTION.adhoc.v1"
PLATE_COLORS = {COMPOSITION: ("Bright Green", "#4B9F4A"), SECTION: ("Light Bluish Gray", "#A0A5A9")}
HEADINGS = 5
PRELABELLED = "Vital signs"           # printed on one of the heading plates, as an example
INK = "#1B1B1B"

UNIT = MM_PER_BRICK / W                 # mm per unit of the block and plate drawings
STUD_MM = STUD * UNIT                   # 20.25 mm
DEPTH = (DX * UNIT, DY * UNIT)          # top face, the same as on the blocks
HEADING_STUDS, HEADING_H = 8, PLATE_FH * UNIT   # as high as an archetype plate
HEADING_TEXT = 7.9                      # mm: a heading's name, written or printed
GAP_STUDS = 1                           # between two parts of the form and at both ends: room for the paper edges
BASE_STUDS, BASE_H, BASE_K = 6 * 8 + 7 * GAP_STUDS, 60, 2   # BASE_K: text size, relative to a heading
A0 = (1189, 841)                        # landscape
GROUPS = 8                              # baseplates on the A0 sheet: one per group
WRITE_INK = "#1d3f8f"                   # what participants write, in the demo and the worked example

# Pieces in front view, in mm: printed width, and the front face (left, top, bottom, width) inside it.
BLOCK = {"w": MM_PER_BRICK, "face": (FX * UNIT, FY * UNIT, (FY + FH) * UNIT, FW * UNIT)}
PLATE = {"w": PW * UNIT, "face": (FX * UNIT, PLATE_FY * UNIT, (PLATE_FY + PLATE_FH) * UNIT, 2 * FW * UNIT)}

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


# The baseplate's white space, right of the template name: (title, lines) per column, at most four
# lines each. A line starting with ** is printed bold.
BASE_INFO = [
    ("THE EXERCISES: DETAILED STEPS IN THE ASSIGNMENT", [
        "**Exercise 0: Choose the archetypes (the plates)",
        "Plates and grey headings only, keep the blocks aside.",
        "**Exercise 1: Choose the elements (the building blocks)",
        "Keep only the blocks the form needs, add yellow stickers."]),
    ("HOW TO BUILD", ["Everything stands on what it belongs to.",
                      "Higher up = deeper in the template.",
                      "One free stud between two parts of the form.",
                      "Use a grey heading only for a group or a repeating list."]),
    ("ENCOUNTER: ONE CONTACT WITH THE PATIENT", ["Saved as one record (a composition), always with:",
                                                 "Who filled it in (composer)",
                                                 "When and where (start time, care setting)",
                                                 "Language and territory"]),
]
BASE_NAME_W = 280                       # mm of the template name line on the baseplate
BASE_INFO_W = 260                       # mm from one BASE_INFO column to the next


def plate(x, y, studs, h, color, header, note, field_label, k=1, info=(), printed=None):
    """A long building-block plate in mm, `studs` wide: top face with studs on the grid, front face
    with a write-on sticker. k scales the text (the baseplate is higher than a heading). info: columns
    of (title, lines) right of the write-on line (BASE_INFO on the baseplate). printed: (name, size in mm)
    printed on the write-on line instead of leaving it blank."""
    w = studs * STUD_MM
    dx, dy = DEPTH
    top, side, edge = shade(color, 1.25), shade(color, 0.72), shade(color, 0.55)
    head_ink = INK if is_light(color) else "#FFFFFF"
    p = [
        f'<polygon points="{x},{y} {x + dx},{y + dy} {x + w + dx},{y + dy} {x + w},{y}" fill="{top}" '
        f'stroke="{edge}" stroke-width="0.3" stroke-linejoin="round"/>',
        f'<polygon points="{x + w},{y} {x + w + dx},{y + dy} {x + w + dx},{y + h + dy} {x + w},{y + h}" '
        f'fill="{side}" stroke="{edge}" stroke-width="0.3" stroke-linejoin="round"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="{edge}" stroke-width="0.3"/>',
    ]
    rx, ry, sh = STUD_RX * UNIT, STUD_RY * UNIT, STUD_H * UNIT   # the same studs as the blocks
    for t in (0.77, 0.27):                      # back row first
        for i in range(studs):
            cx = x + (i + 0.5) * STUD_MM + dx * t
            cy = y + dy * t - sh + 8 * UNIT
            p.append(f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + sh} A{rx},{ry} 0 0 0 {cx + rx},{cy + sh} '
                     f'L{cx + rx},{cy} Z" fill="{side}" stroke="{edge}" stroke-width="0.2"/>')
            p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{top}" stroke="{edge}" '
                     f'stroke-width="0.2"/>')
    # sticker
    sx, sy, sw, sh_ = x + 2.2 * k, y + 2.2 * k, w - 4.4 * k, h - 4.4 * k
    r = 1.6 * k
    p += [
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh_}" rx="{r}" fill="#fff" stroke="{edge}" '
        f'stroke-width="0.25"/>',
        f'<path d="M{sx},{sy + 5.4 * k} V{sy + r} a{r},{r} 0 0 1 {r},-{r} H{sx + sw - r} '
        f'a{r},{r} 0 0 1 {r},{r} V{sy + 5.4 * k} Z" fill="{color}"/>',
        name_and_kind(header, sx + 3 * k, sy + 3.9 * k, 2.6 * k, head_ink),
        f'<text x="{sx + sw - 3 * k}" y="{sy + 3.9 * k}" font-size="{2.1 * k}" font-weight="600" fill="{head_ink}" '
        f'text-anchor="end">{esc(note)}</text>',
        f'<text x="{sx + 3 * k}" y="{sy + 9.6 * k}" font-size="{2.1 * k}" font-weight="800" fill="#555">'
        f'{esc(field_label)}</text>',
        f'<line x1="{sx + 3 * k}" y1="{sy + sh_ - 3 * k}" x2="{sx + (BASE_NAME_W if info else sw - 3 * k)}" '
        f'y2="{sy + sh_ - 3 * k}" stroke="#9A9A9A" stroke-width="0.3"/>',
    ]
    if printed:
        p.append(f'<text x="{x + 5.2 * k}" y="{y + h - 6.8 * k}" font-size="{printed[1]}" font-weight="700" '
                 f'fill="{INK}">{esc(printed[0])}</text>')
    for i, (title, lines) in enumerate(info):
        cx = sx + BASE_NAME_W + 30 + i * BASE_INFO_W
        p.append(f'<text x="{cx}" y="{sy + 9.6 * k}" font-size="{2.1 * k}" font-weight="800" fill="#555">'
                 f'{esc(title)}</text>')
        for j, line in enumerate(lines):
            bold = line.startswith("**")
            p.append(f'<text x="{cx}" y="{sy + 9.6 * k + 7.4 + j * 7}" font-size="6.2" '
                     f'font-weight="{800 if bold else 600}" fill="{INK}">{esc(line.removeprefix("**"))}</text>')
    return p


def strip_piece(aid, studs, h, note, label, k=1, text_mm=HEADING_TEXT, info=(), printed=""):
    """A heading or the baseplate as a piece of its own (front view, mm): its SVG parts, size, front
    face and where its name is written (fractions of the piece, like the demo's write-ins)."""
    kind = "Composition" if aid == COMPOSITION else "Section"
    top = 11                                    # room for the top face and the studs
    vw, vh = studs * STUD_MM + 7.5, h + top + 1.5
    parts = plate(1, top, studs, h, ensure_colors()[aid]["hex"], (concept(aid)[0], kind), note, label, k, info,
                  (printed, text_mm) if printed else None)
    write = {"key": "name", "x": (1 + 5.2 * k) / vw, "y": (top + h - 6.8 * k) / vh, "size": text_mm / vw,
             "bg": True, "prompt": label.capitalize()}
    return {"parts": parts, "w": vw, "h": vh, "face": (1, top, top + h, studs * STUD_MM),
            "write": [] if printed else [write]}


def heading_piece(printed=""):
    """A write-on heading, or with its name already printed on it."""
    _, sect_desc = concept(SECTION)
    return strip_piece(SECTION, HEADING_STUDS, HEADING_H, sect_desc.split(" which")[0] + ": rename it",
                       "SECTION NAME", printed=printed)


def baseplate_piece():
    return strip_piece(COMPOSITION, BASE_STUDS, BASE_H, "The template: everything stands on this baseplate",
                       "TEMPLATE NAME", k=BASE_K, text_mm=16, info=BASE_INFO)


def plate_write_ins():
    """Where an archetype plate's cardinality line is, as fractions of the plate (renames go on a sticker)."""
    fy, fh = PLATE_FY, PLATE_FH
    sx, sy, sw = FX + 30, fy + 26, 2 * FW - 60
    line_y = (sy + fh - 52 - 26) / PH
    split = sx + sw - 40 - 560
    return [{"key": "card", "x": (split + 280) / PW, "y": line_y, "size": 0.032, "anchor": "middle", "bg": True,
             "prompt": "Cardinality, e.g. 0..1 or 0..*"}]


# --------------------------------------------------------------------------- worked example

def block_stem(aid, name):
    """File name of a building block, e.g. "manifestation" -> "03_manifestation": the numbers depend on
    which blocks make_bricks.py selected."""
    found = sorted((OUT_DIR / aid).glob(f"[0-9][0-9]_{name}.svg"))
    if not found:
        raise SystemExit(f"No building block {name!r} for {aid}: run make_bricks.py first")
    return found[0].stem


O = "openEHR-EHR-OBSERVATION."
EXAMPLE_NAME = "Nursing Admission Assessment"


def example():
    """The answer key on the baseplate, in the order of the form, left to right, with its stickers.

    Returns the pieces in build order (lower pieces first, stickers last) as dicts: kind (baseplate,
    heading, plate, block, sticker), aid, stem (a block's file name), sticker ("name" or "card") and
    label (printed on it, None for a blank one), x, y (top left, mm, the baseplate's top left at 0, 0),
    w (printed width, mm) and ink (what is written on it)."""
    out = []
    base = baseplate_piece()
    out.append({"kind": "baseplate", "aid": COMPOSITION, "x": 0, "y": 0, "w": base["w"],
                "ink": {"name": EXAMPLE_NAME}})
    left0, floor = base["face"][0], base["face"][1]
    heading = heading_piece()

    def put(kind, piece, stud, bottom, **more):
        """Front face starting `stud` studs from the baseplate's left end, standing on `bottom`."""
        fx, ft, fb, _ = piece["face"]
        out.append({"kind": kind, "x": left0 + stud * STUD_MM - fx, "y": bottom - fb, "w": piece["w"], **more})
        return bottom - (fb - ft)

    def arch(aid, stud, bottom, blocks, name="", card="0..1"):
        """An archetype plate with its blocks side by side; returns the top of the first block."""
        top = put("plate", PLATE, stud, bottom, aid=aid, ink={"card": card}, rename=name)
        return [put("block", BLOCK, stud + 4 * i, top, aid=aid, stem=block_stem(aid, b))
                for i, b in enumerate(blocks)][0]

    reaction = "openEHR-EHR-CLUSTER.adverse_reaction_event.v1"

    def section(stud, name):
        if name == PRELABELLED:
            return put("heading", heading, stud, floor, aid=SECTION, ink={}, label=name)
        return put("heading", heading, stud, floor, aid=SECTION, ink={"name": name})

    col = [GAP_STUDS + (8 + GAP_STUDS) * i for i in range(6)]
    arch("openEHR-EHR-EVALUATION.problem_diagnosis.v1", col[0], floor, ["problem_diagnosis_name"],
         "Main Diagnosis")
    arch(O + "story.v1", col[1], floor, ["story"], "Patient History")
    # the slot block goes on the left: the CLUSTER plate on it overhangs 4 studs, above the gap and Patient History
    slot = arch("openEHR-EHR-EVALUATION.adverse_reaction_risk.v2", col[2], section(col[2], "Allergies"),
                ["reaction_event_summary", "substance"], card="0..*")
    top = put("plate", PLATE, col[2] - 4, slot, aid=reaction, ink={"card": "0..1"})
    put("block", BLOCK, col[2], top, aid=reaction, stem=block_stem(reaction, "manifestation"))
    arch("openEHR-EHR-INSTRUCTION.medication_order.v3", col[3], section(col[3], "Medications"),
         ["medication_item", "overall_directions_description"], card="0..*")
    # more than one archetype under a heading: each stands on the blocks of the one below
    top = arch(O + "height.v2", col[4], section(col[4], "Vital signs"), ["height_length"])
    top = arch(O + "body_weight.v2", col[4], top, ["weight"])
    arch(O + "blood_pressure.v2", col[4], top, ["systolic", "diastolic"])   # only the capitals differ: no rename
    arch(O + "clinical_frailty_scale.v1", col[5], floor, ["assessment"])
    return out + stickers(out)


# Yellow stickers of the answer key, per building block (its file name without the number):
# (new name, stricter cardinality).
# Allergy, Reaction and Directions are printed on the sticker sheet, the other names are written on blanks.
EXAMPLE_STICKERS = {
    "story": ("Patient's story", None),
    "substance": ("Allergy", None),
    "manifestation": ("Reaction", "1..1 required"),
    "medication_item": ("Name", None),
    "overall_directions_description": ("Directions", None),
    "height_length": ("Height", None),
    "systolic": (None, "1..1 required"),
    "diastolic": (None, "1..1 required"),
}


def stickers(placed):
    """Rename stickers over a block's field name or a plate's archetype name, cardinality stickers over a
    block's cardinality chip."""
    from make_stickers import CARD_H, CARD_W, NAME_H, NAME_W, RENAMES
    printed = {label for label, _ in RENAMES if label}
    out = []
    for pc in placed:
        if pc.get("rename"):                    # on the plate's header, over the archetype name
            label = pc["rename"] if pc["rename"] in printed else None
            out.append({"kind": "sticker", "sticker": "name", "label": label, "w": NAME_W,
                        "x": pc["x"] + (FX + 30 + 40) * UNIT - 3,
                        "y": pc["y"] + (PLATE_FY + 26 + PLATE_HB / 2) * UNIT - NAME_H / 2,
                        "ink": {} if label else {"text": pc["rename"]}})
        if pc["kind"] != "block" or pc["stem"][3:] not in EXAMPLE_STICKERS:
            continue
        name, card = EXAMPLE_STICKERS[pc["stem"][3:]]
        svg = (OUT_DIR / pc["aid"] / f'{pc["stem"]}.svg').read_text(encoding="utf-8")
        if name:                                # just under the header, over the field name
            label = name if name in printed else None
            out.append({"kind": "sticker", "sticker": "name", "label": label, "w": NAME_W,
                        "x": pc["x"] + (FX + 34 + 44) * UNIT - 3, "y": pc["y"] + (FY + 32 + 96 + 8) * UNIT,
                        "ink": {} if label else {"text": name}})
        if card:                                # centred on the cardinality chip (the second chip)
            chip_x, chip_y = (float(v) for v in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="\d+" '
                                                            r'height="58" rx="29"', svg)[1])
            out.append({"kind": "sticker", "sticker": "card", "label": card, "w": CARD_W,
                        "x": pc["x"] + chip_x * UNIT - 1.5, "y": pc["y"] + (chip_y + 29) * UNIT - CARD_H / 2,
                        "ink": {}})
    return out


# --------------------------------------------------------------------------- pages


def plates_page():
    """A4: the write-on Ad hoc heading plates for one group."""
    colors = ensure_colors()
    sect_name, sect_desc = concept(SECTION)
    w = HEADING_STUDS * STUD_MM
    x = (A4[0] - w - DEPTH[0]) / 2
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
         f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">',
         '<rect width="100%" height="100%" fill="#fff"/>']
    y = 36
    p.append(sheet_header("Template structure: Ad hoc headings", colors[SECTION]["hex"], x - 2))
    for i in range(HEADINGS):
        p += plate(x, y, HEADING_STUDS, HEADING_H, colors[SECTION]["hex"], (sect_name, "Section"),
                   sect_desc.split(" which")[0] + ": rename it", "SECTION NAME",
                   printed=(PRELABELLED, HEADING_TEXT) if i == 0 else None)
        p.append(f'<rect x="{x - 2}" y="{y - 12}" width="{w + 9.5}" height="{HEADING_H + 14}" fill="none" '
                 f'stroke="#666" stroke-width="0.3" stroke-dasharray="1.5 1.5"/>')
        y += HEADING_H + 22
    p.append("</svg>")
    return "\n".join(p)


def baseplates_page():
    """A0 landscape: one Encounter baseplate per group, each in one piece."""
    colors = ensure_colors()
    comp_name, _ = concept(COMPOSITION)
    w = BASE_STUDS * STUD_MM
    x = (A0[0] - w - DEPTH[0]) / 2
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A0[0]}mm" height="{A0[1]}mm" '
         f'viewBox="0 0 {A0[0]} {A0[1]}" font-family="{FONT_FAMILY}, sans-serif">',
         '<rect width="100%" height="100%" fill="#fff"/>',
         f'<text x="{x}" y="30" font-size="9" font-weight="800" fill="{INK}">Encounter baseplates: one per group'
         f'</text>',
         f'<text x="{x + w}" y="30" font-size="6" font-weight="600" fill="#888" text-anchor="end">'
         f'✂ cut along the dashed lines</text>']
    step = (A0[1] - 60) / GROUPS
    for i in range(GROUPS):
        y = 60 + i * step + (step - BASE_H) / 2
        p += plate(x, y, BASE_STUDS, BASE_H, colors[COMPOSITION]["hex"], (comp_name, "Composition"),
                   "The template: everything stands on this baseplate", "TEMPLATE NAME", BASE_K, BASE_INFO)
        p.append(f'<rect x="{x - 3}" y="{y - 14}" width="{w + DEPTH[0] + 6}" height="{BASE_H + 17}" fill="none" '
                 f'stroke="#666" stroke-width="0.5" stroke-dasharray="3 3"/>')
    p.append("</svg>")
    return "\n".join(p)


def main():
    from make_print import render
    for page, name in ((plates_page(), "plates.pdf"), (baseplates_page(), "baseplates_A0.pdf")):
        render([page], OUT_DIR / name)
        print(f"-> {OUT_DIR / name}")


if __name__ == "__main__":
    main()
