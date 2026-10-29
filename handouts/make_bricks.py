#!/usr/bin/env python3
"""Generate printable paper building blocks, one per data field, from openEHR ADL 1.4 archetypes.

Each archetype gets its own brick colour (see colors.json). Every ELEMENT (and,
optionally, every archetype slot) becomes one brick with the field name, its RM
location, data type, cardinality and a short hint (units / value set).

Usage:
    uv run make_bricks.py ARCHETYPE.adl [...]          # bricks for given archetypes
    uv run make_bricks.py --all                         # every archetype in the export, except EXCLUDED
    uv run make_bricks.py --all --dry-run               # only list fields, no images
Options:
    --lang nl        use translated term texts (falls back to English)
    --no-slots       leave out archetype slot bricks
    --keep-extension also make bricks for the generic 'Extension' slots

Output (per archetype) in out/<archetype-id>/:
    NN_<field>.svg / .png   one brick per field
    sheet.pdf               A4 print sheet(s), bricks at a fixed physical width
"""

import argparse
import functools
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import ImageFont

HERE = Path(__file__).resolve().parent
EXPORT_DIR = HERE.parent / "archetypes" / "practica-596Export"
DECOY_DIR = HERE.parent / "archetypes" / "decoys"
OUT_DIR = HERE / "out"
COLORS_FILE = HERE / "colors.json"
TEMPLATE_FILE = EXPORT_DIR / "Nursing Admission Assessment COMPLETE.v0.t.json"
# In the export (the templates use them) but taken off the form: too many vital signs. --all skips them.
EXCLUDED = {"openEHR-EHR-OBSERVATION.pulse.v2", "openEHR-EHR-OBSERVATION.pulse_oximetry.v1"}

FONT_FAMILY = "Lexend"


@functools.cache
def font_file(name):
    """Path of an installed font file, e.g. 'Lexend-SemiBold.ttf' (text is measured with these)."""
    try:
        listed = subprocess.run(["fc-list", ":", "file"], capture_output=True, text=True).stdout.split()
    except FileNotFoundError:
        listed = []
    found = [f.rstrip(":") for f in listed if Path(f.rstrip(":")).name == name]
    if found:
        return Path(found[0])
    fallback = Path.home() / ".local/share/fonts" / name
    if fallback.exists():
        return fallback
    sys.exit(f"Font {name} not found: install Lexend (see README.md)")


FONT_FILES = {600: "Lexend-SemiBold.ttf", 800: "Lexend-ExtraBold.ttf"}

# Bright toy colours, assigned in order to archetypes without an entry in colors.json.
PALETTE = [
    ("Bright Red", "#C91A09"), ("Bright Blue", "#0055BF"), ("Bright Yellow", "#F2CD37"),
    ("Dark Green", "#237841"), ("Bright Orange", "#FE8A18"), ("Medium Azure", "#36AEBF"),
    ("Magenta", "#923978"), ("Lime", "#BBE90B"), ("Reddish Brown", "#582A12"),
    ("Dark Bluish Gray", "#6C6E68"), ("Tan", "#E4CD9E"), ("Dark Blue", "#0A3463"),
    ("Sand Green", "#A0BCAC"), ("Dark Red", "#720E0F"), ("Medium Lavender", "#AC78BA"),
    ("Black", "#212121"), ("Bright Pink", "#E4ADC8"), ("Dark Orange", "#A95500"),
    ("Dark Turquoise", "#008F9B"),
]

# Entry types whose fields become bricks; COMPOSITION/SECTION are the "baseplates".
BRICK_RM_TYPES = {"OBSERVATION", "EVALUATION", "INSTRUCTION", "ACTION", "ADMIN_ENTRY", "CLUSTER"}

DATA_TYPES = {
    "DV_QUANTITY": "Quantity", "C_DV_QUANTITY": "Quantity", "DV_COUNT": "Count",
    "DV_TEXT": "Text", "DV_CODED_TEXT": "Coded text", "DV_ORDINAL": "Ordinal",
    "C_DV_ORDINAL": "Ordinal", "DV_SCALE": "Scale", "DV_BOOLEAN": "Boolean",
    "DV_DATE_TIME": "Date/time", "DV_DATE": "Date", "DV_TIME": "Time",
    "DV_DURATION": "Duration", "DV_PROPORTION": "Proportion", "DV_IDENTIFIER": "Identifier",
    "DV_MULTIMEDIA": "Multimedia", "DV_URI": "URI", "DV_EHR_URI": "EHR URI",
    "DV_PARSABLE": "Parsable", "DV_INTERVAL": "Interval",
}

# Human-friendly display of common UCUM units.
UNITS = {"Cel": "°C", "[degF]": "°F", "[lb_av]": "lb", "mm[Hg]": "mmHg", "deg": "°", "[in_i]": "in",
         "/min": "/min", "1": "ratio"}

# Attributes that tell where in the RM structure a field lives.
LOCATION_ATTRS = ["protocol", "state", "description", "activities", "data"]


# --------------------------------------------------------------------------- parsing

@dataclass
class Field:
    code: str
    kind: str                      # "ELEMENT" or "SLOT"
    occurrences: str
    location: str
    parents: list = field(default_factory=list)   # at-codes of enclosing CLUSTERs
    types: list = field(default_factory=list)
    units: list = field(default_factory=list)
    codes: list = field(default_factory=list)     # local at-codes of a value set
    ordinals: dict = field(default_factory=dict)  # at-code -> ordinal value
    external: str = ""                            # external terminology / ac-code
    slot_target: str = ""
    slot_colors: list = field(default_factory=list)
    binding: str = ""                              # e.g. "SNOMED CT 271649006", from term_bindings
    in_exclude: bool = False                       # parsing state: inside a slot's exclude block


NODE_RE = re.compile(
    r"^\s*(allow_archetype\s+)?([A-Z_]+)\[(at[\d.]+)\]"
    r"(?:\s+occurrences matches \{([^}]*)\})?\s+matches \{")
ATTR_RE = re.compile(r"^\s*([a-z_]+)\s+(?:existence matches \{[^}]*\}\s+)?(?:cardinality matches \{[^}]*\}\s+)?matches \{")


def strip_comment(line):
    # `--` starts a comment, regexes like {/.../} may contain braces we must ignore
    line = re.sub(r"\{/.*?/\}", "{}", line)
    return line.split("--", 1)[0]


