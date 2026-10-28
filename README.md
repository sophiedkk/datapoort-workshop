# Datapoort openEHR building blocks workshop

A paper building-block openEHR template-modelling workshop: participants build the *Nursing
Admission Assessment* template from printed archetype plates and building blocks, then author
a new archetype (*Inpatient admission details*) with write-on blocks. Adapted from the
EHRCON26 freshEHR/Hanze practical. No computers or internet needed on the day.

| Folder | What's in it |
|---|---|
| `forms/` | Word sources of the two paper forms |
| `archetypes/practica-596Export/` | Archetype Designer export: archetypes and the COMPLETE / STARTER templates |
| `archetypes/decoys/` | CKM archetypes the form does *not* need, printed to make the exercise harder |
| `handouts/` | Generator for the print pack (see `handouts/README.md`) |

## Building the handouts

### With Podman (recommended)

The container has everything (ImageMagick, rsvg-convert, the Lexend font, Python):

```sh
podman build -t datapoort-handouts .
podman run --rm --userns=keep-id -v "$PWD:/work:Z" datapoort-handouts
```

`--userns=keep-id` makes the output files yours, and `:Z` lets SELinux (Fedora) allow the mount.
Docker works too: `docker build -f Containerfile ...` and `docker run --rm -u "$(id -u):$(id -g)"
-v "$PWD:/work" ...`.

### Without a container

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
handouts/build.sh
```

This writes `handouts/out/participant_handouts.pdf` and `handouts/out/facilitator_handouts.pdf`.
Print instructions are on the first page of the facilitator PDF.

The build also writes `handouts/out/demo.html`: a self-contained page (works offline) for
showing the idea of the workshop. Drag the strips, plates, building blocks, stickers and paper
forms from the tray onto the flipchart sheet (forms stay underneath, so blocks can go on top).
Pick what the tray shows with the *Show* menu (grouped by exercise). Double-click a plate, strip
or blank sticker to write on it, add notes with *Text*, resize a piece with its corner handle, and take it off the sheet with its x button or the Delete key. Single scripts run the same
way from `handouts/`, e.g. `uv run make_bricks.py --all --dry-run`.

### Online version (GitHub Pages)

`.github/workflows/pages.yml` publishes the committed `handouts/out/demo.html` as the start page
of the repository's GitHub Pages site, on every push to `main` that changes it (or by hand from
the Actions tab). To update the site: rebuild, commit `demo.html` and push.

One-time setup on GitHub: in the repository's *Settings*, open *Pages* and under *Build and
deployment* set *Source* to *GitHub Actions*.
On a free account the repository has to be public for Pages.

## Changing a paper form

Edit the docx in `forms/`, then render it to the image the assignment uses:

```sh
soffice --headless --convert-to pdf --outdir /tmp "forms/Nursing Admission Assessment.docx"
pdftoppm -r 150 -png -singlefile "/tmp/Nursing Admission Assessment.pdf" /tmp/form
magick /tmp/form.png -trim -bordercolor white -border 20 -alpha off handouts/assets/nursing-admission.png
```

Do the same for `forms/Additional information on admission.docx` and
`handouts/assets/additional-info.png`. Older versions of the form images are in the Git history.
