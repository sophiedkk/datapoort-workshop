#!/bin/sh
# Rebuild the two handout PDFs and the offline demo page (out/demo.html) from the archetypes.
# Python dependencies come from ../pyproject.toml via uv; see ../README.md for the rest.
set -e
cd "$(dirname "$0")"
for tool in uv magick rsvg-convert fc-list; do
    command -v "$tool" >/dev/null || { echo "Missing: $tool (see README.md)" >&2; exit 1; }
done
uv run make_bricks.py --all
uv run make_bricks.py ../archetypes/decoys/*.adl
uv run make_bricks.py --blank ../archetypes/practica-596Export/openEHR-EHR-ADMIN_ENTRY.inpatient_admission_details.v0.adl
uv run make_print.py
uv run make_demo.py