def parse_definition(text):
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip() == "definition")
    end = next(i for i, l in enumerate(lines) if l.strip() == "ontology")
    root_type = None
    stack = []   # (kind, name, Field|None)
    fields = []

    for raw in lines[start + 1:end]:
        line = strip_comment(raw)
        opens, closes = line.count("{"), line.count("}")
        node = NODE_RE.match(line)
        current = next((f for k, _, f in reversed(stack) if f is not None), None)

        if node:
            slot, rm_type, code, occ = node.groups()
            if root_type is None:
                root_type = rm_type
            entry = None
            if rm_type == "ELEMENT" or (slot and rm_type == "CLUSTER"):
                attrs = [n for k, n, _ in stack if k == "attr"]
                location = next((a for a in LOCATION_ATTRS if a in attrs), "")
                parents = [n for k, n, _ in stack if k == "CLUSTER" and n != "at0000"]
                entry = Field(code=code, kind="SLOT" if slot else "ELEMENT",
                              occurrences=(occ or "1..1").strip(), location=location, parents=parents)
                fields.append(entry)
            stack.append(("CLUSTER" if rm_type == "CLUSTER" else "node", code, entry))
            delta = opens - closes - 1
        elif ATTR_RE.match(line):
            stack.append(("attr", ATTR_RE.match(line).group(1), None))
            delta = opens - closes - 1
        else:
            delta = opens - closes
            if current is not None:
                collect_value_info(current, raw)

        # every remaining unbalanced brace is an anonymous frame; a negative delta closes frames
        # (this also closes one-line nodes such as `ELEMENT[at0001] matches {*}`)
        for _ in range(max(delta, 0)):
            stack.append(("anon", "", None))
        for _ in range(max(-delta, 0)):
            stack.pop()

    return root_type, fields


def collect_value_info(f, raw):
    for t in re.findall(r"\b(C_DV_\w+|DV_\w+)\b", raw):
        name = DATA_TYPES.get(t, t)
        if name not in f.types:
            f.types.append(name)
    m = re.search(r'units = <"([^"]+)">', raw)
    if m and m.group(1) not in f.units:
        f.units.append(m.group(1))
    code_part = raw.split("--")[0]
    for value, code in re.findall(r"(-?\d+(?:\.\d+)?)\|\[local::(at[\d.]+)\]", code_part):
        f.ordinals[code] = value
        if "Ordinal" not in f.types:
            f.types.append("Ordinal")
    if ("local::" in code_part or re.match(r"^\s*at\d", code_part)) and "assumed_value" not in code_part:
        f.codes += [c for c in re.findall(r"\b(at\d{4}(?:\.\d+)*)\b", code_part) if c not in f.codes]
    m = re.search(r"\[(ac\d+|[A-Za-z][\w-]*::[^\]]*)\]", code_part)
    if m and not m.group(1).startswith(("local::", "openehr::")):
        f.external = m.group(1)
    if raw.strip() in ("include", "exclude"):
        f.in_exclude = raw.strip() == "exclude"
    m = re.search(r"archetype_id/value matches \{/(.*)/\}", raw)
    if m and not f.in_exclude:
        f.slot_target = f"{f.slot_target}|({m.group(1)})" if f.slot_target else f"({m.group(1)})"


def parse_terms(text, lang):
    onto = text[text.index("\nontology"):]
    td = onto[onto.index("term_definitions"):]
    end = td.find("term_bindings")
    td = td if end < 0 else td[:end]
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'\["([\w-]+)"\] = <\s*items = <', td)]
    blocks = {}
    for i, (pos, language) in enumerate(starts):
        block = td[pos: starts[i + 1][0] if i + 1 < len(starts) else len(td)]
        blocks[language] = {
            m.group(1): (unescape(m.group(2)), unescape(m.group(3)))
            for m in re.finditer(
                r'\["(at[\d.]+)"\] = <\s*text = <"((?:[^"\\]|\\.)*)">\s*description = <"((?:[^"\\]|\\.)*)">',
                block)
        }
    english = blocks.get("en", {})
    wanted = blocks.get(lang, {})
    terms = dict(english)
    for code, (txt, desc) in wanted.items():
        if not txt.startswith("*"):          # '*...(en)' marks an untranslated term
            terms[code] = (txt, desc)
    return terms


def parse_bindings(text):
    """at-code -> 'SNOMED CT <code>' (preferred) or 'LOINC <code>', from the archetype's term_bindings."""
    start = text.find("term_bindings")
    if start < 0:
        return {}
    found = {}
    for code, term, value in re.findall(r'\["(at[\d.]+)"\]\s*=\s*<\[([^\]:]+)::([^\]]+)\]>', text[start:]):
        name = "SNOMED CT" if term.upper().startswith("SNOMED") else "LOINC" if term.upper().startswith(("LOINC", "LNC")) else None
        if name and (code not in found or name == "SNOMED CT"):
            found[code] = f"{name} {value.strip()}"
    return found


def unescape(s):
    return s.replace('\\"', '"').replace("\\\\", "\\")


# --------------------------------------------------------------------------- drawing

_font_cache = {}


def text_width(text, size, weight=800):
    key = (size, weight)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(font_file(FONT_FILES[weight])), size)
    return _font_cache[key].getlength(text)


def wrap(text, size, max_width, weight=800):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_width(trial, size, weight) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def wrap_widths(text, size, widths, weight=800):
    """Like wrap(), but line i may be at most widths[i] wide (the last width repeats)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        max_width = widths[min(len(lines), len(widths) - 1)] if widths else 0
        if text_width(trial, size, weight) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def fit_title(text, max_width, max_lines=2, sizes=range(96, 39, -4)):
    for size in sizes:
        lines = wrap(text, size, max_width)
        if len(lines) <= max_lines and all(text_width(l, size) <= max_width for l in lines):
            return size, lines
    size = sizes[-1] if isinstance(sizes, list) else min(sizes)
    return size, wrap(text, size, max_width)[:max_lines]


def ellipsize(text, size, max_width, weight=600):
    if text_width(text, size, weight) <= max_width:
        return text
    while text and text_width(text + "…", size, weight) > max_width:
        text = text[:-1]
    return text.rstrip(" ,;") + "…"


def shade(hex_color, factor):
    """factor < 1 darkens, > 1 lightens (towards white)."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    if factor < 1:
        r, g, b = (int(c * factor) for c in (r, g, b))
    else:
        t = factor - 1
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def is_light(hex_color):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b > 160


