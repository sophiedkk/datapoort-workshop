#!/usr/bin/env python3
"""Participant assignment for the building block workshop, as A4 pages: out/assignment.pdf.

Adapted from the practical modelling tasks by Ian McNicoll (freshEHR), as extended by the Hanze for EHRCON26
(https://freshehrteam.github.io/openehr-workshop/exercises/) for paper bricks and stickers.
Also used by make_print.py, which puts these pages in the print pack.

    uv run make_assignment.py
"""

import base64
import html
import json
import re
from pathlib import Path

from PIL import ImageFont

from make_bricks import A4, COLORS_FILE, FONT_FAMILY, OUT_DIR, W, H, font_file

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
TITLE = "Assignment"

ML, MR, MT, MB = 16, 16, 16, 16          # page margins (mm)
TEXT_W = A4[0] - ML - MR
INK, MUTED, YELLOW = "#1B1B1B", "#666666", "#FFE14D"

esc = html.escape

# --------------------------------------------------------------------------- content
# Inline markup: **bold**. Archetype swatches use the archetype id (colour from colors.json).

BP = "openEHR-EHR-OBSERVATION.blood_pressure.v2"
CONTENT = [
    ("h1", "Build a template with building blocks"),
    ("sub", "Practical clinical modelling with the Nursing Admission Assessment"),
    ("p", "In this practical you build the **Nursing Admission Assessment** template on paper, "
          "block by block. Archetypes are deliberately broad so they can be reused everywhere; "
          "template design means narrowing each archetype down to what this specific form needs, "
          "and pulling in extra archetypes for what is still missing."),
    ("p", "Based on the openEHR practical modelling tasks by Ian McNicoll (freshEHR), with additions by the Hanze "
          "for EHRCON26. If you want to "
          "explore further, the online version of the workshop is at "
          "**freshehrteam.github.io/openehr-workshop**"),

    ("h2", "Your materials"),
    ("h4", "Building blocks"),
    ("legend", BP + "/01_systolic.svg", [
        "**One building block = one data element** of an archetype. Same colour = same archetype.",
        "**Header:** the archetype it belongs to, and its entry type.",
        "**Chips:** the data type, and the cardinality the archetype allows: "
        "**0..1** optional, **1..1** required, **0..*** repeats.",
        "**Grey text** under the name: what the element is for, taken from the archetype.",
        "**Code at the bottom:** a SNOMED CT or LOINC code from the archetype, if it has one.",
    ]),
    ("h4", "The baseplate, headings and plates"),
    ("bullets", [
        "**Green Encounter baseplate = the template** (COMPOSITION). Lay it along the edge of your table: you "
        "build the template up from it, seen from the front, like a wall of building blocks.",
        "**Grey plates = Ad hoc heading** (SECTION): a generic heading; write its name on the plate.",
        "**Coloured plates = archetypes.** One per archetype, in its own colour, two building blocks wide. "
        "Write the cardinality the archetype gets in your template on the plate; a new name goes on a yellow "
        "sticker over the archetype's name.",
        "**Everything stands on what it belongs to**, lined up with the studs: building blocks on their "
        "archetype plate, an archetype plate on a heading or on the baseplate. The higher up, the deeper in "
        "the template.",
    ]),
    ("h4", "Changing the template"),
    ("bullets", [
        "**Remove an element** from the template (constrain it out, 0..0): take its building block off the template. "
        "It stays in the archetype, just not in this form.",
        "**Yellow stickers = template changes:** a new name, or a stricter cardinality. "
        "A template can only **narrow** what the archetype allows: going from 0..1 to 1..1 is fine, going from 0..1 to 0..* is not.",
    ]),

    ("h2", "Exercise 0: Choose the archetypes"),
    ("p", "Start with the big picture: which archetypes does this form need? Use only the green Encounter, "
          "the grey headings and the archetype plates for now, and keep the building blocks aside."),
    ("bullets", [
        "Build on the green **Encounter** baseplate: the parts of the form from left to right, in the same "
        "order as on the form, side by side with one free stud between them.",
        "Not every part of the form needs a grey heading: an archetype's name already works as a heading "
        "(and you can rename it to match the form). Use a heading (**SECTION**) only to group several "
        "archetypes, or to put one heading above a list that repeats. Write the names on the grey plates.",
        "Several archetypes under one heading? Stack them on the heading, one on top of the other.",
        "Find an archetype plate for each part of the form. Not every plate belongs in your template, and some "
        "parts need more than one.",
        "Read the purpose and the entry type (OBSERVATION, EVALUATION, INSTRUCTION, CLUSTER) on each plate: "
        "does it fit what the form records?",
        "Can the form hold more than one of something? Fill in the cardinality on that archetype's plate.",
        "Found a dashed CLUSTER plate you need? Put it on top of the archetype it slots into.",
        "Is there something on the form that none of the plates covers? Go to the **CKM desk** (your "
        "facilitator) and describe what you're looking for, as precisely as you can.",
        "Medications: in openEHR, the list of medication a patient uses is made of medication orders, even "
        "when someone else (such as the GP) prescribed them.",
    ]),

    ("h2", "Exercise 1: Choose the elements"),
    ("p", "Now take the building blocks of the archetypes you chose, and put them on their plates. Archetypes "
          "are deliberately broad, so most blocks won't be needed: narrow each archetype down to what this "
          "form needs. We do 1.1 together; from 1.2 on, the steps say what the form needs, not which block "
          "to use."),
    ("h3", "1.1 Main diagnosis (together)", None),
    ("bullets", [
        "Rename the **Problem/Diagnosis** archetype to **Main Diagnosis**: write the new name on a blank yellow "
        "sticker and stick it over the name on its plate.",
        "Constrain out everything apart from **Problem/Diagnosis name**: take the other blocks off the plate.",
    ]),

    ("h3", "1.2 Patient history, medication and vital signs", None),
    ("bullets", [
        "Keep only the blocks the form needs for **Patient history**, the **name of the medication**, and the "
        "vital signs **Height**, **Weight** and **Blood pressure**.",
        "Which blood pressure values should never be left empty? Make them mandatory.",
    ]),

    ("h3", "1.3 Allergies", None),
    ("bullets", [
        "Keep only the element that says what the patient is allergic to, and rename it to match the form.",
        "The reaction is a CLUSTER. Find the building block on the allergy archetype that it slots into "
        "(the CLUSTER slot: its studs have the colour of the reaction plate), and put the reaction plate on top "
        "of that block. The plate is wider than the block: let it hang over the side where there is room.",
        "Keep only the element that describes how the reaction showed itself. Rename it to match the form, and "
        "make it mandatory.",
    ]),

    ("h3", "1.4 Medication directions", None),
    ("p", "In the **medication** list on the form, the 'Directions' column holds the prescriber's directions "
          "for each medication: how much, and how often. There is no element called Dose or Frequency."),
    ("bullets", [
        "Look at the **Medication order** elements about directions and read their descriptions. Which one "
        "covers the whole of the directions?",
        "Keep that element and rename it to match the form.",
    ]),

    ("h3", "1.5 Frailty", None),
    ("bullets", [
        "Keep the element that holds the frailty score.",
    ]),

    ("h2", "Exercise 2: Create a new local archetype"),
    ("p", "The nurses want to record **additional information on admission** (paper form below). CKM has no "
          "suitable archetype, so you make a new **ADMIN_ENTRY**: admission logistics, not a clinical finding."),
    ("bullets", [
        "Get the black plate and the **write-on building blocks** from the CKM desk: archetype **Inpatient "
        "admission details**.",
        "Make one building block per question on the form: write its name and values, tick the data type, "
        "and fill in the cardinality.",
        "Which data type lets a nurse pick from a list, or write something under 'Other'?",
        "Can more than one 'Transported with' apply? What does that mean for the cardinality?",
        "Where would your new archetype go in the template: under a heading, or straight on the Encounter? "
        "It doesn't need to go on the baseplate.",
    ]),
    ("space", 4),
    ("image", "additional-info.png", 112, "Paper form: Additional information on admission"),

    ("pagebreak",),
    ("h2", "The paper form: Nursing Admission Assessment"),
    ("image", "nursing-admission.png", 178, None),
]

