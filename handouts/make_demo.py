#!/usr/bin/env python3
"""Offline demo page: out/demo.html, one self-contained file (font, pieces and forms embedded).

A table with the Encounter baseplate along the bottom: drag headings, plates, building blocks, stickers
and paper forms from the tray and build the template up from the baseplate, in front view. Pieces click
onto the stud grid and onto the piece below them. Double-click a plate, heading, the baseplate, a blank
sticker or a text note to write on it; the x button or the Delete key takes a piece off the table.
"Show the worked example" builds the answer key (make_plates.example).
Run after make_bricks.py (like make_print.py):

    uv run make_demo.py
"""

import base64
import json
import re

from PIL import Image

from make_bricks import OUT_DIR, font_file
from make_plates import (BLOCK, COMPOSITION, PLATE, SECTION, HEADINGS, STUD_MM, baseplate_piece, ensure_colors,
                         example, heading_piece, plate_write_ins)
from make_print import CKM_PILE, EXCLUDED, EXERCISE_3, archetype_names, plate
from make_stickers import CARD_H, CARD_W, CARDINALITY, NAME_H, NAME_W, RENAMES, card_sticker, name_sticker

HERE = OUT_DIR.parent
DEMO = OUT_DIR / "demo.html"
TABLE = {"w": 1200, "h": 460}               # the table in mm; the baseplate lies along the bottom
FORMS = [("Nursing Admission Assessment", HERE / "assets" / "nursing-admission.png"),
         ("Additional information on admission", HERE / "assets" / "additional-info.png")]
FORM_DPI = 150                              # the form images are rendered at 150 dpi (see ../README.md)


def inline(svg):
    """Root <svg> without fixed width/height, so CSS sizes it."""
    return re.sub(r'<svg([^>]*?) width="[^"]+" height="[^"]+"', r"<svg\1", svg, count=1)


def mm_svg(parts, w, h, pad=0.5):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" '
            f'font-family="Lexend, sans-serif">' + "".join(parts) + "</svg>")


def face(piece):
    """Front face (left, top, bottom, width) as fractions of the piece's width, for snapping."""
    return [v / piece["w"] for v in piece["face"]]


def strip(piece, **more):
    return {"kind": "strip", "w": piece["w"], "svg": mm_svg(piece["parts"], piece["w"], piece["h"], 0),
            "write": piece["write"], "face": face(piece), **more}


def blocks(aid):
    return [(path.stem, path.read_text(encoding="utf-8")) for path in sorted((OUT_DIR / aid).glob("[0-9][0-9]_*.svg"))]


def items():
    colors = {aid: c for aid, c in ensure_colors().items() if aid not in EXCLUDED}
    names = archetype_names()
    held_back = set(CKM_PILE) | {EXERCISE_3, COMPOSITION, SECTION}
    table = sorted((aid for aid in colors if aid not in held_back), key=lambda aid: names[aid].lower())
    out = [{"id": "base", "fixed": True, **strip(baseplate_piece(), aid=COMPOSITION)}]   # always on the table

    def add(tab, group, item):
        out.append({"id": f"i{len(out)}", "tab": tab, "group": group, **item})

    def plate_item(aid):
        return {"kind": "plate", "aid": aid, "w": PLATE["w"], "svg": inline(plate(aid)), "write": plate_write_ins(),
                "face": face(PLATE)}

    def block_items(tab, aid):
        for stem, svg in blocks(aid):
            add(tab, names[aid], {"kind": "block", "aid": aid, "stem": stem, "w": BLOCK["w"], "svg": inline(svg),
                                  "face": face(BLOCK)})

    for _ in range(HEADINGS):
        add("Structure", "Ad hoc headings (SECTION)", strip(heading_piece(), aid=SECTION))
    for aid in table:
        add("Plates", "Archetype plates", plate_item(aid))
    for aid in table:
        block_items("Blocks", aid)
    for aid in CKM_PILE:
        add("CKM desk", names[aid], plate_item(aid))
        block_items("CKM desk", aid)
    for label, n in CARDINALITY:
        for _ in range(min(n, 3)):
            write = [] if label else [{"key": "text", "x": 0.5, "y": 0.72, "size": 0.22, "anchor": "middle",
                                       "prompt": "Cardinality, e.g. 1..1"}]
            add("Stickers", "Cardinality", {"kind": "sticker", "sticker": "card", "label": label, "w": CARD_W + 1,
                                            "svg": mm_svg(card_sticker(0, 0, label if label else ""), CARD_W,
                                                          CARD_H), "write": write})
    for title, path in FORMS:
        mm = Image.open(path).width / FORM_DPI * 25.4
        add("Forms", "Paper forms", {"kind": "form", "w": mm,
                                     "svg": f'<img alt="Paper form: {title}" src="{data_uri(path, "image/png")}">'})
    for label, n in RENAMES:
        for _ in range(n):                    # enough blanks for the worked example
            write = [] if label else [{"key": "text", "x": 3.5 / (NAME_W + 1), "y": (NAME_H - 1.6) / (NAME_H + 1),
                                       "size": 0.068, "prompt": "New name"}]
            add("Stickers", "Rename", {"kind": "sticker", "sticker": "name", "label": label, "w": NAME_W + 1,
                                       "svg": mm_svg(name_sticker(0, 0, label), NAME_W, NAME_H), "write": write})
    return out


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    page = (PAGE
            .replace("/*FONT*/", data_uri(font_file("Lexend-VariableFont_wght.ttf"), "font/ttf"))
            .replace("/*ITEMS*/", json.dumps(items()).replace("</", "<\\/"))
            .replace("/*EXAMPLE*/", json.dumps(example()))
            .replace("/*TABLE*/", json.dumps(TABLE))
            .replace("/*STUD*/", f"{STUD_MM:g}"))
    DEMO.write_text(page, encoding="utf-8")
    print(f"-> {DEMO} ({DEMO.stat().st_size / 1e6:.1f} MB)")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>openEHR building blocks</title>