W, H = 1400, 840                  # canvas
FX, FY, FW, FH = 30, 220, 1260, 590   # front face
DX, DY = 90, -150                 # offset of the back edge of the top face
STUD = FW / 4                     # stud pitch: a block is 4 studs wide; plates and headings are 8
STUD_RX, STUD_RY, STUD_H = 54, 21, 30   # every stud, on blocks, plates, headings and the baseplate


def brick_svg(color, archetype_label, f, terms, opts, header_only=False):
    dx, dy = DX, DY
    top, side, edge = shade(color, 1.25), shade(color, 0.72), shade(color, 0.55)
    ink = "#1B1B1B"
    esc = html.escape
    p = []
    a = p.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
      f'font-family="{FONT_FAMILY}, sans-serif">')

    # --- brick body: front, top and right side faces
    a(f'<polygon points="{FX},{FY} {FX + dx},{FY + dy} {FX + FW + dx},{FY + dy} {FX + FW},{FY}" '
      f'fill="{top}" stroke="{edge}" stroke-width="4" stroke-linejoin="round"/>')
    a(f'<polygon points="{FX + FW},{FY} {FX + FW + dx},{FY + dy} {FX + FW + dx},{FY + FH + dy} {FX + FW},{FY + FH}" '
      f'fill="{side}" stroke="{edge}" stroke-width="4" stroke-linejoin="round"/>')
    a(f'<rect x="{FX}" y="{FY}" width="{FW}" height="{FH}" fill="{color}" stroke="{edge}" '
      f'stroke-width="4" stroke-linejoin="round"/>')

    # --- studs: 2 rows x 4 on the top face, back row first so front row overlaps it
    edge_s = edge
    rx, ry, sh = STUD_RX, STUD_RY, STUD_H
    for row in (1, 0):
        t = 0.27 + 0.5 * row                # position across the depth of the top face
        for i in range(4):
            cx = FX + FW * (i + 0.5) / 4 + dx * t
            cy = FY + dy * t - sh + 8
            a(f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + sh} A{rx},{ry} 0 0 0 {cx + rx},{cy + sh} '
              f'L{cx + rx},{cy} Z" fill="{side}" stroke="{edge_s}" stroke-width="3"/>')
            a(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{top}" stroke="{edge_s}" stroke-width="3"/>')
            if opts.stud_logo:
                a(f'<text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="22" font-weight="800" '
                  f'fill="{shade(color, 1.08)}" stroke="{edge}" stroke-width="0.6" '
                  f'transform="scale(1 0.4) translate(0 {cy / 0.4 - cy})">openEHR</text>')

    # --- sticker on the front face
    SX, SY, SW, SH = FX + 34, FY + 32, FW - 68, FH - 64
    dashed = ""
    a(f'<rect x="{SX}" y="{SY}" width="{SW}" height="{SH}" rx="26" fill="#FFFFFF" '
      f'stroke="{edge}" stroke-width="4"{dashed}/>')
    pad = 44
    inner_w = SW - 2 * pad

    # header: the archetype it belongs to
    hb = 96
    a(f'<rect x="{SX}" y="{SY}" width="{SW}" height="{hb}" rx="26" fill="{color}"/>')
    a(f'<rect x="{SX}" y="{SY + hb - 26}" width="{SW}" height="26" fill="{color}"/>')
    head_ink = ink if is_light(color) else "#FFFFFF"
    label_w = inner_w
    label_size = next((sz for sz in range(46, 33, -2) if label_width(archetype_label, sz) <= label_w), 34)
    name, kind = archetype_label
    if label_width(archetype_label, label_size) > label_w:
        name = ellipsize(name, label_size, label_w - label_width(("", kind), label_size), 800)
    a(name_and_kind((name, kind), SX + pad, SY + hb / 2 + label_size * 0.36, label_size, head_ink))
    if header_only:
        a("</svg>")
        return "\n".join(p)

    # field name on one line at the top, units / values anchored just above the chips,
    # and the description from the archetype fills the space in between
    chips_y = SY + SH - 40 - 52
    y = SY + hb + 22
    name = terms.get(f.code, (f.code, ""))[0]
    size = next((sz for sz in range(60, 39, -2) if text_width(name, sz) <= inner_w), 40)
    name = ellipsize(name, size, inner_w, 800)
    a(f'<text x="{SX + pad}" y="{y + size * 0.82:.0f}" font-size="{size}" '
      f'font-weight="800" fill="{ink}">{esc(name)}</text>')
    y += size * 1.08

    shrink, icon_top = 0, chips_y
    icon_scale = 1.35
    for c in f.slot_colors[:1]:
        icon_top = chips_y - 12 - CLICK_H * icon_scale
        a(click_icon(SX + SW - pad - CLICK_W * icon_scale, icon_top, color, c, scale=icon_scale))
        shrink = CLICK_W * icon_scale + 20                  # keep text clear of the icon

    hint = value_hint(f, terms)
    hint_top = chips_y - 30
    if hint:
        hint_lines = wrap(hint, 29, inner_w - shrink, weight=600)
        if len(hint_lines) > 2:
            hint_lines = hint_lines[:1] + [ellipsize(" ".join(hint_lines[1:]), 29, inner_w - shrink)]
        hint_top = chips_y - 24 - 38 * len(hint_lines)
        for i, line in enumerate(hint_lines):
            a(f'<text x="{SX + pad}" y="{hint_top + 38 * (i + 1):.0f}" font-size="29" font-weight="600" '
              f'fill="#333">{esc(line)}</text>')

    description = first_sentence(terms.get(f.code, ("", ""))[1])
    keep = int((hint_top - 6 - y - 4) // 46)
    if description and keep > 0:
        y += 4
        # lines that reach down next to the icon are kept narrower
        widths = [inner_w - (shrink if y + 46 * (i + 1) > icon_top else 0) for i in range(keep)]
        desc_lines = wrap_widths(description, 40, widths, weight=600)
        if len(desc_lines) > keep:
            desc_lines = desc_lines[:keep - 1] + [ellipsize(" ".join(desc_lines[keep - 1:]), 40, widths[-1])]
        for line in desc_lines:
            y += 46
            a(f'<text x="{SX + pad}" y="{y:.0f}" font-size="40" font-weight="600" fill="#333">{esc(line)}</text>')

    # footer chips: data type, cardinality, at-code
    x = SX + pad + 3                 # outer edge of the stroke lines up with the glyphs of the text above
    dtype = "CLUSTER slot" if f.kind == "SLOT" else (" / ".join(f.types) or "Any")
    for label, fill, txt_color in (
            (dtype, color, head_ink),
            (cardinality_label(f.occurrences), "#EDEDED", ink)):
        w = text_width(label, 32, 800) + 48
        a(f'<rect x="{x}" y="{chips_y}" width="{w:.0f}" height="58" rx="29" fill="{fill}" '
          f'stroke="{edge}" stroke-width="2.5"/>')
        a(f'<text x="{x + 24}" y="{chips_y + 40}" font-size="32" font-weight="800" '
          f'fill="{txt_color}">{esc(label)}</text>')
        x += w + 18
    right = SX + SW - pad
    if f.binding and x + text_width(f.binding, 28, 800) < right:
        a(f'<text x="{right}" y="{chips_y + 40}" font-size="28" font-weight="800" fill="#1B1B1B" '
          f'text-anchor="end">{esc(f.binding)}</text>')

    a("</svg>")
    return "\n".join(p)


def name_and_kind(label, x, y, size, fill, extra=""):
    """('Body weight', 'Observation') -> bold name, then the type in a lighter weight."""
    name, kind = label if isinstance(label, tuple) else (label, "")
    kind_span = (f'<tspan font-weight="600" fill-opacity="0.72">{html.escape("   " + kind)}</tspan>'
                 if kind else "")
    return (f'<text xml:space="preserve" x="{x}" y="{y}" font-size="{size}" fill="{fill}"{extra}>'
            f'<tspan font-weight="800">{html.escape(name)}</tspan>{kind_span}</text>')


def label_width(label, size):
    name, kind = label if isinstance(label, tuple) else (label, "")
    return text_width(name, size, 800) + (text_width("   " + kind, size, 600) if kind else 0)


PW = FX + 2 * FW + DX + 20         # plate canvas: the front face is exactly two blocks (8 studs) wide
PH = 620
PLATE_FY, PLATE_FH = 190, 410
PLATE_HB = 172                     # plate header: a rename sticker (10 mm high) fits on it
PLATE_NAME_W = 1100                # the archetype name stays under a rename sticker (75 mm)


def plate_svg(color, archetype_label, purpose, plugs_into=(), shown=None, binding=""):
    """A broad archetype plate: the building blocks of the archetype go on it. Shows the archetype's
    purpose, where a CLUSTER plugs in, and write-in lines for its name and cardinality in the template.

    plugs_into: [(slot name, host archetype name, host colour), ...] for CLUSTER archetypes."""
    fx, fy, fh = FX, PLATE_FY, PLATE_FH
    fw = 2 * FW
    dx, dy = DX, DY
    top, side, edge = shade(color, 1.25), shade(color, 0.72), shade(color, 0.55)
    head_ink = "#1B1B1B" if is_light(color) else "#FFFFFF"
    esc = html.escape
    is_cluster = archetype_label[1].upper() == "CLUSTER"
    elements = f' data-elements="{shown[0]} of {shown[1]} elements"' if shown else ""
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}" '
         f'font-family="{FONT_FAMILY}, sans-serif"{elements}>',
         f'<polygon points="{fx},{fy} {fx + dx},{fy + dy} {fx + fw + dx},{fy + dy} {fx + fw},{fy}" '
         f'fill="{top}" stroke="{edge}" stroke-width="4" stroke-linejoin="round"/>',
         f'<polygon points="{fx + fw},{fy} {fx + fw + dx},{fy + dy} {fx + fw + dx},{fy + fh + dy} {fx + fw},{fy + fh}" '
         f'fill="{side}" stroke="{edge}" stroke-width="4" stroke-linejoin="round"/>',
         f'<rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" fill="{color}" stroke="{edge}" stroke-width="4"/>']
    # the same studs as a block, on the same grid (8 studs: two blocks), so pieces line up. A CLUSTER
    # plate gets studs in the colour of the archetype it slots into.
    stud = plugs_into[0][2] if plugs_into else color
    s_top, s_side, s_edge = shade(stud, 1.25), shade(stud, 0.72), shade(stud, 0.55)
    rx, ry, sh = STUD_RX, STUD_RY, STUD_H
    for t in (0.77, 0.27):
        for i in range(8):
            cx = fx + (i + 0.5) * STUD + dx * t
            cy = fy + dy * t - sh + 8
            p.append(f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + sh} A{rx},{ry} 0 0 0 {cx + rx},{cy + sh} '
                     f'L{cx + rx},{cy} Z" fill="{s_side}" stroke="{s_edge}" stroke-width="3"/>')
            p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{s_top}" stroke="{s_edge}" '
                     f'stroke-width="3"/>')
    sx, sy, sw, shh = fx + 30, fy + 26, fw - 60, fh - 52
    pad = 40
    dashed = ' stroke-dasharray="22 14"' if is_cluster else ""
    hb = PLATE_HB                                   # colour header with the archetype name, the eye-catcher
    p += [f'<rect x="{sx}" y="{sy}" width="{sw}" height="{shh}" rx="22" fill="#fff" stroke="{edge}" '
          f'stroke-width="4"{dashed}/>',
          f'<path d="M{sx},{sy + hb} V{sy + 22} a22,22 0 0 1 22,-22 H{sx + sw - 22} a22,22 0 0 1 22,22 V{sy + hb} Z" '
          f'fill="{color}"/>']
    # the name fits under a rename sticker; the archetype type goes on the right
    name, kind = archetype_label
    name_size = next((sz for sz in range(104, 63, -4) if text_width(name, sz) <= PLATE_NAME_W), 64)
    p.append(f'<text x="{sx + pad}" y="{sy + hb / 2 + name_size * 0.36}" font-size="{name_size}" font-weight="800" '
             f'fill="{head_ink}">{esc(ellipsize(name, name_size, PLATE_NAME_W, 800))}</text>')
    tag = "CLUSTER: GOES IN A SLOT" if is_cluster else "ARCHETYPE"
    p.append(f'<text x="{sx + sw - pad}" y="{sy + 78}" font-size="52" font-weight="600" fill="{head_ink}" '
             f'fill-opacity="0.8" text-anchor="end">{esc(kind)}</text>')
    p.append(f'<text x="{sx + sw - pad}" y="{sy + 132}" font-size="24" font-weight="800" fill="{head_ink}" '
             f'text-anchor="end" letter-spacing="2">{tag}</text>')
    # right column: elements shown, cardinality write-in at the bottom
    col_w = 560
    right = sx + sw - pad
    if shown and shown[0] < shown[1]:
        p.append(f'<text x="{right}" y="{sy + hb + 44}" font-size="28" font-weight="800" fill="#777" '
                 f'text-anchor="end">{shown[0]} of {shown[1]} elements shown</text>')
    if binding:
        p.append(f'<text x="{right}" y="{sy + hb + 84}" font-size="28" font-weight="800" fill="#1B1B1B" '
                 f'text-anchor="end">{esc(binding)}</text>')
    purpose_w = sw - 2 * pad - col_w - 40
    if plugs_into:                                  # keep clear of the slot-in picture
        purpose_w -= CLICK_W * 1.05 + 40
        p.append(click_icon(right - col_w - CLICK_W * 1.05 - 20, sy + hb + 12, plugs_into[0][2], color, scale=1.05))
    size, step = 44, 52
    keep = 2 if plugs_into else 3
    purpose_lines = wrap(purpose, size, purpose_w, weight=600)
    if len(purpose_lines) > keep:
        purpose_lines = purpose_lines[:keep - 1] + [ellipsize(" ".join(purpose_lines[keep - 1:]), size, purpose_w)]
    y = sy + hb + 2
    for line in purpose_lines:
        y += step
        p.append(f'<text x="{sx + pad}" y="{y}" font-size="{size}" font-weight="600" fill="#1B1B1B">{esc(line)}</text>')
    for slot, host, _ in plugs_into[:1]:
        y += step
        p.append(f'<text x="{sx + pad}" y="{y}" font-size="36" font-weight="800" fill="#1B1B1B">Plugs into:</text>')
        x = sx + pad + text_width("Plugs into: ", 36, 800)
        p.append(f'<text x="{x}" y="{y}" font-size="36" font-weight="600" fill="#1B1B1B">'
                 f'{esc(slot)} (a building block of {esc(host)})</text>')
    # cardinality the archetype gets in the template (a rename goes on a sticker over the name)
    label_y, line_y = sy + shh - 62, sy + shh - 22
    split = right - col_w
    p.append(f'<text x="{split}" y="{label_y}" font-size="24" font-weight="800" fill="#777" '
             f'letter-spacing="1.5">CARDINALITY</text>')
    for lx in (split, split + 330):
        p.append(f'<line x1="{lx}" y1="{line_y}" x2="{lx + 230}" y2="{line_y}" stroke="#1B1B1B" stroke-width="3"/>')
    p.append(f'<text x="{split + 280}" y="{line_y - 4}" font-size="40" font-weight="800" fill="#1B1B1B" '
             f'text-anchor="middle">..</text>')
    p.append("</svg>")
    return "\n".join(p)