# --------------------------------------------------------------------------- text measuring

_fonts = {}


def font(weight):
    if weight not in _fonts:
        if weight >= 800:
            _fonts[weight] = ImageFont.truetype(str(font_file("Lexend-ExtraBold.ttf")), 100)
        else:
            f = ImageFont.truetype(str(font_file("Lexend-VariableFont_wght.ttf")), 100)
            f.set_variation_by_axes([weight])
            _fonts[weight] = f
    return _fonts[weight]


def width(text, size, weight):
    return font(weight).getlength(text) / 100 * size


def tokens(rich, base_weight):
    """'a **b**, c' -> [(word, weight, glued_to_previous), ...]"""
    out, pending_space = [], False
    for i, part in enumerate(re.split(r"\*\*", rich)):
        weight = 800 if i % 2 else base_weight
        for m in re.finditer(r"(\s*)(\S+)", part):
            glued = bool(out) and not m.group(1) and not pending_space
            out.append((m.group(2), weight, glued))
            pending_space = False
        pending_space = part[-1:].isspace() if part else pending_space
    return out


def wrap_rich(rich, size, max_w, base_weight=400):
    """Wrap on whole groups: words glued together without a space, like '(**SECTION**)', never split
    across lines (and never overflow because only the first part was checked)."""
    groups = []
    for word, weight, glued in tokens(rich, base_weight):
        if glued and groups:
            groups[-1].append((word, weight))
        else:
            groups.append([(word, weight)])
    lines, line, x = [], [], 0.0
    space = width(" ", size, base_weight)
    for group in groups:
        w = sum(width(word, size, weight) for word, weight in group)
        if line and x + space + w > max_w:
            lines.append(line)
            line, x = [], 0.0
        if line:
            x += space
        for i, (word, weight) in enumerate(group):
            line.append((word, weight, i > 0 or not line))
        x += w
    if line:
        lines.append(line)
    return lines


