# Handouts generator

Printable paper building blocks for the physical openEHR modelling workshop: one building block
per data field (ELEMENT or archetype slot), one colour per archetype. Participants build the
*Nursing Admission Assessment* template by picking, removing and renaming building blocks.

Build everything (both handout PDFs and `out/demo.html`) with `./build.sh`. The steps separately:

```sh
uv run make_bricks.py ../archetypes/practica-596Export/local/openEHR-EHR-OBSERVATION.body_weight.v2.adl
uv run make_bricks.py --all              # every archetype in practica-596Export
uv run make_bricks.py --all --dry-run    # list the fields only
```

## How many building blocks per archetype

To keep it manageable, each archetype gets at most 8 building blocks (`--max-bricks`, one A4 sheet):
every field the COMPLETE template uses (`--template`) plus unused fields from the same
archetype as decoys, so participants still have to constrain things out. Unfilled slots
only count as used when the template fills them. Cloned fields (Medication order:
*Specific directions description* → Dose / Frequency) get one building block per clone (unless `FORM_CHANGES` overrides it, see below).
`--dry-run` marks the template fields with `*`. Use `--max-bricks 0` for every field.

`--blank` adds `blank_sheet.pdf`: 6 write-on building blocks in the archetype's colour (field name,
values, cardinality, data type tick boxes). Used for exercise 2, where participants
author *Inpatient admission details* themselves:

```sh
uv run make_bricks.py --blank ../archetypes/practica-596Export/openEHR-EHR-ADMIN_ENTRY.inpatient_admission_details.v0.adl
```

Options: `--lang nl` (translated labels, English fallback), `--no-slots`,
`--keep-extension` (include the generic *Extension* slots), `--stud-logo`.

Output goes to `out/<archetype-id>/`: an SVG + 300 dpi PNG per building block, `plate.svg`
and `sheet.pdf` (A4, building blocks 90 mm wide, dashed cut lines).

Archetype colours are stored in `colors.json` (with a colour name). New archetypes get the
next free colour automatically; edit the file to change one.

What a building block shows, from top to bottom:

- header: archetype name + entry type
- the field name, on one line (shrinks, then is cut off with "…" if it is very long)
- the field's description from the archetype (its first sentence), filling the space down to
  the next line
- units / value set / slot target, just above the chips
- data type chip and cardinality chip (`0..1 optional`, `1..1 required`, `0..* repeats`), and on
  the right a SNOMED CT or LOINC code if the archetype binds one
- slot building blocks: a "CLUSTER slot" chip and a small picture of the CLUSTER plugging in

Each building block page in the print pack says how many of the archetype's elements it shows
("8 of 20 elements"), next to the archetype name.

## Decoys

`../archetypes/decoys/` holds two CKM archetypes that the form does *not* need, to make the
exercise harder (render them with `uv run make_bricks.py ../archetypes/decoys/*.adl`):

| Archetype | Why it's tempting |
|---|---|
| OBSERVATION.respiration.v2 | a vital sign, but not on the form |
| OBSERVATION.body_mass_index.v2 | height and weight are on the form, BMI isn't |

Body temperature is a third decoy: it is in the export (the COMPLETE template uses it) but was
taken off the form, so `FORM_DECOYS` in `make_print.py` prints it as one.

Their building blocks go to the same `out/` folder, so nothing marks them as decoys on paper.

Therapeutic direction, the two falls risk archetypes, and Pulse and Pulse oximetry (taken
off the form: too many vital signs) are in the export but not in the workshop,
so they are left out of the print pack (`EXCLUDED` in `make_print.py`).

Where the workshop form differs from the COMPLETE template, `FORM_CHANGES` in `make_bricks.py`
overrides it: the form has one *Directions (dose/frequency)* field, so Medication order keeps
Overall directions description instead of the template's Dose and Frequency clones.

COMPOSITION and SECTION archetypes are skipped (they're the baseplate and heading strips, not building blocks).
Setup (uv, ImageMagick, rsvg-convert, Lexend): see `../README.md`.

## Override stickers

`uv run make_stickers.py --groups N` makes `out/stickers.pdf` (one A4 page per group,
best on label paper). Yellow means "changed in the template":

- cardinality stickers (28 × 9 mm) cover a building block's cardinality chip; templates can only
  narrow, so `0..1` → `1..1` is fine but `0..1` → `0..*` isn't. An archetype's own
  cardinality is written on its plate
- rename stickers (75 × 14 mm) cover the field name: the exercise renames (Allergy, Reaction,
  Directions) plus blank write-on ones

## Handouts

`uv run make_print.py` makes two vector PDFs (with `rsvg-convert`). Run `make_bricks.py --all`,
the decoys and `--blank` first; it reads the building block SVGs from `out/`.

- `out/participant_handouts.pdf`: the assignment (one per participant), then per group the
  template structure page, all archetype plates together (handed out first, for exercise 0),
  one page of building blocks per archetype (handed out after exercise 0; archetype name at the
  top and bottom of the page) and the override stickers.
- `out/facilitator_handouts.pdf`: a guide page (print counts, contents of both files, colour
  legend with the decoys marked), the answer key, the write-on building blocks (one per group,
  handed out at exercise 2), the CKM pile (Clinical Frailty Scale, one per group, handed out in
  exercise 0) and the filled-in Inpatient admission details.

## Assignment

`uv run make_assignment.py` makes `out/assignment.pdf`: the EHRCON26 practical modelling tasks
rewritten for building blocks and stickers, plus both paper forms. The text lives in `CONTENT`
at the top of the script. It is also the first part of the participant print pack.

## Template structure plates

`uv run make_plates.py` makes `out/plates.pdf`: one green Encounter strip (stuck at the top
of a flipchart sheet, which is the baseplate)
(COMPOSITION, write-in template name) and 5 grey write-on Ad hoc heading strips (SECTION,
renamed by participants: the COMPLETE template uses Allergies, Medications and Vital signs).
Also part of the participant print pack.

## Archetype plates and building blocks

`make_bricks.py` also writes `out/<archetype-id>/plate.svg`: a broad plate (two building
blocks wide) per archetype with its purpose, a "name in template" line and a cardinality
write-in. CLUSTER plates are dashed, have studs in the colour of the archetype they slot into,
and say which building block that is (worked out from the slot `include` patterns of the other
archetypes). Slot building blocks are normal blocks with a "CLUSTER slot" chip and a small
instruction picture: the element on top, the CLUSTER slotting in underneath.

Exercise order in the assignment: 0 choose the archetypes (structure + plates), 1 choose the
elements (building blocks, renames, cardinality), 2 author Inpatient admission details.