def blank_brick_svg(color, archetype_label):
    """A write-on brick for fields participants model themselves (exercise 2)."""
    blank = Field(code="", kind="ELEMENT", occurrences="", location="data")
    svg = brick_svg(color, archetype_label, blank, {}, argparse.Namespace(stud_logo=False), header_only=True)
    edge, head_ink = shade(color, 0.55), "#1B1B1B"
    SX, SY, SW, SH = FX + 34, FY + 32, FW - 68, FH - 64
    pad, line = 44, "#9A9A9A"
    x0, x1 = SX + pad, SX + SW - pad
    p = [svg.rsplit("</svg>", 1)[0]]
    a = p.append
    label = 'font-size="28" font-weight="800" fill="#555"'
    a(f'<text x="{x0}" y="{SY + 128}" {label}>FIELD NAME</text>')
    a(f'<line x1="{x0}" y1="{SY + 232}" x2="{x1}" y2="{SY + 232}" stroke="{line}" stroke-width="3"/>')
    a(f'<text x="{x0}" y="{SY + 290}" {label}>VALUES</text>')
    a(f'<line x1="{x0 + 150}" y1="{SY + 292}" x2="{x1}" y2="{SY + 292}" stroke="{line}" stroke-width="2.5" '
      f'stroke-dasharray="6 8"/>')
    a(f'<line x1="{x0}" y1="{SY + 352}" x2="{x1 - 440}" y2="{SY + 352}" stroke="{line}" stroke-width="2.5" '
      f'stroke-dasharray="6 8"/>')
    # data type tick boxes + cardinality write-in
    y = SY + SH - 92
    x = x0
    for dtype in ("Text", "Coded text", "Boolean", "_______"):
        a(f'<rect x="{x}" y="{y + 12}" width="34" height="34" rx="6" fill="#fff" stroke="{edge}" stroke-width="3"/>')
        a(f'<text x="{x + 46}" y="{y + 41}" font-size="30" font-weight="800" fill="{head_ink}">{dtype}</text>')
        x += 46 + text_width(dtype, 30) + 30
    a(f'<text x="{x1 - 400}" y="{SY + 352}" {label}>CARDINALITY</text>')
    for i, lx in enumerate((x1 - 170, x1 - 70)):
        a(f'<line x1="{lx}" y1="{SY + 354}" x2="{lx + 70}" y2="{SY + 354}" stroke="{head_ink}" stroke-width="3"/>')
    a(f'<text x="{x1 - 85}" y="{SY + 352}" font-size="34" font-weight="800" fill="{head_ink}" '
      f'text-anchor="middle">..</text>')
    a("</svg>")
    return "\n".join(p)