def text_line(line, x, y, size, fill=INK):
    """One <text> per line; tspans per weight, spacing left to the renderer (xml:space=preserve)."""
    spans = []
    for word, weight, glued in line:
        chunk = esc(word if glued else " " + word)
        if spans and spans[-1][0] == weight:
            spans[-1][1] += chunk
        else:
            spans.append([weight, chunk])
    body = "".join(f'<tspan font-weight="{w}">{t}</tspan>' for w, t in spans)
    return [f'<text xml:space="preserve" x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}">{body}</text>']


def justified_line(line, x, y, size, width_mm, fill=INK):
    """Spread a line over width_mm: words glued to punctuation stay together, the gaps between
    them grow. librsvg ignores word-spacing and textLength, so each group gets its own x."""
    groups = []
    for word, weight, glued in line:
        if glued and groups:
            groups[-1].append((word, weight))
        else:
            groups.append([(word, weight)])
    widths = [sum(width(w, size, wt) for w, wt in g) for g in groups]
    space = width(" ", size, 400)
    gap = (width_mm - sum(widths)) / (len(groups) - 1) if len(groups) > 1 else 0
    if len(groups) < 2 or gap > 3 * space or gap < space * 0.5:
        return text_line(line, x, y, size, fill)          # too stretched (or squeezed): leave ragged
    out, gx = [], x
    for g, w in zip(groups, widths):
        body = "".join(f'<tspan font-weight="{wt}">{esc(word)}</tspan>' for word, wt in g)
        out.append(f'<text xml:space="preserve" x="{gx:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}">'
                   f'{body}</text>')
        gx += w + gap
    return out


# --------------------------------------------------------------------------- layout

