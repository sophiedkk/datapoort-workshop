#!/usr/bin/env python3
"""Offline demo page: out/demo.html, one self-contained file (font, pieces and forms embedded).

Drag the Encounter strip, plates, building blocks, stickers and paper forms from the tray onto the
flipchart to show what participants do. Double-click a plate, strip, blank sticker or text note to
write on it; the x button or the Delete key takes a piece off the sheet.
Run after make_bricks.py (like make_print.py):

    uv run make_demo.py
"""

import base64
import json
import re

from PIL import Image

from make_bricks import DX, FX, OUT_DIR, PH, PW, W, font_file
from make_plates import COMPOSITION, SECTION, concept, ensure_colors
from make_plates import plate as strip_parts
from make_print import CKM_PILE, EXCLUDED, EXERCISE_3, archetype_names, bricks, plate
from make_stickers import CARD_H, CARD_W, CARDINALITY, NAME_H, NAME_W, RENAMES, card_sticker, name_sticker

HERE = OUT_DIR.parent
DEMO = OUT_DIR / "demo.html"
BLOCK_MM = 90
FORMS = [("Nursing Admission Assessment", HERE / "assets" / "nursing-admission.png"),
         ("Additional information on admission", HERE / "assets" / "additional-info.png")]
FORM_DPI = 150                              # the form images are rendered at 150 dpi (see ../README.md)


def inline(svg):
    """Root <svg> without fixed width/height, so CSS sizes it."""
    return re.sub(r'<svg([^>]*?) width="[^"]+" height="[^"]+"', r"<svg\1", svg, count=1)


def mm_svg(parts, w, h, pad=0.5):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w + 2 * pad} {h + 2 * pad}" '
            f'font-family="Lexend, sans-serif">' + "".join(parts) + "</svg>")


def plate_write_ins():
    """Where a plate's 'name in template' and cardinality lines are, as fractions of the plate."""
    fy, fh = 190, 410
    fw = PW - FX - DX - 20
    sx, sy, sw = FX + 30, fy + 26, fw - 60
    line_y = (sy + fh - 52 - 26) / PH
    split = sx + sw - 40 - 560
    return [{"key": "name", "x": (sx + 40) / PW, "y": line_y, "size": 0.032, "bg": True, "prompt": "Name in template"},
            {"key": "card", "x": (split + 280) / PW, "y": line_y, "size": 0.032, "anchor": "middle", "bg": True,
             "prompt": "Cardinality, e.g. 0..1 or 0..*"}]


def strip(aid, kind, h, label, note):
    w = 180
    name = concept(aid)[0]
    color = ensure_colors()[aid]["hex"]
    svg = mm_svg(strip_parts(1, 10, w, h, color, (name, kind), note, label, 12), w + 7.5, h + 11.5, 0)
    vw, vh = w + 7.5, h + 11.5
    write = [{"key": "name", "x": 6.2 / vw, "y": (10 + h - 6.8) / vh, "size": 0.042, "bg": True, "prompt": label.capitalize()}]
    return {"kind": "strip", "w": vw, "svg": svg, "write": write}


def items():
    colors = {aid: c for aid, c in ensure_colors().items() if aid not in EXCLUDED}
    names = archetype_names()
    held_back = set(CKM_PILE) | {EXERCISE_3, COMPOSITION, SECTION}
    table = sorted((aid for aid in colors if aid not in held_back), key=lambda aid: names[aid].lower())
    plate_w = BLOCK_MM * PW / W
    out = []

    def add(tab, group, item):
        out.append({"id": f"i{len(out)}", "tab": tab, "group": group, **item})

    add("Structure", "Encounter (COMPOSITION)",
        strip(COMPOSITION, "Composition", 30, "TEMPLATE NAME", "Stick this at the top of the flipchart sheet"))
    for _ in range(5):
        add("Structure", "Ad hoc headings (SECTION)",
            strip(SECTION, "Section", 22, "SECTION NAME", "A heading: rename it"))
    for aid in table:
        add("Plates", "Archetype plates", {"kind": "plate", "w": plate_w, "svg": inline(plate(aid)),
                                           "write": plate_write_ins()})
    for aid in table:
        for svg in bricks(aid):
            add("Blocks", names[aid], {"kind": "block", "w": BLOCK_MM, "svg": inline(svg)})
    for aid in CKM_PILE:
        add("CKM desk", names[aid], {"kind": "plate", "w": plate_w, "svg": inline(plate(aid)),
                                     "write": plate_write_ins()})
        for svg in bricks(aid):
            add("CKM desk", names[aid], {"kind": "block", "w": BLOCK_MM, "svg": inline(svg)})
    for label, n in CARDINALITY:
        for _ in range(min(n, 3)):
            write = [] if label else [{"key": "text", "x": 0.5, "y": 0.72, "size": 0.22, "anchor": "middle",
                                       "prompt": "Cardinality, e.g. 1..1"}]
            add("Stickers", "Cardinality", {"kind": "sticker", "w": CARD_W + 1,
                                            "svg": mm_svg(card_sticker(0, 0, label if label else ""), CARD_W,
                                                          CARD_H), "write": write})
    for title, path in FORMS:
        mm = Image.open(path).width / FORM_DPI * 25.4
        add("Forms", "Paper forms", {"kind": "form", "w": mm,
                                     "svg": f'<img alt="Paper form: {title}" src="{data_uri(path, "image/png")}">'})
    for label, n in RENAMES:
        for _ in range(min(n, 3)):
            write = [] if label else [{"key": "text", "x": 3.5 / (NAME_W + 1), "y": (NAME_H - 2.5) / (NAME_H + 1),
                                       "size": 0.1, "prompt": "New name"}]
            add("Stickers", "Rename", {"kind": "sticker", "w": NAME_W + 1,
                                       "svg": mm_svg(name_sticker(0, 0, label), NAME_W, NAME_H), "write": write})
    return out