def mini_brick(x, y, w, h, color, studs=2):
    """A tiny isometric brick with its front face at (x, y, w, h), for instruction-style icons."""
    dx, dy = w * 0.18, -h * 0.45
    top, side, edge = shade(color, 1.25), shade(color, 0.72), shade(color, 0.55)
    p = [f'<polygon points="{x},{y} {x + dx},{y + dy} {x + w + dx},{y + dy} {x + w},{y}" fill="{top}" '
         f'stroke="{edge}" stroke-width="1.6" stroke-linejoin="round"/>',
         f'<polygon points="{x + w},{y} {x + w + dx},{y + dy} {x + w + dx},{y + h + dy} {x + w},{y + h}" '
         f'fill="{side}" stroke="{edge}" stroke-width="1.6" stroke-linejoin="round"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" stroke="{edge}" stroke-width="1.6"/>']
    rx, ry, sh = w / (studs * 3.2), w / (studs * 8), h * 0.3
    for i in range(studs):
        cx, cy = x + w * (i + 0.5) / studs + dx * 0.5, y + dy * 0.5 - sh + 1
        p.append(f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + sh} A{rx},{ry} 0 0 0 {cx + rx},{cy + sh} '
                 f'L{cx + rx},{cy} Z" fill="{side}" stroke="{edge}" stroke-width="1.2"/>')
        p.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{top}" stroke="{edge}" stroke-width="1.2"/>')
    return "".join(p)