class Pages:
    def __init__(self, colors):
        self.colors = colors
        self.pages = []
        self.new_page()

    def new_page(self):
        self.parts = []
        self.pages.append(self.parts)
        self.y = MT

    def need(self, h):
        if self.y + h > A4[1] - MB:
            self.new_page()

    def para(self, rich, size=3.3, x=ML, w=TEXT_W, fill=INK, gap=2.6, base_weight=400, justify=False):
        lh = size * 1.45
        lines = wrap_rich(rich, size, w, base_weight)
        for i, line in enumerate(lines):
            self.need(lh)
            self.y += lh
            baseline = self.y - lh * 0.28
            if justify and i < len(lines) - 1:              # last line of a paragraph stays ragged
                self.parts += justified_line(line, x, baseline, size, w, fill)
            else:
                self.parts += text_line(line, x, baseline, size, fill)
        self.y += gap

    def bullets(self, items, x=ML, w=TEXT_W, size=3.3, justify=True):
        for item in items:
            lines = wrap_rich(item, size, w - 5)
            self.need(size * 1.45 * len(lines))             # keep a bullet together on one page
            y0 = self.y
            self.para(item, size=size, x=x + 5, w=w - 5, gap=1.2, justify=justify)
            self.parts.append(f'<circle cx="{x + 1.6}" cy="{y0 + size * 1.45 * 0.5:.2f}" r="0.75" fill="{INK}"/>')
        self.y += 1.6

    def swatch(self, aid, x, y, w=6, h=4.2):
        c = self.colors.get(aid, {"hex": "#ccc"})["hex"]
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="0.8" fill="{c}" '
                          f'stroke="#555" stroke-width="0.2"/>')

    def heading(self, text, size, gap_before, aid=None):
        self.need(gap_before + size * 1.4 + (28 if size > 5 else 16))
        self.y += gap_before + size
        x = ML
        if aid:
            self.swatch(aid, ML, self.y - size * 0.82, w=size * 1.4, h=size * 0.9)
            x += size * 1.4 + 2.5
        self.parts.append(f'<text x="{x}" y="{self.y:.2f}" font-size="{size}" font-weight="800" '
                          f'fill="{INK}">{esc(text)}</text>')
        self.y += size * 0.55

    def tip(self, rich):
        size, pad = 3.2, 3
        lines = wrap_rich(rich, size, TEXT_W - 2 * pad)
        h = len(lines) * size * 1.45 + 2 * pad - 1
        self.need(h)
        self.parts.append(f'<rect x="{ML}" y="{self.y:.2f}" width="{TEXT_W}" height="{h:.2f}" rx="2" '
                          f'fill="#FBEDC4" stroke="#DCC27A" stroke-width="0.25"/>')
        self.y += pad - 1
        self.para(rich, size=size, x=ML + pad, w=TEXT_W - 2 * pad, gap=0)
        self.y += pad + 2.5

    def legend(self, brick_rel, items):
        bw = 74
        bh = bw * H / W
        brick = (OUT_DIR / brick_rel).read_text(encoding="utf-8")
        brick = brick.replace('<svg xmlns="http://www.w3.org/2000/svg"',
                              f'<svg x="{ML + TEXT_W - bw}" y="{self.y:.2f}" width="{bw}" height="{bh:.2f}"', 1)
        brick = re.sub(rf' width="{W}" height="{H}"', "", brick, count=1)
        self.need(bh)
        top = self.y
        self.parts.append(brick)
        self.bullets(items, x=ML, w=TEXT_W - bw - 5, size=3.1, justify=False)
        self.y = max(self.y, top + bh + 3)

    def swatches(self, rows):
        size = 3.2
        for aid, name, note in rows:
            lines = wrap_rich(f"**{name}** {note}", size, TEXT_W - 12)
            self.need(len(lines) * size * 1.45)
            self.swatch(aid, ML + 2, self.y + 0.9, w=7, h=3.6)
            self.para(f"**{name}** {note}", size=size, x=ML + 12, w=TEXT_W - 12, gap=0.8)
        self.y += 1.8

    def table(self, rows):
        size, col = 3.2, 52
        for label, values in rows:
            lines = wrap_rich(values, size, TEXT_W - col - 4)
            h = len(lines) * size * 1.45 + 2.4
            self.need(h)
            self.parts.append(f'<rect x="{ML}" y="{self.y:.2f}" width="{TEXT_W}" height="{h:.2f}" fill="#F3F3F3" '
                              f'stroke="#DDD" stroke-width="0.2"/>')
            y0 = self.y + 1.2
            self.y = y0
            self.para(f"**{label}**", size=size, x=ML + 2.5, w=col - 4, gap=0)
            self.y = y0
            self.para(values, size=size, x=ML + col, w=TEXT_W - col - 4, gap=0)
            self.y = y0 - 1.2 + h + 0.8
        self.y += 2.4

    def image(self, name, w, caption):
        path = ASSETS / name
        from PIL import Image
        iw, ih = Image.open(path).size
        h = w * ih / iw
        self.need(h + (6 if caption else 0))
        data = base64.b64encode(path.read_bytes()).decode()
        x = ML + (TEXT_W - w) / 2
        self.parts.append(f'<rect x="{x - 0.5}" y="{self.y - 0.5:.2f}" width="{w + 1}" height="{h + 1:.2f}" '
                          f'fill="none" stroke="#CCC" stroke-width="0.25"/>')
        self.parts.append(f'<image x="{x}" y="{self.y:.2f}" width="{w}" height="{h:.2f}" '
                          f'href="data:image/png;base64,{data}"/>')
        self.y += h + 1.5
        if caption:
            self.para(caption, size=2.9, x=x, w=w, fill=MUTED)
        self.y += 2

    def svgs(self, footer=True):
        total = len(self.pages)
        out = []
        for n, parts in enumerate(self.pages, 1):
            out.append("\n".join([
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
                f'viewBox="0 0 {A4[0]} {A4[1]}" font-family="{FONT_FAMILY}, sans-serif">',
                '<rect width="100%" height="100%" fill="#fff"/>',
                *parts,
                (f'<text x="{A4[0] / 2}" y="{A4[1] - 6}" font-size="2.6" font-weight="600" fill="#999" '
                 f'text-anchor="middle">{esc(TITLE)}   {n} / {total}</text>' if footer else ""),
                "</svg>"]))
        return out


