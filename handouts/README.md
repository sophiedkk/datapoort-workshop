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

Pulse and Pulse oximetry (taken off the form: too many vital signs) are in the export, because
the templates use them, but not in the workshop: `make_bricks.py --all` skips them and they are
left out of the print pack (`EXCLUDED` in `make_bricks.py`).

Where the workshop form differs from the COMPLETE template, `FORM_CHANGES` in `make_bricks.py`
overrides it: the form has one *Directions (dose/frequency)* field, so Medication order keeps
Overall directions description instead of the template's Dose and Frequency clones.

COMPOSITION and SECTION archetypes are skipped (they're the baseplate and the heading plates, not building blocks).
Setup (uv, ImageMagick, rsvg-convert, Lexend): see *Building without a container* below.

## Override stickers

`uv run make_stickers.py` makes `out/stickers.pdf` (one A4 page, the same for every group,
best on label paper). Yellow means "changed in the template":

- cardinality stickers (28 × 9 mm) cover a building block's cardinality chip; templates can only
  narrow, so `0..1` → `1..1` is fine but `0..1` → `0..*` isn't. An archetype's own
  cardinality is written on its plate
- rename stickers (75 × 10 mm) cover the field name of a building block or the name in the
  header of an archetype plate: the exercise renames (Allergy, Reaction, Directions) plus blank
  write-on ones

## Handouts

`uv run make_print.py` makes two vector PDFs (with `rsvg-convert`). Run `make_bricks.py --all`,
the decoys and `--blank` first; it reads the building block SVGs from `out/`.

- `out/participant_handouts.pdf`: the assignment (one per participant), then per group the
  template structure page, all archetype plates together (handed out first, for exercise 0),
  one page of building blocks per archetype (handed out after exercise 0; archetype name at the
  top and bottom of the page) and the override stickers.
- `out/facilitator_handouts.pdf`: a guide page (print counts, contents of both files, colour
  legend with the decoys marked), the answer key, the worked example (the answer built on the
  baseplate, from `example()` in `make_plates.py`) and the filled-in Inpatient admission details.
- `out/ckm_desk.pdf`: what the CKM desk hands out, printed once per group: the CKM pile (Clinical
  Frailty Scale plate and building block) and the black plate and write-on building blocks for
  exercise 2. So the facilitator handouts are printed only once.
- `out/baseplates_A0.pdf`: one A0 sheet (landscape) with eight Encounter baseplates, one per
  group, each 55 studs (about 1.12 m) in one piece.

## Assignment

`uv run make_assignment.py` makes `out/assignment.pdf`: the EHRCON26 practical modelling tasks
rewritten for building blocks and stickers, plus both paper forms. The text lives in `CONTENT`
at the top of the script. It is also the first part of the participant print pack.

## Template structure plates

Everything stands on one stud grid of 20.25 mm (a quarter of a building block's front): a
building block is 4 studs wide, an archetype plate and a heading 8 (exactly two blocks), and the
baseplate 55: six parts of the form of 8 studs side by side, with a free stud between two parts
and at both ends, because a cut-out piece keeps a little white paper around it. It fits the long
side of an A0 sheet.

`uv run make_plates.py` makes `out/plates.pdf`: 5 grey write-on Ad hoc heading plates (SECTION,
renamed by participants: the COMPLETE template uses Allergies, Medications and Vital signs), also
part of the participant print pack, and `out/baseplates_A0.pdf`: the green Encounter baseplates
(COMPOSITION, write-in template name, the building rules and what an Encounter is and records by
itself, from `BASE_INFO`), eight on one A0 sheet. `example()` places the answer on the
baseplate, for the facilitator PDF and the demo page.

## Archetype plates and building blocks

`make_bricks.py` also writes `out/<archetype-id>/plate.svg`: a broad plate (two building
blocks wide) per archetype with its name in a large header (sized to stay under a rename
sticker), its purpose and a cardinality write-in. CLUSTER plates are dashed and say which building block they slot into (worked out from the slot `include` patterns of the other
archetypes). Slot building blocks are normal blocks with a "CLUSTER slot" chip, studs in the
colour of the CLUSTER that goes on them and a small instruction picture: the CLUSTER coming down
onto the element and standing on it.

Exercise order in the assignment: 0 choose the archetypes (structure + plates), 1 choose the
elements (building blocks, renames, cardinality), 2 author Inpatient admission details.

## Building without a container

One-time setup:

1. [uv](https://docs.astral.sh/uv/). It installs Python and the Python dependencies
   (`pyproject.toml`) by itself on the first run.
2. ImageMagick and librsvg's `rsvg-convert`:
   - Fedora: `sudo dnf install ImageMagick librsvg2-tools`
   - Debian/Ubuntu: `sudo apt install imagemagick librsvg2-bin`
   - macOS: `brew install imagemagick librsvg`
3. The [Lexend](https://fonts.google.com/specimen/Lexend) font: install the variable font
   *and* the static SemiBold and ExtraBold files (`Lexend-VariableFont_wght.ttf`,
   `Lexend-SemiBold.ttf`, `Lexend-ExtraBold.ttf`), e.g. in `~/.local/share/fonts`.

Then:

```sh
./build.sh
```

Docker works too: `docker build -f Containerfile ...` and `docker run --rm -u "$(id -u):$(id -g)"
-v "$PWD:/work" ...` (from the repository root).

## Demo page

The build also writes `handouts/out/demo.html`: a self-contained page (works offline) for
showing the idea of the workshop: a table with the Encounter baseplate along the bottom. Drag
headings, plates, building blocks, stickers and paper forms from the tray onto the table; headings,
plates and blocks click onto the stud grid and onto the piece below them (forms stay underneath).
Pick what the tray shows with the *Show* menu (grouped by exercise); *Show the worked example*
builds the answer. Double-click the baseplate, a plate, a heading or a blank sticker to write on
it, add notes with *Text*, resize a note, sticker or form with its corner handle, and take a piece
off the table with its x button or the Delete key. Zoom with the mouse wheel or *Zoom*, drag the
empty table to move around, and *Fit* shows the whole table.

On a phone the tray opens with *Pieces* (tap a piece to put it on the table), pinch to zoom,
drag the empty table to move around, and *Write* writes on the selected piece.

## Online demo (GitHub Pages)

The demo is online at <https://sophiedkk.github.io/datapoort-workshop/>.
`.github/workflows/pages.yml` publishes the committed `handouts/out/demo.html` as the start page
of the repository's GitHub Pages site, on every push to `main` that changes it (or by hand from
the Actions tab). To update the site: rebuild, commit `demo.html` and push.

One-time setup on GitHub: in the repository's *Settings*, open *Pages* and under *Build and
deployment* set *Source* to *GitHub Actions*.
On a free account the repository has to be public for Pages.

## Changing a paper form

Edit the docx in `forms/`, then render it to the image the assignment uses (from the repository root):

```sh
soffice --headless --convert-to pdf --outdir /tmp "forms/Nursing Admission Assessment.docx"
pdftoppm -r 150 -png -singlefile "/tmp/Nursing Admission Assessment.pdf" /tmp/form
magick /tmp/form.png -trim -bordercolor white -border 20 -alpha off handouts/assets/nursing-admission.png
```

Do the same for `forms/Additional information on admission.docx` and
`handouts/assets/additional-info.png`. Older versions of the form images are in the Git history.
