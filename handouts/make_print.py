#!/usr/bin/env python3
"""Combine the workshop materials into vector PDFs:
out/participant_handouts.pdf (everything on the tables),
out/facilitator_handouts.pdf (guide with decoys, answers),
out/ckm_desk.pdf (the CKM pile and the write-on blocks, printed once per group) and
out/baseplates_A0.pdf (the Encounter baseplates for all groups, on one A0 sheet).

Run make_bricks.py (with --blank for inpatient admission details) first; this script
reads the brick SVGs from out/ and lays them out again, so nothing is re-parsed.
Needs rsvg-convert (librsvg) to turn the SVG pages into PDF.

    uv run make_print.py
"""

import html
import json
import re
import subprocess
import tempfile
from pathlib import Path

from make_bricks import (A4, COLORS_FILE, DECOY_DIR, EXCLUDED, EXPORT_DIR, FONT_FAMILY, OUT_DIR, parse_terms,
                         sheet_pages, text_width)
from make_assignment import answer_key_pages, assignment_pages
from make_plates import (COMPOSITION, GROUPS, SECTION, WRITE_INK, baseplate_piece, baseplates_page, example,
                         heading_piece, plate_write_ins, plates_page)
from make_stickers import NAME_H, card_sticker, name_sticker
from make_stickers import page_svg as sticker_page

HERE = Path(__file__).resolve().parent
PARTICIPANT_PDF = OUT_DIR / "participant_handouts.pdf"
FACILITATOR_PDF = OUT_DIR / "facilitator_handouts.pdf"
CKM_PDF = OUT_DIR / "ckm_desk.pdf"
EXAMPLE_PNG = OUT_DIR / "worked_example.png"
BASEPLATES_PDF = OUT_DIR / "baseplates_A0.pdf"
TITLE = "Facilitator guide"

# Archetypes held back from the table at the start, by section.
CKM_PILE = ["openEHR-EHR-OBSERVATION.clinical_frailty_scale.v1"]          # handed out at the CKM desk
EXERCISE_3 = "openEHR-EHR-ADMIN_ENTRY.inpatient_admission_details.v0"     # authored by participants

# In the export (the COMPLETE template used it) but no longer on the form: printed as a decoy.
FORM_DECOYS = {"openEHR-EHR-OBSERVATION.body_temperature.v2"}

esc = html.escape


def archetype_names():
    names = {}
    for path in [*EXPORT_DIR.rglob("*.adl"), *DECOY_DIR.glob("*.adl")]:
        text = path.read_text(encoding="utf-8-sig")
        aid = re.search(r"openEHR-EHR-[A-Z_]+\.[\w-]+\.v\d+", text).group(0)
        names[aid] = parse_terms(text, "en").get("at0000", (aid,))[0]
    return names


def bricks(aid):
    return [p.read_text(encoding="utf-8") for p in sorted((OUT_DIR / aid).glob("[0-9][0-9]_*.svg"))]


def plate(aid):
    return (OUT_DIR / aid / "plate.svg").read_text(encoding="utf-8")


def sheets(aid, names, colors, suffix="", with_plate=True):
    rm = aid.split("-")[2].split(".")[0].replace("_", " ").title()
    elements = re.search(r'data-elements="([^"]+)"', plate(aid))
    return sheet_pages([plate(aid)] * with_plate + bricks(aid), (names[aid], rm + suffix), colors[aid]["hex"],
                       note=elements.group(1) if elements else "")