CLICK_W, CLICK_H = 110, 96          # click_icon size at scale 1


def click_icon(x, y, element_color, cluster_color, scale=1.0):
    """Assembly-instruction style: the CLUSTER comes down onto the element with the slot, and stands on it.
    CLICK_W x CLICK_H at scale 1; (x, y) is the top left."""
    w, h = 64 * scale, 22 * scale
    ax = x + w + 30 * scale
    return (f'<g>{mini_brick(x, y + 74 * scale, w, h, element_color)}'
            f'{mini_brick(x, y + 20 * scale, w, h, cluster_color)}'
            f'<line x1="{ax}" y1="{y + 20 * scale}" x2="{ax}" y2="{y + 72 * scale}" stroke="#1B1B1B" '
            f'stroke-width="{4 * scale}" stroke-linecap="round"/>'
            f'<polygon points="{ax - 9 * scale},{y + 66 * scale} {ax + 9 * scale},{y + 66 * scale} '
            f'{ax},{y + 81 * scale}" fill="#1B1B1B"/></g>')


def first_sentence(text):
    text = text.strip().lstrip("*")
    if not text or text.startswith("@ internal"):
        return ""
    m = re.match(r"(.+?[.!?])(\s|$)", text, re.S)
    return " ".join((m.group(1) if m else text).split())


def cardinality_label(occ):
    lo, _, hi = occ.partition("..")
    req = "required" if lo.strip() != "0" else "optional"
    rep = ", repeats" if hi.strip() == "*" else ""
    return f"{occ.strip()}  {req}{rep}"


def value_hint(f, terms):
    if f.kind == "SLOT":
        return "Plug in: " + slot_label(f.slot_target)
    if f.units:
        return "Units: " + ", ".join(pretty_unit(u) for u in f.units)
    if f.codes:
        values = [(f"{f.ordinals[c]} " if c in f.ordinals else "") + terms.get(c, (c,))[0] for c in f.codes]
        return "Values: " + ("; " if any("," in v for v in values) else ", ").join(values)
    if f.external:
        return "Coded from external terminology"
    return ""


def pretty_unit(unit):
    if unit in UNITS:
        return UNITS[unit]
    unit = re.sub(r"\[[^\]]+\]|Cel|deg", lambda m: UNITS.get(m.group(0), m.group(0)), unit)
    return re.sub(r"(?<=[a-z])2\b", "²", unit)


def accepts(pattern, archetype_id):
    """Does a slot pattern explicitly name this archetype? Open slots (.*) don't count."""
    if not pattern or pattern.strip("()") == ".*":
        return False
    try:
        return re.fullmatch(pattern, archetype_id) is not None
    except re.error:
        return False


def slot_label(pattern):
    if pattern.strip("()") in (".*", ""):
        return "any CLUSTER archetype"
    names = re.findall(r"CLUSTER\\?\.([a-z_]+)", pattern)
    return ", ".join(n.replace("_", " ") for n in dict.fromkeys(names)) or pattern


# --------------------------------------------------------------------------- output

MM_PER_BRICK = 90           # printed brick width
A4 = (210, 297)
MARGIN = 10


def render_png(svg_path, png_path, dpi=300):
    subprocess.run(["magick", "-density", str(dpi), "-background", "none", str(svg_path), str(png_path)],
                   check=True)


def sheet_header(title, color, x0, page_note="", y=MARGIN, hint=True):
    """Title strip of a sheet: colour swatch, archetype name, cutting hint. Without a colour, no swatch."""
    swatch = (f'<rect x="{x0}" y="{y + 1}" width="10" height="6" rx="1" fill="{color}" stroke="#555" '
              f'stroke-width="0.2"/>' if color else "")
    label = (title, "") if isinstance(title, str) else (title[0], title[1] + page_note)
    tx = x0 + (13 if color else 0)
    hint_text = "✂ cut along the dashed lines"
    room = A4[0] - x0 - tx - label_width(label, 4.6) - 4
    cut = (f'<text x="{A4[0] - x0}" y="{y + 6}" font-size="2.8" font-weight="600" fill="#888" '
           f'text-anchor="end">{hint_text}</text>' if hint and text_width(hint_text, 2.8, 600) <= room else "")
    return (f'<g font-family="{FONT_FAMILY}, sans-serif">' + swatch
            + name_and_kind(label, tx, y + 6, 4.6, "#1B1B1B") + cut + '</g>')