def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    page = (PAGE
            .replace("/*FONT*/", data_uri(font_file("Lexend-VariableFont_wght.ttf"), "font/ttf"))
            .replace("/*ITEMS*/", json.dumps(items()).replace("</", "<\\/")))
    DEMO.write_text(page, encoding="utf-8")
    print(f"-> {DEMO} ({DEMO.stat().st_size / 1e6:.1f} MB)")


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Building blocks demo</title>
<style>
@font-face { font-family: Lexend; src: url("/*FONT*/") format("truetype"); font-weight: 100 900; }
:root { --tray: 340px; --ink: #1B1B1B; --muted: #6b6b6b; --line: #d9d6cf; --bg: #f3f1ec; --paper: #fff; }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body { font-family: Lexend, sans-serif; color: var(--ink); background: var(--bg); display: grid;
       grid-template-columns: var(--tray) 1fr; grid-template-rows: 100vh; overflow: hidden; }
#side { display: flex; flex-direction: column; min-height: 0; height: 100vh; border-right: 1px solid var(--line);
        background: var(--paper); }
.show { padding: 14px 16px; border-bottom: 1px solid var(--line); }
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
label { font-size: 14px; font-weight: 600; color: var(--muted); display: flex; gap: 8px; align-items: center; }
.spacer { flex: 1; }
#tray { flex: 1; overflow-y: auto; padding: 4px 16px 40px; }
#tray h2 { font-size: 13px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
           margin: 18px 0 8px; }
#tray .piece { position: relative; width: 100%; margin-bottom: 10px; }
#tray .piece.sticker { display: inline-block; width: auto; margin-right: 8px; }
#tray .empty { color: var(--muted); font-size: 14px; }
#wrap { overflow: hidden; position: relative; }
#board { position: relative; margin: 24px; background: var(--paper); border: 1px solid var(--line);
         box-shadow: 0 2px 10px rgba(0,0,0,.06); }
#board::before { content: "Flipchart sheet: the template"; position: absolute; left: 16px; top: 10px;
                 font-size: 13px; font-weight: 600; color: #b3aea4; }
.piece { touch-action: none; user-select: none; cursor: grab; }
.piece svg { display: block; width: 100%; height: auto; pointer-events: none; }
#board .piece { position: absolute; filter: drop-shadow(0 2px 3px rgba(0,0,0,.15)); }
.piece.dragging { cursor: grabbing; filter: drop-shadow(0 8px 14px rgba(0,0,0,.25)); z-index: 100000 !important; }
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
.del { display: none; position: absolute; top: -12px; right: -12px; width: 26px; height: 26px; padding: 0;
       border-radius: 50%; font-size: 16px; line-height: 1; background: var(--ink); color: #fff; border: 2px solid #fff;
       z-index: 2; font-family: Lexend, sans-serif; }