<style>
@font-face { font-family: Lexend; src: url("/*FONT*/") format("truetype"); font-weight: 100 900; }
:root { --tray: 340px; --ink: #1B1B1B; --muted: #6b6b6b; --line: #d9d6cf; --bg: #f3f1ec; --paper: #fff; }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { font-family: Lexend, sans-serif; color: var(--ink); background: var(--bg); display: grid;
       grid-template-columns: var(--tray) 1fr; grid-template-rows: 100%; height: 100vh; height: 100dvh;
       overflow: hidden; }
#side { display: flex; flex-direction: column; min-height: 0; height: 100%; border-right: 1px solid var(--line);
        background: var(--paper); }
.show { position: relative; padding: 14px 16px; border-bottom: 1px solid var(--line); }
.show h1 { margin: 2px 0 2px; font-size: 20px; font-weight: 800; line-height: 1.2; }
.show .sub { margin: 0 0 14px; font-size: 13px; font-weight: 600; color: var(--muted); }
.show label { display: block; margin-bottom: 6px; }
.show select { width: 100%; font-size: 15px; padding: 8px 10px; }
#tools { position: absolute; bottom: 36px; right: 40px; z-index: 300000; display: flex; gap: 6px; align-items: center;
         padding: 6px; background: var(--paper); border: 1px solid var(--line); border-radius: 12px;
         box-shadow: 0 4px 14px rgba(0,0,0,.10); }
#tools .size { display: flex; align-items: center; gap: 2px; padding-left: 8px; font-size: 14px; font-weight: 600;
               color: var(--muted); }
#tools .size button { width: 34px; padding: 6px 0; font-size: 16px; }
#tools .sep { width: 1px; align-self: stretch; background: var(--line); margin: 0 4px; }
button, select { font: inherit; font-size: 14px; font-weight: 600; border: 1px solid var(--line);
                 background: var(--paper); border-radius: 8px; padding: 6px 12px; cursor: pointer; color: var(--ink); }
button[aria-pressed="true"] { background: var(--ink); color: #fff; border-color: var(--ink); }
button:disabled { opacity: .4; cursor: default; }
button.icon { display: inline-flex; align-items: center; justify-content: center; padding: 6px 9px; }
button.icon[hidden] { display: none; }
#full .leave, .fullscreen #full .enter { display: none; }
.fullscreen #full .leave { display: inline; }
.phone-only { display: none; }
label { font-size: 14px; font-weight: 600; color: var(--muted); display: flex; gap: 8px; align-items: center; }
.spacer { flex: 1; }
#tray { flex: 1; overflow-y: auto; padding: 4px 16px 40px; }
#tray h2 { font-size: 13px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
           margin: 18px 0 8px; }
#tray .piece { position: relative; width: 100%; margin-bottom: 10px; touch-action: pan-y; }
#tray .piece.sticker { display: inline-block; width: auto; margin-right: 8px; }
#tray .empty { color: var(--muted); font-size: 14px; }
#wrap { overflow: hidden; position: relative; touch-action: none; }
#board { position: absolute; left: 0; top: 0; transform-origin: 0 0; background: var(--paper);
         border: 1px solid var(--line); box-shadow: 0 2px 10px rgba(0,0,0,.06); }
#board::before { content: "The table: build the template up from the Encounter baseplate"; position: absolute;
                 left: 24px; top: 16px; font-size: 40px; font-weight: 600; color: #c9c4ba; }
#wrap.panning { cursor: grabbing; }
.piece { touch-action: none; user-select: none; cursor: grab; }
.piece svg { display: block; width: 100%; height: auto; pointer-events: none; }
#board .piece { position: absolute; filter: drop-shadow(0 2px 3px rgba(0,0,0,.15)); }
.piece.dragging { cursor: grabbing; filter: drop-shadow(0 8px 14px rgba(0,0,0,.25)); z-index: 9999999 !important; }
#board .piece.fixed { cursor: default; }
.ink { position: absolute; font-family: Lexend, sans-serif; font-weight: 600; color: #1d3f8f;
       white-space: nowrap; pointer-events: none; transform: translateY(-100%); line-height: 1; }