ANSWERS = [
    ("h1", "Answer key"),
    ("sub", "Based on the Nursing Admission Assessment COMPLETE template"),
    ("h2", "Exercise 0: Archetypes"),
    ("table", [
        ("Structure", "Main diagnosis, Patient history and Frailty straight on the Encounter baseplate, without a "
                      "heading: the (renamed) archetype is the heading. Ad hoc headings: **Vital signs** (three "
                      "archetypes stacked on it), **Allergies** and **Medications** (one heading above a repeating "
                      "list, 0..*). Two of the five heading plates stay unused. The worked example shows it built."),
        ("Main diagnosis", "**Problem/Diagnosis** (EVALUATION)."),
        ("Patient history", "**Story/History** (OBSERVATION)."),
        ("Allergies", "**Adverse reaction risk** (EVALUATION), with **Adverse reaction event** (CLUSTER) "
                      "for the reaction."),
        ("Medications", "**Medication order** (INSTRUCTION): in openEHR a current medication list is built from "
                        "medication orders, also for medication prescribed elsewhere. Discussion point: the "
                        "'Medication use statement' (OBSERVATION.medication_statement) fits 'medication used at "
                        "admission' better, but is still an unpublished draft on CKM."),
        ("Vital signs", "**Height/Length**, **Body weight**, **Blood pressure**."),
        ("Frailty", "**Clinical Frailty Scale (CFS)** from the CKM desk."),
        ("Decoys", "Respiration and Body temperature (vital signs, not on the form), Body Mass Index (derived "
                   "from height and weight)."),
        ("Cardinality", "Adverse reaction risk **0..*** and Medication order **0..***: several allergies or "
                        "medications. The rest 0..1. Adverse reaction event 0..1 in its slot."),
    ]),
    ("h2", "Exercise 1: Elements"),
    ("table", [
        ("1.1 Main diagnosis", "Plate renamed **Main Diagnosis**; keep **Problem/Diagnosis name**."),
        ("1.2 Other parts", "Story/History: **Story**. Medication order: **Medication item**. "
                               "Height/Length: **Height/Length**. Body weight: **Weight**. Blood pressure: **Systolic** "
                               "and **Diastolic**, both **1..1**."),
        ("1.2 Optional renames", "The template renames to the form's labels: plate Story/History to **Patient "
                                 "History**; elements Story to **Patient's story**, Medication item to **Name**, "
                                 "Height/Length to **Height**. Other names that match the form are fine too. No "
                                 "rename where only the capital letters differ (Blood pressure)."),
        ("1.3 Allergies", "Keep **Substance**, renamed **Allergy**. Adverse reaction event on the slot block "
                          "**Reaction event summary**, which goes on the left so the CLUSTER plate can hang over "
                          "Patient History. Keep **Manifestation**, renamed "
                          "**Reaction**, **1..1**. The cluster itself stays 0..1, so an allergy without a "
                          "recorded reaction is still possible."),
        ("1.4 Medication directions", "Medication order: **Overall directions description**, renamed **Directions**. Tempting but "
                              "wrong: Specific directions description (one part of the directions), Parsable "
                              "directions (a computable syntax for systems)."),
        ("1.5 Frailty", "Clinical Frailty Scale: keep **Assessment** (an ordinal, 1 Very Fit to 9 Terminally Ill)."),
    ]),
    ("h2", "Exercise 2: Inpatient admission details (ADMIN_ENTRY)"),
    ("table", [
        ("Mode of access", "Coded text, with free text allowed for 'Other'. 0..1."),
        ("Transported with", "Coded text, with free text for 'Other'. **0..***: more than one can apply."),
        ("Admission method", "Coded text. 0..1."),
        ("Additional help needed", "Boolean, or coded text Yes/No. 0..1."),
        ("Placement", "Straight on the Encounter, no section needed (not built on the baseplate). "
                      "Cardinality on the plate: 0..1."),
    ]),
    ("p", "The filled-in building blocks are on the last page of this document."),
]