def sheet_pages(svgs, title=None, color="#cccccc", footer=True, gap=6, note=""):
    """Lay block and plate SVGs out on A4 pages (mm user units), two per row, with dashed cut guides.

    With a title, it goes at the top of each page, and (footer) again at the bottom, so a pile of
    half-cut pages can still be told apart. A note (such as "6 of 26 elements") follows the title.

    Everything is printed at the same scale (a plate is exactly two blocks wide) and a wide item gets a
    row of its own; a row is as tall as its tallest item."""
    bw = MM_PER_BRICK
    cols = int((A4[0] - 2 * MARGIN + gap) // (bw + gap))
    x0 = (A4[0] - cols * bw - (cols - 1) * gap) / 2
    top = MARGIN + (14 if title else 0)
    bottom = A4[1] - MARGIN - (12 if title and footer else 0)

    full = cols * bw + (cols - 1) * gap
    scale = bw / W                  # every piece at the same scale, so plates are exactly two blocks wide

    def size(svg):
        """canvas width, height, printed width and printed height (wide items span the whole row)"""
        w, h = (float(v) for v in re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
        return w, h, w * scale, h * scale

    def wide(svg):
        return size(svg)[0] > 1.5 * W

    # rows: a wide item gets a row of its own, blocks fill rows of `cols`; then pages of rows
    rows = []
    for svg in svgs:
        if wide(svg) or not rows or len(rows[-1]) == cols or wide(rows[-1][0]):
            rows.append([svg])
        else:
            rows[-1].append(svg)
    page_rows, current, y = [], [], top
    for row in rows:
        rh = max(size(svg)[3] for svg in row)
        if current and y + rh > bottom:
            page_rows.append(current)
            current, y = [], top
        current.append(row)
        y += rh + gap
    if current:
        page_rows.append(current)

    pages = []
    for page_no, page in enumerate(page_rows, 1):
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4[0]}mm" height="{A4[1]}mm" '
                 f'viewBox="0 0 {A4[0]} {A4[1]}"><rect width="100%" height="100%" fill="#fff"/>']
        if title:
            page_note = (f"  ({page_no}/{len(page_rows)})" if len(page_rows) > 1 else "") + (f"   {note}" if note else "")
            parts.append(sheet_header(title, color, x0, page_note))
            if footer:
                parts.append(sheet_header(title, color, x0, page_note, y=A4[1] - MARGIN - 9, hint=False))
        y = top
        for row in page:
            rh = max(size(svg)[3] for svg in row)
            for c, svg in enumerate(row):
                w, h, iw, ih = size(svg)
                x = x0 + (full - iw) / 2 if wide(svg) else x0 + c * (bw + gap)
                # light cut guide around each item
                parts.append(f'<rect x="{x - 1.5}" y="{y - 1.5}" width="{iw + 3}" height="{ih + 3}" fill="none" '
                             f'stroke="#666" stroke-width="0.3" stroke-dasharray="1.5 1.5"/>')
                inner = svg.replace('<svg xmlns="http://www.w3.org/2000/svg"',
                                    f'<svg x="{x}" y="{y}" width="{iw}" height="{ih}"', 1)
                inner = re.sub(rf' width="{w:g}" height="{h:g}"', "", inner, count=1)
                parts.append(inner)
            y += rh + gap
        parts.append("</svg>")
        pages.append("\n".join(parts))
    return pages


def build_sheets(svgs, out_dir, name="sheet.pdf", title=None, color="#cccccc"):
    pages = []
    for page_no, page in enumerate(sheet_pages(svgs, title, color), 1):
        page_svg = out_dir / f".sheet-{page_no}.svg"
        page_svg.write_text(page, encoding="utf-8")
        pages.append(page_svg)
    pdf = out_dir / name
    subprocess.run(["magick", "-density", "300", *map(str, pages), "-units", "PixelsPerInch",
                    "-density", "300", str(pdf)], check=True)
    for pg in pages:
        pg.unlink()
    return pdf


def load_colors():
    return json.loads(COLORS_FILE.read_text()) if COLORS_FILE.exists() else {}


def color_for(archetype_id, colors):
    if archetype_id not in colors:
        used = {v["hex"] for v in colors.values()}
        name, hex_ = next(((n, h) for n, h in PALETTE if h not in used), PALETTE[len(colors) % len(PALETTE)])
        colors[archetype_id] = {"name": name, "hex": hex_}
        COLORS_FILE.write_text(json.dumps(colors, indent=2) + "\n")
    return colors[archetype_id]["hex"]


# --------------------------------------------------------------------------- template

@dataclass
class TemplateUsage:
    prohibited: set = field(default_factory=set)   # base at-codes with an occurrences 0..0 variant
    kept: dict = field(default_factory=dict)       # base at-code -> number of explicitly kept variants
    filled_slots: set = field(default_factory=set)


# Where the workshop form differs from the COMPLETE template: per archetype, at-code -> number of copies
# kept (0 = constrained out). The form has one 'Dose/frequency' field, so Overall directions description
# instead of the two Specific directions description clones (Dose, Frequency).
FORM_CHANGES = {"openEHR-EHR-INSTRUCTION.medication_order.v3": {"at0173": 0, "at0009": 1}}


def load_template(path):
    """Per parent archetype id: which fields the template prohibits, keeps, clones or fills."""
    data = json.loads(path.read_text(encoding="utf-8"))
    usage = {}

    def walk(node, u):
        if isinstance(node, dict):
            code = node.get("nodeId", "")
            if code.startswith("at") and code != "at0000.1":
                base = code.split(".")[0]
                if node.get("occurrences") == "0..0":
                    u.prohibited.add(base)
                elif node.get("@type") == "C_ARCHETYPE_ROOT":
                    u.filled_slots.add(base)
                elif node.get("rmTypeName") == "ELEMENT":
                    u.kept[base] = u.kept.get(base, 0) + 1
            for v in node.values():
                walk(v, u)
        elif isinstance(node, list):
            for v in node:
                walk(v, u)

    for overlay in data["templateOverlays"]:
        u = usage.setdefault(overlay["parentArchetypeId"], TemplateUsage())
        walk(overlay["definition"], u)
    for aid, changes in FORM_CHANGES.items():
        u = usage.setdefault(aid, TemplateUsage())
        for code, copies in changes.items():
            u.kept.pop(code, None)
            u.prohibited.discard(code)
            if copies:
                u.kept[code] = copies
            else:
                u.prohibited.add(code)
    return usage


def is_used(f, u):
    if u is None:
        return False
    if f.kind == "SLOT":
        return f.code in u.filled_slots
    return f.code in u.kept or f.code not in u.prohibited