def example_parts():
    """The worked example (make_plates.example) in front view: SVG parts in mm, width and height."""
    pieces = {"baseplate": baseplate_piece(), "heading": heading_piece()}
    placed = example()
    top = min(pc["y"] for pc in placed)
    width, height = pieces["baseplate"]["w"], pieces["baseplate"]["h"] - top
    p = []
    for pc in placed:
        if pc["kind"] == "sticker":
            x, y = pc["x"], pc["y"] - top
            if pc["sticker"] == "card":
                p += card_sticker(x, y, pc["label"])
                continue
            p += name_sticker(x, y, pc["label"])
            if pc["ink"]:
                p.append(f'<text x="{x + 3}" y="{y + NAME_H - 2}" font-size="4.8" font-weight="600" '
                         f'fill="{WRITE_INK}">{esc(pc["ink"]["text"])}</text>')
            continue
        if pc["kind"] in pieces:
            piece = pieces[pc["kind"]]
            svg = (f'<svg viewBox="0 0 {piece["w"]} {piece["h"]}">' + "".join(piece["parts"]) + "</svg>")
            writes, w, h = piece["write"], piece["w"], piece["h"]
        else:
            svg = plate(pc["aid"]) if pc["kind"] == "plate" else (OUT_DIR / pc["aid"] / f'{pc["stem"]}.svg').read_text(
                encoding="utf-8")
            cw, ch = (float(v) for v in re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
            svg = re.sub(rf' width="{cw:g}" height="{ch:g}"', "", svg, count=1)
            writes, w, h = (plate_write_ins() if pc["kind"] == "plate" else []), pc["w"], pc["w"] * ch / cw
        x, y = pc["x"], pc["y"] - top
        p.append(svg.replace('<svg', f'<svg x="{x}" y="{y}" width="{w}" height="{h}"', 1)
                    .replace(' xmlns="http://www.w3.org/2000/svg"', "", 1))
        for wr in writes:
            text = pc.get("ink", {}).get(wr["key"], "")
            if not text:
                continue
            size = wr["size"] * w
            tw = text_width(text, size, 600)
            tx = x + wr["x"] * w - (tw / 2 if wr.get("anchor") == "middle" else 0)
            ty = y + wr["y"] * h
            p.append(f'<rect x="{tx - size * 0.2}" y="{ty - size * 1.05}" width="{tw + size * 0.4}" '
                     f'height="{size * 1.05}" fill="#fff"/>')
            p.append(f'<text x="{tx}" y="{ty - size * 0.22}" font-size="{size}" font-weight="600" '
                     f'fill="{WRITE_INK}">{esc(text)}</text>')
    return p, width, height


def example_page():
    """The worked example on a landscape page turned onto A4."""
    p, width, height = example_parts()
    page_w = A4[1]                      # landscape
    k = (page_w - 32) / width
    notes = ["The parts of the form side by side, one stud apart, from left to right: Main Diagnosis, Patient History, "
             "Allergies, Medications, Vital signs, Frailty.",
             "Everything stands on what it belongs to: blocks on their archetype, archetypes on a heading or "
             "on the baseplate, the CLUSTER on its slot block.",
             "The slot block goes on the left of the allergy plate, so the CLUSTER plate can overhang above "
             "Patient History.",
             "Vital signs: one heading; Height, Weight and Blood pressure each stand on the blocks of the one below.",
             "Yellow stickers: the renames of plates and elements (blue ones written on blank stickers) and 1..1 for "
             "Reaction, Systolic and Diastolic."]
    body = ['<text x="16" y="22" font-size="8" font-weight="800" fill="#1B1B1B">Worked example: the answer on '
            'the baseplate</text>',
            f'<g transform="translate(16 32) scale({k})">' + "".join(p) + "</g>"]
    y = 32 + height * k + 10
    for line in notes:
        body.append(f'<text x="16" y="{y}" font-size="3.2" font-weight="600" fill="#333">{esc(line)}</text>')
        y += 5.6
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
            f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">'
            f'<rect width="100%" height="100%" fill="#fff"/>'
            f'<g transform="translate(0 {A4[1]}) rotate(-90)">' + "".join(body) + "</g></svg>")


def add_footer(svg, text):
    footer = (f'<text x="{A4[0] / 2}" y="{A4[1] - 4}" font-family="{FONT_FAMILY}, sans-serif" font-size="2.6" '
              f'font-weight="600" fill="#999" text-anchor="middle">{esc(text)}</text>')
    head, tail = svg.rsplit("</svg>", 1)
    return head + footer + "</svg>" + tail