#board .piece:hover > .del, #board .piece.selected > .del { display: block; }
.piece.note > .del { right: -34px; top: -6px; }
.grip { display: none; position: absolute; right: -8px; bottom: -8px; width: 18px; height: 18px; border-radius: 4px;
        background: #fff; border: 2px solid var(--ink); cursor: nwse-resize; z-index: 2; }
#board .piece:hover > .grip, #board .piece.selected > .grip { display: block; }
#board .piece.selected { outline: 2px dashed #1d3f8f; outline-offset: 3px; }
@media (max-width: 700px) { body { --tray: 200px; } }
</style>
</head>
<body>
<aside id="side">
  <div class="show">
    <label for="view">Show</label>
    <select id="view"></select>
  </div>
  <div id="tray" aria-label="Pieces"></div>
</aside>
<div id="wrap">
  <div id="board"></div>
  <div id="tools" role="toolbar" aria-label="Sheet tools">
    <div class="size">Size <button id="smaller" aria-label="Smaller pieces">−</button>
      <button id="bigger" aria-label="Bigger pieces">+</button></div>
    <div class="sep"></div>
    <button id="addText">Text</button>
    <button id="reset">Clear</button>
  </div>
</div>
<script>
const ITEMS = /*ITEMS*/;
const viewOf = i => i.tab === "Blocks" ? "Blocks|" + i.group : i.tab;
const VIEWS = [                               // the tray's "Show" menu, in workshop order
  ["Exercise 0: choose the archetypes", [["Structure", "Encounter and headings"], ["Plates", "Archetype plates"],
                                         ["CKM desk", "CKM desk"]]],
  ["Exercise 1: choose the elements",
   [...new Set(ITEMS.filter(i => i.tab === "Blocks").map(i => i.group))].map(g => ["Blocks|" + g, "Building blocks: " + g])
     .concat([["Stickers", "Template stickers"]])],
  ["Reference", [["Forms", "Paper forms"]]],
];
const state = { view: "Structure", scale: 4, placed: new Map(), z: 1, selected: null, notes: 0 };
const NOTE_MM = 7;                            // text note font size, mm on the sheet
const $ = s => document.querySelector(s);
const tray = $("#tray"), board = $("#board"), wrap = $("#wrap");

function piece(item) {
  const el = document.createElement("div");
  el.className = "piece " + item.kind;
  el.dataset.id = item.id;
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

function layoutBoard() {
  const s = state.scale;                      // px per mm of the printed pieces; the sheet fills the window
  board.style.width = wrap.clientWidth - 48 + "px";
  board.style.height = wrap.clientHeight - 48 + "px";
  state.placed.forEach((pos, id) => {         // positions in px on the sheet
    const el = pieces.get(id), item = ITEMS.find(i => i.id === id);
    el.style.left = pos.x + "px";
    el.style.top = pos.y + "px";
    el.style.zIndex = item.kind === "form" ? pos.z : 100000 + pos.z;   // forms stay underneath
    const k = pos.k || 1;                     // the piece's own size, set with its resize handle
    if (item.kind === "note") el.style.fontSize = NOTE_MM * s * k + "px";
    else { el.style.width = item.w * s * k + "px"; sizeInk(el, item, item.w * s * k); }
  });
}

function select(el) {
  if (state.selected) state.selected.classList.remove("selected");
  state.selected = el;
  if (el) el.classList.add("selected");
}

function remove(item) {
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
  const w = wrap.getBoundingClientRect(), b = board.getBoundingClientRect();
  state.placed.set(item.id, { x: w.left + w.width / 2 - b.left - 60, y: w.top + w.height / 2 - b.top,
                              z: ++state.z });
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
  const move = ev => { pos.k = Math.max(0.3, Math.min(5, startK * (startW + ev.clientX - x0) / startW)); layoutBoard(); };
  grip.addEventListener("pointermove", move);
  grip.addEventListener("pointerup", () => grip.removeEventListener("pointermove", move), { once: true });
}

function startDrag(e, el, item) {
  if (e.button !== 0 || el.isContentEditable) return;
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
  const pos = state.placed.get(item.id);
  pos.z = ++state.z;
  select(el);
  el.classList.add("dragging");
  el.setPointerCapture(e.pointerId);
  const move = ev => {
    const b = board.getBoundingClientRect();
    const w = el.offsetWidth || item.w * s, h = el.offsetHeight || w * 0.6;
    pos.x = Math.min(Math.max(ev.clientX - b.left - grab.x * w, -w / 2), b.width - w / 2);
    pos.y = Math.min(Math.max(ev.clientY - b.top - grab.y * h, -h / 2), b.height - h / 2);
    layoutBoard();
  };
  const up = ev => {
    el.classList.remove("dragging");
    el.removeEventListener("pointermove", move);
    el.removeEventListener("pointerup", up);
    const t = $("#side").getBoundingClientRect();
    if (ev.clientX < t.right && ev.clientX >= t.left) remove(item);   // dropped back on the tray
  };
  el.addEventListener("pointermove", move);
  el.addEventListener("pointerup", up);
  move(e);
}

function write(el, item) {
  (item.write || []).forEach(w => {
    const t = el.querySelector(`.ink[data-key="${w.key}"]`);
    const v = prompt(w.prompt, t.textContent);
    if (v !== null) t.textContent = v;
  });
}

const resize = d => { state.scale = Math.min(6, Math.max(1.5, state.scale + d)); layoutBoard(); };
$("#smaller").onclick = () => resize(-0.5);
$("#bigger").onclick = () => resize(0.5);
$("#reset").onclick = () => {
  if (!confirm("Put every piece back on the tray and delete the text notes?")) return;
  ITEMS.filter(i => i.kind === "note").forEach(remove);
  state.placed.clear();
  select(null);
  pieces.forEach(el => el.querySelectorAll(".ink").forEach(t => t.textContent = ""));
  renderTray(); layoutBoard();
};
$("#addText").onclick = addNote;
board.addEventListener("pointerdown", e => { if (e.target === board) select(null); });
document.addEventListener("keydown", e => {
  const el = state.selected;
  if (!el || el.isContentEditable || !["Delete", "Backspace"].includes(e.key)) return;
  e.preventDefault();
  remove(ITEMS.find(i => i.id === el.dataset.id));
});

window.addEventListener("resize", () => { renderTray(); layoutBoard(); });
renderViews(); renderTray(); layoutBoard();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