.ink.middle { transform: translate(-50%, -100%); }
.ink.bg:not(:empty) { background: #fff; padding: 0 .2em; margin-left: -.2em; }   /* writes over the printed label */
.piece img { display: block; width: 100%; height: auto; pointer-events: none; }
.piece.form { border: 1px solid var(--line); background: #fff; }
#board .piece.form { filter: none; box-shadow: 0 1px 6px rgba(0,0,0,.12); }
.piece.note { padding: .15em .35em; background: #fff8c4; border: 1px solid #e3d77a; border-radius: 4px;
              font-family: Lexend, sans-serif; font-weight: 600; color: #1d3f8f;
              white-space: pre-wrap; min-width: 2em; line-height: 1.25; }
.piece.note[contenteditable="true"] { cursor: text; outline: 2px solid #1d3f8f; user-select: text; }
/* handles keep their on-screen size whatever the zoom: --inv = 1 / zoom, set by applyView */
.del { display: none; position: absolute; top: calc(-12px * var(--inv, 1)); right: calc(-12px * var(--inv, 1));
       width: calc(26px * var(--inv, 1)); height: calc(26px * var(--inv, 1)); padding: 0;
       border-radius: 50%; font-size: calc(16px * var(--inv, 1)); line-height: 1; background: var(--ink); color: #fff;
       border: calc(2px * var(--inv, 1)) solid #fff; z-index: 2; font-family: Lexend, sans-serif; }
#board .piece:hover > .del, #board .piece.selected > .del { display: block; }
.piece.note > .del { right: -34px; top: -6px; }
.grip { display: none; position: absolute; right: calc(-8px * var(--inv, 1)); bottom: calc(-8px * var(--inv, 1));
        width: calc(18px * var(--inv, 1)); height: calc(18px * var(--inv, 1)); border-radius: calc(4px * var(--inv, 1));
        background: #fff; border: calc(2px * var(--inv, 1)) solid var(--ink); cursor: nwse-resize; z-index: 2; }
#board .piece:hover > .grip, #board .piece.selected > .grip { display: block; }
#board .piece.selected { outline: calc(2px * var(--inv, 1)) dashed #1d3f8f; outline-offset: calc(3px * var(--inv, 1)); }
/* the baseplate stays put; pieces on the stud grid keep their size */
#board .piece.fixed > .del, #board .piece.fixed > .grip, #board .piece[data-face] > .grip { display: none !important; }
.show .wide { width: 100%; margin-top: 12px; }
button:focus-visible, select:focus-visible { outline: 2px solid #1d3f8f; outline-offset: 2px; }
/* our own dialog instead of the browser's prompt() and confirm() boxes */
#ask { border: 1px solid var(--line); border-radius: 14px; padding: 22px 24px 18px; width: min(420px, 90vw);
       background: var(--paper); color: var(--ink); box-shadow: 0 12px 40px rgba(0,0,0,.18); }
#ask::backdrop { background: rgba(40, 36, 28, .25); }
#ask p { margin: 0 0 14px; font-size: 16px; font-weight: 600; line-height: 1.4; }
#ask label { display: block; margin: 0 0 14px; color: var(--muted); }
#ask input { display: block; width: 100%; box-sizing: border-box; margin-top: 6px; padding: 9px 11px;
             font: inherit; font-size: 17px; font-weight: 600; color: #1d3f8f; border: 1px solid var(--line);
             border-radius: 8px; background: #fff; }
#ask input:focus { outline: 2px solid #1d3f8f; outline-offset: 0; border-color: transparent; }
#ask .buttons { display: flex; justify-content: flex-end; gap: 8px; margin-top: 6px; }
#ask .primary { background: var(--ink); color: #fff; border-color: var(--ink); }
/* phones: the tray is a drawer, you pinch-zoom and pan the table, and handles are finger-sized */
@media (max-width: 700px), (pointer: coarse) and (max-height: 500px) {
  body { grid-template-columns: 1fr; }
  #side { position: fixed; left: 0; top: 0; bottom: 0; width: min(340px, 86vw); height: auto; z-index: 400000;
          transform: translateX(-102%); transition: transform .2s ease; box-shadow: 4px 0 24px rgba(0,0,0,.18); }
  body.drawer #side { transform: none; }
  .phone-only { display: inline-block; }
  .show .close { position: absolute; top: 10px; right: 10px; width: 44px; height: 44px; padding: 0; font-size: 22px; }
  .show h1 { padding-right: 48px; }
  #tools { left: 10px; right: 10px; bottom: 10px; justify-content: center; }
  #tools .size, #tools .sep { display: none; }
  #tools { gap: 5px; }
  #tools button { min-height: 44px; padding: 8px 10px; font-size: 15px; }
  #tools button.icon { min-width: 44px; padding: 0; }
  .del { width: calc(40px * var(--inv)); height: calc(40px * var(--inv)); top: calc(-20px * var(--inv));
         right: calc(-20px * var(--inv)); font-size: calc(22px * var(--inv)); border-width: calc(2px * var(--inv)); }
  .piece.note > .del { right: calc(-46px * var(--inv)); top: calc(-8px * var(--inv)); }
  .grip { width: calc(30px * var(--inv)); height: calc(30px * var(--inv)); right: calc(-15px * var(--inv));
          bottom: calc(-15px * var(--inv)); border-width: calc(2px * var(--inv)); border-radius: calc(6px * var(--inv)); }
  #board .piece:hover > .del, #board .piece:hover > .grip { display: none; }
  #board .piece.selected > .del, #board .piece.selected > .grip { display: block; }
  #board .piece.selected { outline-width: calc(2px * var(--inv)); outline-offset: calc(3px * var(--inv)); }
}
</style>
</head>
<body>
<aside id="side">
  <div class="show">
    <button id="closeTray" class="phone-only close" aria-label="Close">×</button>
    <h1>openEHR building blocks</h1>
    <p class="sub">Datapoort workshop demo</p>
    <label for="view">Show</label>
    <select id="view"></select>
    <button id="example" class="wide">Show the worked example</button>
  </div>
  <div id="tray" aria-label="Pieces"></div>
</aside>
<div id="wrap">
  <div id="board"></div>
  <div id="tools" role="toolbar" aria-label="Sheet tools">
    <button id="openTray" class="phone-only">Pieces</button>
    <div class="size">Zoom <button id="zoomOut" aria-label="Zoom out">−</button>
      <button id="zoomIn" aria-label="Zoom in">+</button></div>
    <div class="sep"></div>
    <button id="writeBtn" class="phone-only" disabled>Write</button>
    <button id="addText">Text</button>
    <button id="fit">Fit</button>
    <button id="reset">Clear</button>
    <button id="full" class="icon" aria-label="Full screen" title="Full screen" hidden>
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path class="enter" d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/>
        <path class="leave" d="M9 4v5H4M20 9h-5V4M15 20v-5h5M4 15h5v5"/>
      </svg></button>
  </div>
</div>
<dialog id="ask">
  <form method="dialog">
    <div class="fields"></div>
    <div class="buttons"><button value="cancel" formnovalidate>Cancel</button>
      <button value="ok" class="primary">OK</button></div>
  </form>
</dialog>
<script>
const ITEMS = /*ITEMS*/;
const EXAMPLE = /*EXAMPLE*/;                  // the answer key, in mm from the baseplate's top left
const TABLE = /*TABLE*/;                      // mm
const STUD = /*STUD*/;                        // stud pitch in mm: a block is 4 studs, a plate 8
const viewOf = i => i.tab === "Blocks" ? "Blocks|" + i.group : i.tab;
const VIEWS = [                               // the tray's "Show" menu, in workshop order
  ["Exercise 0: choose the archetypes", [["Structure", "Ad hoc headings"], ["Plates", "Archetype plates"],
                                         ["CKM desk", "CKM desk"]]],
  ["Exercise 1: choose the elements",
   [...new Set(ITEMS.filter(i => i.tab === "Blocks").map(i => i.group))].map(g => ["Blocks|" + g, "Building blocks: " + g])
     .concat([["Stickers", "Template stickers"]])],
  ["Reference", [["Forms", "Paper forms"]]],
];
const state = { view: "Structure", scale: 3.5, placed: new Map(), z: 1, selected: null, notes: 0,
                zoom: 1, pan: { x: 24, y: 24 }, phone: false };
const PHONE = "(max-width: 700px), (pointer: coarse) and (max-height: 500px)";   // same as the CSS
const NOTE_MM = 7;                            // text note font size, mm on the sheet
const $ = s => document.querySelector(s);
const tray = $("#tray"), board = $("#board"), wrap = $("#wrap");

function piece(item) {
  const el = document.createElement("div");
  el.className = "piece " + item.kind + (item.fixed ? " fixed" : "");
  el.dataset.id = item.id;
  if (item.face) el.dataset.face = "";
  el.innerHTML = item.svg || "";
  (item.write || []).forEach(w => {
    const t = document.createElement("div");
    t.className = "ink" + (w.anchor === "middle" ? " middle" : "") + (w.bg ? " bg" : "");
    t.dataset.key = w.key;
    t.style.left = (w.x * 100) + "%";
    t.style.top = (w.y * 100) + "%";
    el.appendChild(t);
  });
  const del = document.createElement("button");
  del.className = "del";
  del.textContent = "×";
  del.contentEditable = "false";
  del.title = "Take off the sheet";
  del.setAttribute("aria-label", "Take off the sheet");
  del.addEventListener("pointerdown", e => e.stopPropagation());
  del.addEventListener("click", e => { e.stopPropagation(); remove(item); });
  el.appendChild(del);
  const grip = document.createElement("div");
  grip.className = "grip";
  grip.title = "Drag to resize";
  grip.contentEditable = "false";
  grip.addEventListener("pointerdown", e => startResize(e, el, item));
  el.appendChild(grip);
  el.addEventListener("pointerdown", e => startDrag(e, el, item));
  el.addEventListener("click", () => { if (!state.placed.has(item.id)) placeInView(item); });   // a tap in the tray
  el.addEventListener("dblclick", () => item.kind === "note" ? editNote(el) : write(el, item));
  return el;
}
const pieces = new Map(ITEMS.map(i => [i.id, piece(i)]));

function sizeInk(el, item, widthPx) {
  (item.write || []).forEach(w => {
    const t = el.querySelector(`.ink[data-key="${w.key}"]`);
    if (t) t.style.fontSize = (w.size * widthPx) + "px";
  });
}

function renderViews() {
  $("#view").innerHTML = VIEWS.map(([step, views]) => `<optgroup label="${step}">` +
    views.map(([key, label]) => `<option value="${key}">${label}</option>`).join("") + "</optgroup>").join("");
  $("#view").value = state.view;
}
$("#view").onchange = e => { state.view = e.target.value; renderTray(); };

function renderTray() {
  tray.innerHTML = "";
  const list = ITEMS.filter(i => i.tab && viewOf(i) === state.view && !state.placed.has(i.id));
  const inner = tray.clientWidth - 32;
  let group = null;
  list.forEach(item => {
    if (item.group !== group) {
      group = item.group;
      const h = document.createElement("h2");
      h.textContent = group;
      tray.appendChild(h);
    }
    const el = pieces.get(item.id);
    el.style.left = el.style.top = el.style.zIndex = "";
    const w = item.kind === "sticker" ? Math.min(inner, item.w * 2) : inner;
    el.style.width = w + "px";
    sizeInk(el, item, w);
    tray.appendChild(el);
  });
  if (!list.length) tray.insertAdjacentHTML("beforeend", '<p class="empty">All of these are on the sheet.</p>');
}

function applyView() {
  board.style.transform = `translate(${state.pan.x}px, ${state.pan.y}px) scale(${state.zoom})`;
  board.style.setProperty("--inv", 1 / state.zoom);
}

function fit() {                              // the whole table in view (on a phone: above the toolbar)
  const s = state.scale, w = wrap.clientWidth;
  const h = wrap.clientHeight - (state.phone ? $("#tools").offsetHeight + 20 : 0);
  state.zoom = Math.min((w - 20) / (TABLE.w * s), (h - 20) / (TABLE.h * s));
  state.pan = { x: (w - TABLE.w * s * state.zoom) / 2, y: (h - TABLE.h * s * state.zoom) / 2 };
  applyView();
}

function zoomAt(clientX, clientY, factor) {   // keeps the table point under (clientX, clientY) in place
  const r = wrap.getBoundingClientRect(), z = Math.min(3, Math.max(0.08, state.zoom * factor));
  const sx = (clientX - r.left - state.pan.x) / state.zoom, sy = (clientY - r.top - state.pan.y) / state.zoom;
  state.zoom = z;
  state.pan = { x: clientX - r.left - sx * z, y: clientY - r.top - sy * z };
  applyView();
}

// Front face of a placed piece, in px on the table: left, right, top, bottom.
function faceOf(item, pos) {
  const w = item.w * state.scale, f = item.face;
  return { l: pos.x + f[0] * w, r: pos.x + (f[0] + f[3]) * w, t: pos.y + f[1] * w, b: pos.y + f[2] * w };
}

// Pieces click into place: the front face on the baseplate's stud grid, and standing on the top of
// the piece just below it when it is close.
function snap(item, pos) {
  if (!item.face || item.fixed) return;
  const s = state.scale, w = item.w * s, f = item.face, pitch = STUD * s;
  const base = faceOf(ITEMS[0], state.placed.get("base"));
  const l = base.l + Math.round((pos.x + f[0] * w - base.l) / pitch) * pitch;
  pos.x = l - f[0] * w;
  const r = l + f[3] * w, b = pos.y + f[2] * w;
  let best = null;
  state.placed.forEach((p, id) => {
    const other = ITEMS.find(i => i.id === id);
    if (id === item.id || !other.face) return;
    const g = faceOf(other, p);
    if (g.r <= l + 1 || g.l >= r - 1) return;   // not underneath
    const d = Math.abs(g.t - b);
    if (d < 14 * s && (!best || d < best.d)) best = { d, t: g.t };
  });
  if (best) pos.y = best.t - f[2] * w;
}

// Front view: a piece higher up covers the studs of the one below it, and of two pieces side by side
// the right one covers the left one's side face. Forms stay underneath, stickers and notes on top.
function zOf(item, pos) {
  if (item.kind === "form") return pos.z;
  if (!item.face) return 1000000 + pos.z;
  const f = faceOf(item, pos), s = state.scale;
  return 1000 + Math.round((TABLE.h * s - f.b) / s) * 1000 + Math.round(f.l / s);
}

function layoutBoard() {
  const s = state.scale;                      // px per mm of the printed pieces
  board.style.width = TABLE.w * s + "px";
  board.style.height = TABLE.h * s + "px";
  applyView();
  state.placed.forEach((pos, id) => {         // positions in px on the table
    const el = pieces.get(id), item = ITEMS.find(i => i.id === id);
    el.style.left = pos.x + "px";
    el.style.top = pos.y + "px";
    el.style.zIndex = zOf(item, pos);
    const k = item.face ? 1 : pos.k || 1;     // the piece's own size, set with its resize handle
    if (item.kind === "note") el.style.fontSize = NOTE_MM * s * k + "px";
    else { el.style.width = item.w * s * k + "px"; sizeInk(el, item, item.w * s * k); }
  });
}

function select(el) {
  if (state.selected) state.selected.classList.remove("selected");
  state.selected = el;
  if (el) el.classList.add("selected");
  const item = el && ITEMS.find(i => i.id === el.dataset.id);
  $("#writeBtn").disabled = !(item && (item.kind === "note" || (item.write || []).length));
}

// Sheet position (unzoomed px) of a point on the screen.
function toSheet(clientX, clientY) {
  const b = board.getBoundingClientRect();
  return { x: (clientX - b.left) / state.zoom, y: (clientY - b.top) / state.zoom };
}

function placeInView(item) {                  // tap in the tray: put the piece in the middle of the view
  const el = pieces.get(item.id);
  const pos = { x: 0, y: 0, z: ++state.z };
  state.placed.set(item.id, pos);
  board.appendChild(el);
  layoutBoard();
  const r = wrap.getBoundingClientRect(), c = toSheet(r.left + r.width / 2, r.top + r.height * 0.4);
  const n = state.placed.size % 5;           // a small step, so pieces don't land exactly on top of each other
  pos.x = c.x - el.offsetWidth / 2 + n * 14;
  pos.y = c.y - el.offsetHeight / 2 + n * 14;
  snap(item, pos);
  layoutBoard();
  select(el);
  renderTray();
  closeTray();
}

const openTray = () => { document.body.classList.add("drawer"); renderTray(); };

function showBlocks(plate) {                  // the tray switches to the building blocks of this archetype
  const block = ITEMS.find(i => i.kind === "block" && i.aid === plate.aid);
  if (!block) return;
  state.view = viewOf(block);
  $("#view").value = state.view;
  renderTray();
  if (state.phone) openTray();
}
const closeTray = () => document.body.classList.remove("drawer");

function remove(item) {
  if (item.fixed) return;
  const el = pieces.get(item.id);
  state.placed.delete(item.id);
  if (state.selected === el) select(null);
  if (item.kind === "note") {                   // notes don't go back to the tray
    el.remove();
    pieces.delete(item.id);
    ITEMS.splice(ITEMS.indexOf(item), 1);
    return;
  }
  state.view = viewOf(item);
  $("#view").value = state.view;
  renderTray();
}

function editNote(el) {
  el.contentEditable = "true";
  el.focus();
  document.getSelection().selectAllChildren(el.firstChild);
}

function addNote() {
  const item = { id: "n" + ++state.notes, kind: "note", w: 0 };
  ITEMS.push(item);
  const el = piece(item);
  const text = document.createElement("span");
  text.textContent = "Text";
  el.prepend(text);
  el.addEventListener("blur", () => { el.contentEditable = "false"; if (!text.textContent.trim()) remove(item); }, true);
  pieces.set(item.id, el);
  const w = wrap.getBoundingClientRect(), c = toSheet(w.left + w.width / 2, w.top + w.height * 0.4);
  state.placed.set(item.id, { x: c.x - 60, y: c.y, z: ++state.z });
  board.appendChild(el);
  layoutBoard();
  select(el);
  editNote(el);
}

function startResize(e, el, item) {
  if (e.button !== 0) return;
  e.preventDefault();
  e.stopPropagation();
  const pos = state.placed.get(item.id), grip = e.currentTarget;
  const startK = pos.k || 1, startW = el.offsetWidth, x0 = e.clientX;
  grip.setPointerCapture(e.pointerId);
  const move = ev => {
    pos.k = Math.max(0.3, Math.min(5, startK * (startW + (ev.clientX - x0) / state.zoom) / startW));
    layoutBoard();
  };
  const end = () => { grip.removeEventListener("pointermove", move); state.cancelDrag = null; };
  state.cancelDrag = () => { end(); pos.k = startK; layoutBoard(); };   // a second finger: pinch instead
  grip.addEventListener("pointermove", move);
  grip.addEventListener("pointerup", end, { once: true });
}

function startDrag(e, el, item) {
  if (e.button !== 0 || el.isContentEditable) return;
  if (item.fixed) { select(el); return; }
  if (e.pointerType === "touch" && !state.placed.has(item.id)) return;   // in the tray a finger scrolls; a tap places
  e.preventDefault();
  if (document.activeElement && document.activeElement.isContentEditable) document.activeElement.blur();
  const s = state.scale;
  const rect = el.getBoundingClientRect();
  const grab = { x: (e.clientX - rect.left) / rect.width, y: (e.clientY - rect.top) / rect.height };
  if (!state.placed.has(item.id)) {
    state.placed.set(item.id, { x: 0, y: 0, z: ++state.z });
    board.appendChild(el);
    renderTray();
  }
  const pos = state.placed.get(item.id), start = { x: pos.x, y: pos.y }, wasPlaced = el.parentNode === board;
  const down = { x: e.clientX, y: e.clientY };
  pos.z = ++state.z;
  select(el);
  el.classList.add("dragging");
  el.setPointerCapture(e.pointerId);
  const move = ev => {
    const p = toSheet(ev.clientX, ev.clientY);
    const w = el.offsetWidth || item.w * s, h = el.offsetHeight || w * 0.6;
    pos.x = Math.min(Math.max(p.x - grab.x * w, -w / 2), board.offsetWidth - w / 2);
    pos.y = Math.min(Math.max(p.y - grab.y * h, -h / 2), board.offsetHeight - h / 2);
    snap(item, pos);
    layoutBoard();
  };
  const end = () => {
    el.classList.remove("dragging");
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", up);
    state.cancelDrag = null;
  };
  const up = ev => {
    end();
    const t = $("#side").getBoundingClientRect();
    if (ev.clientX < t.right && ev.clientX >= t.left) remove(item);   // dropped back on the tray
    else if (wasPlaced && item.kind === "plate" && Math.hypot(ev.clientX - down.x, ev.clientY - down.y) < 6) {
      Object.assign(pos, start);              // a click, not a move: show the archetype's building blocks
      layoutBoard();
      showBlocks(item);
    }
  };
  state.cancelDrag = () => { end(); Object.assign(pos, start); layoutBoard(); };   // a second finger: pinch instead
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", up);
  move(e);
}

// Shows #ask with a message or text fields; resolves to the field values (OK) or null (Cancel, Esc).
function ask({ message = "", fields = [], ok = "OK" }) {
  const dlg = $("#ask"), box = dlg.querySelector(".fields");
  box.textContent = "";
  if (message) box.appendChild(Object.assign(document.createElement("p"), { textContent: message }));
  const inputs = fields.map(f => {
    const label = Object.assign(document.createElement("label"), { textContent: f.label });
    const input = Object.assign(document.createElement("input"), { type: "text", value: f.value, autocomplete: "off" });
    label.appendChild(input);
    box.appendChild(label);
    return input;
  });
  dlg.querySelector(".primary").textContent = ok;
  dlg.returnValue = "";
  dlg.showModal();
  if (inputs.length) inputs[0].select();
  else dlg.querySelector(".primary").focus();
  return new Promise(done => dlg.addEventListener("close",
    () => done(dlg.returnValue === "ok" ? inputs.map(i => i.value) : null), { once: true }));
}

async function write(el, item) {
  const ws = item.write || [];
  if (!ws.length) return;
  const inks = ws.map(w => el.querySelector(`.ink[data-key="${w.key}"]`));
  const values = await ask({ fields: ws.map((w, i) => ({ label: w.prompt, value: inks[i].textContent })) });
  if (values) values.forEach((v, i) => inks[i].textContent = v);
}

const zoomBy = f => { const r = wrap.getBoundingClientRect(); zoomAt(r.left + r.width / 2, r.top + r.height / 2, f); };
$("#zoomOut").onclick = () => zoomBy(1 / 1.25);
$("#zoomIn").onclick = () => zoomBy(1.25);

function placeBase() {                        // the baseplate lies along the bottom of the table
  const s = state.scale, base = ITEMS[0], el = pieces.get(base.id);
  el.style.width = base.w * s + "px";
  board.appendChild(el);
  state.placed.set(base.id, { x: (TABLE.w - base.w) / 2 * s, y: (TABLE.h - 30) * s - el.offsetHeight, z: 0 });
}

function clearTable() {
  ITEMS.filter(i => i.kind === "note").forEach(remove);
  state.placed.clear();
  board.querySelectorAll(".piece").forEach(el => el.remove());   // back to the tray: renderTray adds them again
  select(null);
  pieces.forEach(el => el.querySelectorAll(".ink").forEach(t => t.textContent = ""));
  layoutBoard();
  placeBase();
  renderTray(); layoutBoard();
}
$("#reset").onclick = async () => {
  if (!await ask({ message: "Put every piece back on the tray and delete the text notes?", ok: "Clear table" })) return;
  clearTable();
};

// The answer key, built on the baseplate: each piece of EXAMPLE takes a matching piece from the tray.
$("#example").onclick = async () => {
  if (state.placed.size > 1 && !await ask({ message: "Replace what is on the table with the worked example?",
                                            ok: "Show example" })) return;
  clearTable();
  const s = state.scale, base = state.placed.get("base"), used = new Set(["base"]);
  EXAMPLE.forEach(ex => {
    const kind = ex.kind === "heading" ? "strip" : ex.kind;
    const same = i => ex.kind === "sticker" ? i.sticker === ex.sticker && (i.label || null) === ex.label
                                            : i.aid === ex.aid && (!ex.stem || i.stem === ex.stem);
    const item = ex.kind === "baseplate" ? ITEMS[0] : ITEMS.find(i => !used.has(i.id) && i.tab && i.kind === kind && same(i));
    if (!item) return;
    used.add(item.id);
    const el = pieces.get(item.id);
    const pad = ex.kind === "sticker" ? 0.5 : 0;   // sticker pieces have a 0.5 mm margin around the sticker
    state.placed.set(item.id, { x: base.x + (ex.x - pad) * s, y: base.y + (ex.y - pad) * s, z: ++state.z });
    board.appendChild(el);
    Object.entries(ex.ink || {}).forEach(([key, text]) => {
      const t = el.querySelector(`.ink[data-key="${key}"]`);
      if (t) t.textContent = text;
    });
  });
  renderTray(); layoutBoard(); closeTray(); fit();
};
$("#addText").onclick = addNote;
$("#openTray").onclick = openTray;
$("#closeTray").onclick = closeTray;
$("#fit").onclick = fit;

// Full screen where the browser allows it for a page (not on iPhone): the button stays hidden otherwise.
const root = document.documentElement;
const fullElement = () => document.fullscreenElement || document.webkitFullscreenElement;
if (root.requestFullscreen || root.webkitRequestFullscreen) $("#full").hidden = false;
$("#full").onclick = () => {
  if (fullElement()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  else (root.requestFullscreen || root.webkitRequestFullscreen).call(root);
};
const onFull = () => {
  const on = !!fullElement();
  document.body.classList.toggle("fullscreen", on);
  $("#full").title = on ? "Leave full screen" : "Full screen";
  $("#full").setAttribute("aria-label", $("#full").title);
};
document.addEventListener("fullscreenchange", onFull);
document.addEventListener("webkitfullscreenchange", onFull);
$("#writeBtn").onclick = () => {
  const el = state.selected, item = el && ITEMS.find(i => i.id === el.dataset.id);
  if (item) item.kind === "note" ? editNote(el) : write(el, item);
};

// Mouse: drag the empty table to pan; the wheel zooms (a trackpad's two-finger scroll pans, pinch zooms).
wrap.addEventListener("pointerdown", e => {
  if (e.pointerType === "touch" || e.button !== 0 || (e.target !== board && e.target !== wrap)) return;
  const start = { x: e.clientX, y: e.clientY, pan: { ...state.pan } };
  wrap.setPointerCapture(e.pointerId);
  wrap.classList.add("panning");
  const move = ev => {
    state.pan = { x: start.pan.x + ev.clientX - start.x, y: start.pan.y + ev.clientY - start.y };
    applyView();
  };
  wrap.addEventListener("pointermove", move);
  wrap.addEventListener("pointerup", () => {
    wrap.removeEventListener("pointermove", move);
    wrap.classList.remove("panning");
  }, { once: true });
});
wrap.addEventListener("wheel", e => {
  if (e.target.closest("#tools")) return;
  e.preventDefault();
  const mouseWheel = e.deltaMode !== 0 || (e.deltaX === 0 && Math.abs(e.deltaY) >= 50);
  if (e.ctrlKey || mouseWheel) zoomAt(e.clientX, e.clientY, Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.002)));
  else { state.pan = { x: state.pan.x - e.deltaX, y: state.pan.y - e.deltaY }; applyView(); }
}, { passive: false });

// Touch: one finger on the empty table pans, two fingers pinch-zoom around the point between them.
// One finger on a piece drags it; as soon as a second finger touches (anywhere), that drag is undone
// and both fingers zoom. The listeners run in the capture phase, before the pieces' own.
const touches = new Map();
let gesture = null;
const restartGesture = () => {
  gesture = touches.size ? { pts: [...touches.values()].map(p => ({ ...p })), zoom: state.zoom,
                             pan: { ...state.pan } } : null;
};
wrap.addEventListener("pointerdown", e => {
  if (e.pointerType !== "touch") return;
  if (document.body.classList.contains("drawer")) { closeTray(); e.stopPropagation(); return; }
  if (e.target.closest("#tools")) return;
  touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (touches.size === 1 && e.target.closest(".piece")) { gesture = null; return; }   // the piece's own drag
  if (touches.size > 1) {
    if (state.cancelDrag) state.cancelDrag();
    e.stopPropagation();
  }
  wrap.setPointerCapture(e.pointerId);
  restartGesture();
}, true);
wrap.addEventListener("pointermove", e => {
  if (!touches.has(e.pointerId)) return;
  touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (!gesture) return;                       // one finger dragging a piece
  e.stopPropagation();
  const p = [...touches.values()], g = gesture;
  if (p.length === 1) {
    state.pan = { x: g.pan.x + p[0].x - g.pts[0].x, y: g.pan.y + p[0].y - g.pts[0].y };
  } else {
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) || 1;
    const mid = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
    const r = wrap.getBoundingClientRect(), m0 = mid(g.pts[0], g.pts[1]), m = mid(p[0], p[1]);
    const z = Math.min(3, Math.max(0.08, g.zoom * dist(p[0], p[1]) / dist(g.pts[0], g.pts[1])));
    const sx = (m0.x - r.left - g.pan.x) / g.zoom, sy = (m0.y - r.top - g.pan.y) / g.zoom;   // sheet point under the fingers
    state.zoom = z;
    state.pan = { x: m.x - r.left - sx * z, y: m.y - r.top - sy * z };
  }
  applyView();
}, true);
const liftFinger = e => {
  if (!touches.delete(e.pointerId)) return;
  if (gesture) restartGesture();              // two fingers to one: carry on panning with the other
};
wrap.addEventListener("pointerup", liftFinger, true);
wrap.addEventListener("pointercancel", liftFinger, true);
document.addEventListener("gesturestart", e => e.preventDefault());   // Safari: no page zoom on top of ours
board.addEventListener("pointerdown", e => { if (e.target === board) select(null); });
document.addEventListener("keydown", e => {
  const el = state.selected;
  if (!el || el.isContentEditable || $("#ask").open || !["Delete", "Backspace"].includes(e.key)) return;
  if (el.classList.contains("fixed")) return;
  e.preventDefault();
  remove(ITEMS.find(i => i.id === el.dataset.id));
});

window.addEventListener("resize", () => {
  const was = state.phone;
  state.phone = matchMedia(PHONE).matches;
  if (!state.phone) closeTray();
  renderTray(); layoutBoard();
  if (state.phone !== was) fit();
});
state.phone = matchMedia(PHONE).matches;
renderViews(); renderTray(); layoutBoard(); placeBase(); layoutBoard();
fit();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