STOPWORDS = {"of", "the", "a", "an", "and", "or", "to", "in", "name"}


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def select_fields(fields, u, max_bricks, terms):
    """All fields the template uses (clones repeated), topped up with unused fields as decoys.

    Data elements come before slots, and decoys that share words with a used field go first (e.g. other
    'directions' next to 'Specific directions description'); archetype order is kept."""
    used = [f for f in fields if is_used(f, u)]
    clones = sum(u.kept.get(f.code, 1) - 1 for f in used if f.kind == "ELEMENT") if u else 0
    if max_bricks and len(fields) + clones > max_bricks:
        room = max(max_bricks - len(used) - clones, 0)
        used_words = set().union(*(words(terms.get(f.code, ("",))[0]) for f in used)) if used else set()
        unused = [f for f in fields if f not in used]
        decoys = sorted(unused, key=lambda f: (f.kind == "SLOT",
                                               -len(words(terms.get(f.code, ("",))[0]) & used_words)))[:room]
        fields = [f for f in fields if f in used or f in decoys]
    result = []
    for f in fields:
        copies = u.kept.get(f.code, 1) if u and f in used and f.kind == "ELEMENT" else 1
        result += [f] * max(copies, 1)
    return result, used


def slot_hosts(archetype_id, colors, template_usage):
    """Slots in the other archetypes that explicitly accept this CLUSTER: [(slot, host, host colour)].
    Archetypes in the template come first."""
    hosts = []
    for path in [*EXPORT_DIR.rglob("*.adl"), *DECOY_DIR.glob("*.adl")]:
        text = path.read_text(encoding="utf-8-sig")
        host_id = re.search(r"openEHR-EHR-[A-Z_]+\.[\w-]+\.v\d+", text).group(0)
        if host_id == archetype_id or host_id not in colors:
            continue
        _, host_fields = parse_definition(text)
        terms = parse_terms(text, "en")
        for f in host_fields:
            if f.kind == "SLOT" and accepts(f.slot_target, archetype_id):
                hosts.append((host_id not in template_usage, terms[f.code][0], terms["at0000"][0],
                              colors[host_id]["hex"]))
    return [h[1:] for h in sorted(hosts)]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def process(path, opts, colors):
    text = path.read_text(encoding="utf-8-sig")
    archetype_id = re.search(r"openEHR-EHR-[A-Z_]+\.[\w-]+\.v\d+", text).group(0)
    root_type, fields = parse_definition(text)
    if root_type not in BRICK_RM_TYPES:
        print(f"skip {archetype_id} ({root_type} is a baseplate, not a brick)")
        return
    terms = parse_terms(text, opts.lang)
    bindings = parse_bindings(text)
    for f in fields:
        f.binding = bindings.get(f.code, "")
    if not opts.slots:
        fields = [f for f in fields if f.kind != "SLOT"]
    if not opts.keep_extension:
        fields = [f for f in fields if not (f.kind == "SLOT" and terms.get(f.code, ("",))[0] == "Extension")]

    concept = terms.get("at0000", (archetype_id,))[0]
    label = (concept, root_type.replace("_", " ").title())
    usage = opts.template_usage.get(archetype_id)
    total = len(fields)
    fields, used = select_fields(fields, usage, opts.max_bricks, terms)
    shown = len({f.code for f in fields})
    note = "not in template" if usage is None else f"{len(used)} used in template"
    print(f"{archetype_id}: {len(fields)} bricks (of {total} fields, {note})")
    for f in fields:
        print(f"  {'*' if f in used else ' '} {f.code:8} {f.occurrences:5} {f.location:12} "
              f"{terms.get(f.code, ('?',))[0]:40} {'/'.join(f.types) or f.kind:20} {value_hint(f, terms)[:50]}")
    if opts.dry_run:
        return

    out = OUT_DIR / archetype_id
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("[0-9][0-9]_*.*"):          # blocks from an earlier run with other settings
        stale.unlink()
    color = color_for(archetype_id, colors)
    for f in fields:
        if f.kind == "SLOT":
            f.slot_colors = [c["hex"] for aid, c in colors.items()
                             if aid.startswith("openEHR-EHR-CLUSTER") and accepts(f.slot_target, aid)]
    purpose = first_sentence(terms.get("at0000", ("", ""))[1])
    plugs_into = slot_hosts(archetype_id, colors, opts.template_usage) if root_type == "CLUSTER" else []
    plate = plate_svg(color, label, purpose, plugs_into, shown=(shown, total), binding=bindings.get("at0000", ""))
    (out / "plate.svg").write_text(plate, encoding="utf-8")
    svgs = []
    for i, f in enumerate(fields, 1):
        svg = brick_svg(color, label, f, terms, opts)
        stem = f"{i:02d}_{slug(terms.get(f.code, (f.code,))[0])}"
        (out / f"{stem}.svg").write_text(svg, encoding="utf-8")
        render_png(out / f"{stem}.svg", out / f"{stem}.png")
        svgs.append(svg)
    pdf = build_sheets([plate] + svgs, out, title=label, color=color)
    print(f"  -> {out} ({pdf.name})")
    if opts.blank:
        blank = blank_brick_svg(color, label)
        (out / "blank.svg").write_text(blank, encoding="utf-8")
        render_png(out / "blank.svg", out / "blank.png")
        sheet = build_sheets([plate] + [blank] * 6, out, name="blank_sheet.pdf",
                             title=(concept, f"{label[1]} (write-on)"), color=color)
        print(f"  -> {out} ({sheet.name}, 6 write-on bricks)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archetypes", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="process every .adl in the export")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--no-slots", dest="slots", action="store_false")
    ap.add_argument("--keep-extension", action="store_true")
    ap.add_argument("--stud-logo", action="store_true",
                    help="print 'openEHR' on the studs (default: plain knock-off studs)")
    ap.add_argument("--max-bricks", type=int, default=8,
                    help="max bricks per archetype: every template field plus unused decoy fields "
                         "(default 6: plate + bricks fit one A4 sheet; 0 = every field)")
    ap.add_argument("--template", type=Path, default=TEMPLATE_FILE,
                    help="template (.t.json) that defines which fields are used")
    ap.add_argument("--blank", action="store_true",
                    help="also make an A4 sheet of write-on bricks in the archetype's colour")
    ap.add_argument("--dry-run", action="store_true")
    opts = ap.parse_args()

    paths = [p for p in sorted(EXPORT_DIR.rglob("*.adl")) if p.stem not in EXCLUDED] if opts.all else opts.archetypes
    if not paths:
        ap.error("give one or more .adl files, or --all")
    opts.template_usage = load_template(opts.template) if opts.template.exists() else {}
    colors = load_colors()
    for path in paths:
        process(path, opts, colors)


if __name__ == "__main__":
    sys.exit(main())