def cover_page(documents, colors, names, decoys):
    """documents: [(file name, print note, [(title, note, first page, page count), ...]), ...]"""
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
         f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">',
         '<rect width="100%" height="100%" fill="#fff"/>']
    a = p.append
    x, y = 16, 26
    a(f'<text x="{x}" y="{y}" font-size="8" font-weight="800" fill="#1B1B1B">{esc(TITLE)}</text>')
    y += 7
    a(f'<text x="{x}" y="{y}" font-size="3.4" font-weight="600" fill="#C91A09">Keep this to yourself: '
      f'it lists the decoys.</text>')
    y += 12
    a(f'<text x="{x}" y="{y}" font-size="4.4" font-weight="800">Printing</text>')
    for line in ["A4 in colour, at 100% / actual size (not 'fit to page'): building blocks are 90 mm wide.",
                 "Participants cut the building blocks out along the dashed grey lines.",
                 f"{BASEPLATES_PDF.name}: once, on A0 at 100%. Cut out the {GROUPS} Encounter baseplates, "
                 "one per group.",
                 "Per group: a table at least 1.2 m wide. The template is built up from the baseplate.",
                 f"{CKM_PDF.name}: once per group, for the CKM desk: the CKM pile and the exercise 2 write-on blocks.",
                 "Hand out the archetype plates first (exercise 0), the building block pages after exercise 0."]:
        y += 5.5
        a(f'<text x="{x + 2}" y="{y}" font-size="3.2" font-weight="600" fill="#333">• {esc(line)}</text>')

    for file_name, print_note, sections in documents:
        y += 11
        a(f'<text x="{x}" y="{y}" font-size="4.4" font-weight="800">{esc(file_name)}</text>')
        y += 5
        a(f'<text x="{x}" y="{y}" font-size="3" font-weight="600" fill="#C91A09">{esc(print_note)}</text>')
        for title, note, first, count in sections:
            y += 7
            pages = f"p. {first}" if count == 1 else f"p. {first}–{first + count - 1}"
            a(f'<text x="{x + 2}" y="{y}" font-size="3.4" font-weight="800">{esc(title)}</text>')
            a(f'<text x="{A4[0] - 16}" y="{y}" font-size="3.4" font-weight="800" text-anchor="end">{pages}</text>')
            a(f'<text x="{x + 2}" y="{y + 4.2}" font-size="2.9" font-weight="600" fill="#666">{esc(note)}</text>')
            y += 3

    y += 11
    a(f'<text x="{x}" y="{y}" font-size="4.4" font-weight="800">Building block colours</text>')
    y += 3
    items = sorted(colors.items(), key=lambda kv: names.get(kv[0], kv[0]).lower())
    col_w = (A4[0] - 32) / 2
    for i, (aid, c) in enumerate(items):
        r, col = divmod(i, 2)
        cx, cy = x + col * col_w, y + 3 + r * 8.2
        a(f'<rect x="{cx}" y="{cy}" width="9" height="7" rx="1" fill="{c["hex"]}" stroke="#555" stroke-width="0.2"/>')
        rm = aid.split("-")[2].split(".")[0].replace("_", " ").title()
        a(f'<text x="{cx + 11.5}" y="{cy + 3}" font-size="3.1" font-weight="800">{esc(names.get(aid, aid))}</text>')
        a(f'<text x="{cx + 11.5}" y="{cy + 6.6}" font-size="2.7" font-weight="600" fill="#777">'
          f'{esc(rm)} in {esc(c["name"])}</text>')
        if aid in decoys:
            a(f'<text x="{cx + col_w - 4}" y="{cy + 3}" font-size="2.9" font-weight="800" fill="#C91A09" '
              f'text-anchor="end">DECOY</text>')
    assert cy + 7 < A4[1] - 10, f"the facilitator guide's first page overflows ({cy + 7:.0f} mm)"
    a("</svg>")
    return "\n".join(p)


def example_png(path, px_wide=2400):
    """The worked example as a picture (for the README), with a small white margin."""
    p, width, height = example_parts()
    m = 6
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{px_wide}" '
           f'height="{round(px_wide * (height + 2 * m) / (width + 2 * m))}" '
           f'viewBox="{-m} {-m} {width + 2 * m} {height + 2 * m}" font-family="{FONT_FAMILY}, sans-serif">'
           f'<rect x="{-m}" y="{-m}" width="100%" height="100%" fill="#fff"/>' + "".join(p) + "</svg>")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "example.svg"
        src.write_text(svg, encoding="utf-8")
        subprocess.run(["rsvg-convert", "--format", "png", "--output", str(path), str(src)], check=True)


def render(pages, path):
    """SVG pages (A4, in mm) -> one vector PDF, via librsvg's rsvg-convert."""
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i, svg in enumerate(pages):
            files.append(Path(tmp) / f"{i:03d}.svg")
            files[-1].write_text(svg, encoding="utf-8")
        subprocess.run(["rsvg-convert", "--format", "pdf", "--output", str(path), *map(str, files)], check=True)


