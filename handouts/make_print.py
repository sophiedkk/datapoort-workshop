#!/usr/bin/env python3
"""Combine the workshop materials into two vector PDFs:
out/participant_handouts.pdf (everything on the tables) and
out/facilitator_handouts.pdf (guide with decoys, CKM pile, answers).

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

from make_bricks import A4, COLORS_FILE, DECOY_DIR, EXPORT_DIR, FONT_FAMILY, OUT_DIR, parse_terms, sheet_pages
from make_assignment import answer_key_pages, assignment_pages
from make_plates import COMPOSITION, SECTION, plates_page
from make_stickers import page_svg as sticker_page

HERE = Path(__file__).resolve().parent
PARTICIPANT_PDF = OUT_DIR / "participant_handouts.pdf"
FACILITATOR_PDF = OUT_DIR / "facilitator_handouts.pdf"
TITLE = "Facilitator guide"

# Archetypes held back from the table at the start, by section.
CKM_PILE = ["openEHR-EHR-OBSERVATION.clinical_frailty_scale.v1"]          # handed out at the CKM desk
EXERCISE_3 = "openEHR-EHR-ADMIN_ENTRY.inpatient_admission_details.v0"     # authored by participants
EXCLUDED = {                                                            # in export, not in the workshop
    "openEHR-EHR-CLUSTER.therapeutic_direction.v1",
    "openEHR-EHR-OBSERVATION.falls_risk_assessment.v0",
    "openEHR-EHR-CLUSTER.falls_risk_assessment_extension.v0",
    "openEHR-EHR-OBSERVATION.pulse.v2",                                 # taken off the form: too many vital signs
    "openEHR-EHR-OBSERVATION.pulse_oximetry.v1",
}

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
                 "Per group: a flipchart sheet and tape. It is the baseplate: the template is built on it.",
                 "Hand out the archetype plates first (exercise 0), the building block pages after exercise 0."]:
        y += 5.5
        a(f'<text x="{x + 2}" y="{y}" font-size="3.2" font-weight="600" fill="#333">• {esc(line)}</text>')

    for file_name, print_note, sections in documents:
        y += 13
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

    y += 14
    a(f'<text x="{x}" y="{y}" font-size="4.4" font-weight="800">Building block colours</text>')
    y += 3
    items = sorted(colors.items(), key=lambda kv: names.get(kv[0], kv[0]).lower())
    col_w = (A4[0] - 32) / 2
    for i, (aid, c) in enumerate(items):
        r, col = divmod(i, 2)
        cx, cy = x + col * col_w, y + 3 + r * 9.5
        a(f'<rect x="{cx}" y="{cy}" width="9" height="7" rx="1" fill="{c["hex"]}" stroke="#555" stroke-width="0.2"/>')
        rm = aid.split("-")[2].split(".")[0].replace("_", " ").title()
        a(f'<text x="{cx + 11.5}" y="{cy + 3}" font-size="3.1" font-weight="800">{esc(names.get(aid, aid))}</text>')
        a(f'<text x="{cx + 11.5}" y="{cy + 6.6}" font-size="2.7" font-weight="600" fill="#777">'
          f'{esc(rm)} in {esc(c["name"])}</text>')
        if aid in decoys:
            a(f'<text x="{cx + col_w - 4}" y="{cy + 3}" font-size="2.9" font-weight="800" fill="#C91A09" '
              f'text-anchor="end">DECOY</text>')
    a("</svg>")
    return "\n".join(p)


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
        ("Template structure", "Encounter baseplate (COMPOSITION) and 5 write-on Ad hoc heading strips (SECTION)",
         [plates_page()]),
        ("Archetype plates", "All plates, template archetypes and decoys mixed: hand out first, for exercise 0",
         sheet_pages([plate(aid) for aid in table], "Archetype plates", None, footer=False, gap=4)),
        ("Building blocks", "One sheet per archetype: hand out after exercise 0",
         [pg for aid in table for pg in sheets(aid, names, colors, with_plate=False)]),
        ("Template override stickers", "Cardinality and rename stickers: yellow means changed in the template",
         [sticker_page(1)]),
    ]
    facilitator = [
        ("Answer key", "What each group should end up with, per exercise", answer_key_pages()),
        ("Write-on building blocks", "Black plate and blank building blocks: hand out when a group starts exercise 2",
         sheet_pages([plate(EXERCISE_3)] + [blank] * 6, (names[EXERCISE_3], "Admin Entry (write-on)"),
                     colors[EXERCISE_3]["hex"])),
        ("CKM pile", "Clinical Frailty Scale: the plate for exercise 0, the building block for exercise 1",
         [pg for aid in CKM_PILE for pg in sheet_pages([plate(aid)] + bricks(aid),
                                                       (names[aid], "Observation (CKM pile)"),
                                                       colors[aid]["hex"])]),
        ("Exercise 2 answer building blocks", "The filled-in Inpatient admission details",
         sheets(EXERCISE_3, names, colors, " (answers)")),
    ]

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
        (FACILITATOR_PDF.name, "Guide, answer key and answer blocks once; write-on blocks and CKM pile once per group.", f_rows),
    ]

    render(paginate(participant, 1, p_total), PARTICIPANT_PDF)
    cover = add_footer(cover_page(documents, colors, names, decoys), f"Facilitator guide   1 / {f_total}")
    render([cover] + paginate(facilitator, 2, f_total), FACILITATOR_PDF)
    for (file_name, _, rows), pdf, total in zip(documents, (PARTICIPANT_PDF, FACILITATOR_PDF), (p_total, f_total)):
        print(f"-> {pdf} ({total} pages, {pdf.stat().st_size / 1e6:.1f} MB)")
        for title, _, first, count in rows:
            print(f"   {title}: p. {first}" + (f"–{first + count - 1}" if count > 1 else ""))


if __name__ == "__main__":
    main()