def layout(content, footer=True):
    colors = json.loads(COLORS_FILE.read_text())
    doc = Pages(colors)
    for block in content:
        kind, *args = block
        if kind == "h1":
            doc.heading(args[0], 8.5, 0)
        elif kind == "sub":
            doc.para(args[0], size=3.8, fill=MUTED, gap=5, base_weight=600)
        elif kind == "h2":
            doc.heading(args[0], 5.4, 7)
            doc.y += 1.5
        elif kind == "h3":
            doc.heading(args[0], 4.1, 4, aid=args[1])
            doc.y += 0.8
        elif kind == "h4":
            doc.heading(args[0], 3.5, 2.5)
            doc.y += 0.6
        elif kind == "p":
            doc.para(args[0], justify=True)
        elif kind == "bullets":
            doc.bullets(args[0])
        elif kind == "tip":
            doc.tip(args[0])
        elif kind == "legend":
            doc.legend(*args)
        elif kind == "swatches":
            doc.swatches(args[0])
        elif kind == "table":
            doc.table(args[0])
        elif kind == "image":
            doc.image(*args)
        elif kind == "space":
            doc.y += args[0]
        elif kind == "pagebreak":
            doc.new_page()
    return doc.svgs(footer)


def assignment_pages(footer=True):
    return layout(CONTENT, footer)


def answer_key_pages():
    return layout(ANSWERS, footer=False)


def main():
    from make_print import render
    pages = assignment_pages()
    pdf = OUT_DIR / "assignment.pdf"
    render(pages, pdf)
    print(f"-> {pdf} ({len(pages)} pages)")


if __name__ == "__main__":
    main()