def main():
    colors = {aid: c for aid, c in json.loads(COLORS_FILE.read_text()).items() if aid not in EXCLUDED}
    names = archetype_names()
    decoys = {aid for aid in colors if aid in FORM_DECOYS or not any(EXPORT_DIR.rglob(f"{aid}.adl"))}

    held_back = set(CKM_PILE) | {EXERCISE_3} | {COMPOSITION, SECTION}
    table = sorted((aid for aid in colors if aid not in held_back), key=lambda aid: names[aid].lower())

    blank = (OUT_DIR / EXERCISE_3 / "blank.svg").read_text(encoding="utf-8")
    participant = [
        ("Assignment", "Exercises and the paper forms", assignment_pages(footer=False)),
        ("Template structure", "5 write-on Ad hoc heading plates (SECTION); the baseplates are on the A0 sheet",
         [plates_page()]),
        ("Archetype plates", "All plates, template archetypes and decoys mixed: hand out first, for exercise 0",
         sheet_pages([plate(aid) for aid in table], "Archetype plates", None, footer=False, gap=4)),
        ("Building blocks", "One sheet per archetype: hand out after exercise 0",
         [pg for aid in table for pg in sheets(aid, names, colors, with_plate=False)]),
        ("Template override stickers", "Cardinality and rename stickers: yellow means changed in the template",
         [sticker_page()]),
    ]
    facilitator = [
        ("Answer key", "What each group should end up with, per exercise", answer_key_pages()),
        ("Worked example", "The answer built on the baseplate (landscape)", [example_page()]),
        ("Exercise 2 answer building blocks", "The filled-in Inpatient admission details",
         sheets(EXERCISE_3, names, colors, " (answers)")),
    ]

    ckm = [pg for aid in CKM_PILE
           for pg in sheet_pages([plate(aid)] + bricks(aid), (names[aid], "Observation (CKM pile)"),
                                 colors[aid]["hex"])]
    ckm += sheet_pages([plate(EXERCISE_3)] + [blank] * 6, (names[EXERCISE_3], "Admin Entry (write-on)"),
                       colors[EXERCISE_3]["hex"])     # exercise 2: hand out when a group starts it

    def contents(plan, first_page):
        rows, n = [], first_page
        for title, note, pages in plan:
            rows.append((title, note, n, len(pages)))
            n += len(pages)
        return rows

    def paginate(plan, first_page, total):
        out, n = [], first_page - 1
        for title, _, pages in plan:
            for pg in pages:
                n += 1
                out.append(add_footer(pg, f"{title}   {n} / {total}"))
        return out

    p_rows = contents(participant, 1)
    p_total = sum(r[3] for r in p_rows)
    a_pages = p_rows[0][3]
    f_rows = contents(facilitator, 2)
    f_total = 1 + sum(r[3] for r in f_rows)
    documents = [
        (PARTICIPANT_PDF.name, f"Assignment (p. 1–{a_pages}): one per participant, double-sided. "
                               f"The rest (p. {a_pages + 1}–{p_total}): once per group.", p_rows),
        (FACILITATOR_PDF.name, "Once: guide, answer key, worked example and the exercise 2 answers.", f_rows),
    ]

    render(paginate(participant, 1, p_total), PARTICIPANT_PDF)
    render([baseplates_page()], BASEPLATES_PDF)
    print(f"-> {BASEPLATES_PDF} (A0, {GROUPS} baseplates)")
    cover = add_footer(cover_page(documents, colors, names, decoys), f"Facilitator guide   1 / {f_total}")
    render([cover] + paginate(facilitator, 2, f_total), FACILITATOR_PDF)
    render([add_footer(pg, f"CKM desk   {i} / {len(ckm)}") for i, pg in enumerate(ckm, 1)], CKM_PDF)
    print(f"-> {CKM_PDF} ({len(ckm)} page(s), once per group)")
    example_png(EXAMPLE_PNG)
    print(f"-> {EXAMPLE_PNG} (the worked example, for the README)")
    for (file_name, _, rows), pdf, total in zip(documents, (PARTICIPANT_PDF, FACILITATOR_PDF), (p_total, f_total)):
        print(f"-> {pdf} ({total} pages, {pdf.stat().st_size / 1e6:.1f} MB)")
        for title, _, first, count in rows:
            print(f"   {title}: p. {first}" + (f"–{first + count - 1}" if count > 1 else ""))


if __name__ == "__main__":
    main()
