"""The roadmap board page: one self-contained file, no network, no build step.

The model is embedded as JSON with every ``<`` and ``>`` escaped; every piece of item
text and every comment reaches the page through ``textContent``. Colours are CSS
custom properties with a dark variant.
"""
from __future__ import annotations

import json
from pathlib import Path


def embed(model: dict) -> str:
    """The model as JSON that is safe inside a ``<script>`` element: no ``<`` or ``>``
    at all, so neither ``</script>`` nor ``<!--<script>`` can end or swallow the block."""
    return (json.dumps(model, ensure_ascii=True, sort_keys=True)
            .replace("<", "\\u003c").replace(">", "\\u003e"))


def render_board(model: dict) -> str:
    model = dict(model)
    if model.get("root"):
        model["rootUri"] = Path(str(model["root"])).as_uri() + "/"
    return (_TEMPLATE.replace("__TITLE__", _text(model.get("project") or "Roadmap"))
            .replace("__BOARD_JSON__", embed(model)))


def _text(value: str) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="virtuoso generate_board">
<title>__TITLE__ — Roadmap board</title>
<style>
:root {
  color-scheme: light;
  --page: #f6f7fb; --panel: #ffffff; --ink: #1f2430; --muted: #676f80; --line: #dfe3ec;
  --head: #f1f3f8; --accent: #0073ea; --focus: #0060c0; --warn: #b45309; --hover: #f3f6fd;
  --s-queued: #2f80ed; --s-in-flight: #e2a400; --s-blocked: #8e44ad; --s-completed: #22a565;
  --s-retired: #8a93a3; --s-unknown: #8a93a3;
  --r-amber: #e2a400; --r-blue: #2f80ed; --r-red: #e2445c; --r-green: #22a565; --r-grey: #8a93a3;
  --w-full: #2f80ed; --w-stub: #8e44ad;
  --p0: #0f7b8a; --p1: #c2410c; --p2: #2f80ed; --p3: #8e44ad; --p4: #22a565;
  --p5: #b5306a; --p6: #5b6bd6; --p7: #8a6d00; --p8: #4a7c3a; --p9: #6d4c41;
  --chip-ink: #ffffff; --shadow: rgba(0, 0, 0, .15); --tint: rgba(0, 115, 234, .08);
  --over: #fde8e8; --over-ink: #b42318; --resolved: #8a93a3; --track: #e9ecf3;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #14161c; --panel: #1c1f27; --ink: #e6e8ee; --muted: #9aa2b2; --line: #2e3340;
    --head: #232733; --accent: #4c9dff; --focus: #7ab4ff; --warn: #f0a24a; --hover: #252a36;
    --over: #4a1f1f; --over-ink: #ffb4ab; --track: #2a2f3b; --shadow: rgba(0, 0, 0, .5);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #14161c; --panel: #1c1f27; --ink: #e6e8ee; --muted: #9aa2b2; --line: #2e3340;
  --head: #232733; --accent: #4c9dff; --focus: #7ab4ff; --warn: #f0a24a; --hover: #252a36;
  --over: #4a1f1f; --over-ink: #ffb4ab; --track: #2a2f3b; --shadow: rgba(0, 0, 0, .5);
}
* { box-sizing: border-box; }
html, body { overflow-x: hidden; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
header.top { padding: 16px 16px 8px; background: var(--panel); border-bottom: 1px solid var(--line); }
header.top h1 { margin: 0 0 4px; font-size: 22px; }
.meta { color: var(--muted); font-size: 13px; display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: center; }
.meta span { overflow-wrap: anywhere; }
.badge { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px;
  background: var(--warn); color: var(--chip-ink); }
.mark { display: inline-block; margin-left: 6px; padding: 0 6px; border-radius: 8px; font-size: 11px;
  font-weight: 500; border: 1px solid var(--warn); color: var(--warn); }
nav.tabs { display: flex; gap: 4px; padding: 8px 16px 0; background: var(--panel);
  border-bottom: 1px solid var(--line); overflow-x: auto; }
nav.tabs button { border: 0; background: none; color: var(--muted); padding: 8px 12px;
  font: inherit; cursor: pointer; border-bottom: 3px solid transparent; }
nav.tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); font-weight: 600; }
main { padding: 12px 16px 48px; }
section[hidden] { display: none; }
button, select, input, textarea { font: inherit; color: var(--ink); }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 0 0 12px; }
.toolbar input, .toolbar select, .tool {
  border: 1px solid var(--line); background: var(--panel); border-radius: 6px; padding: 6px 10px; }
.tool { cursor: pointer; }
.tool[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }
.tool:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--focus); outline-offset: 1px; }
.menu { position: relative; }
.menu .panel { position: absolute; z-index: 20; top: 100%; left: 0; margin-top: 4px; background: var(--panel);
  border: 1px solid var(--line); border-radius: 8px; padding: 8px; min-width: 200px; max-height: 320px;
  overflow: auto; box-shadow: 0 6px 24px var(--shadow); }
.menu .panel[hidden] { display: none; }
.menu .panel label { display: block; padding: 2px 0; white-space: nowrap; }
.group { margin: 0 0 20px; }
.group-title { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; font-size: 16px; font-weight: 600;
  position: sticky; top: 0; z-index: 4; background: var(--page); padding: 4px 0; }
.group-title button { border: 0; background: none; cursor: pointer; padding: 0 4px; color: inherit; font-size: 14px; }
.group-title .count { color: var(--muted); font-weight: 400; font-size: 13px; }
.frame { overflow-x: auto; max-width: 100%; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); }
table.board { border-collapse: separate; border-spacing: 0; min-width: 100%; }
table.board th, table.board td { border-bottom: 1px solid var(--line); border-right: 1px solid var(--line);
  padding: 0 10px; height: 36px; text-align: left; white-space: nowrap; max-width: 280px;
  overflow: hidden; text-overflow: ellipsis; vertical-align: middle; }
table.board thead th { background: var(--head); color: var(--muted); font-weight: 500; font-size: 12px; }
table.board tbody tr:hover td { background: var(--hover); }
table.board td { background: var(--panel); }
.sel { width: 34px; padding: 0 8px !important; border-left: 6px solid var(--rail); }
.item { position: sticky; left: 0; z-index: 1; min-width: 220px; max-width: 360px !important; font-weight: 500; }
thead .item { z-index: 3; }
.actions { width: 84px; text-align: center !important; }
.actions button { border: 0; background: none; cursor: pointer; padding: 2px 4px; color: var(--muted); }
.actions button:hover { color: var(--accent); }
.actions .copied { color: var(--r-green); font-size: 12px; }
.actions .count { font-size: 11px; vertical-align: super; color: var(--accent); }
td.k-number, th.k-number { text-align: right; font-variant-numeric: tabular-nums; }
td.k-mono { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
td.k-label { color: var(--chip-ink); text-align: center; font-weight: 500; padding: 0 6px; }
td.over { background: var(--over) !important; color: var(--over-ink); font-weight: 600; }
.chip { display: inline-block; border: 1px solid var(--muted); border-radius: 12px; padding: 0 8px; font-size: 12px; }
.warn { color: var(--warn); margin-left: 6px; }
td a, .link { color: var(--accent); text-decoration: none; }
td a:hover { text-decoration: underline; }
tr.target td { background: var(--hover); box-shadow: inset 0 0 0 9999px var(--tint); }
tr.comment-row td { white-space: normal; height: auto; padding: 8px 10px; max-width: none; background: var(--head); }
.notes { margin: 0 0 6px; padding: 0; list-style: none; max-width: 720px; }
.notes li { margin: 0 0 4px; white-space: pre-wrap; }
.notes li.resolved { color: var(--resolved); text-decoration: line-through; }
.notes .when { color: var(--muted); font-size: 11px; margin-right: 6px; }
.notes .answer { display: block; color: var(--muted); font-size: 12px; text-decoration: none; }
.comment-row textarea { width: 100%; max-width: 720px; min-height: 56px; border: 1px solid var(--line);
  border-radius: 6px; padding: 6px; background: var(--panel); }
tfoot td { background: var(--panel); height: 30px; }
.battery { display: flex; height: 18px; border-radius: 3px; overflow: hidden; min-width: 80px; }
.battery span { display: block; height: 100%; }
.empty { color: var(--muted); font-style: italic; padding: 12px 0; }
.note { color: var(--muted); font-size: 13px; }
.problems { color: var(--warn); font-size: 13px; margin: 0 0 12px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin: 0 0 16px; }
.tile { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-width: 0; }
.tile span { display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .02em; }
.tile strong { display: block; font-size: 24px; margin-top: 4px; overflow-wrap: anywhere; }
.tile small { display: block; color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.slicers { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 0 0 16px; }
.slicer { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px; min-width: 0; }
.slicer h3 { margin: 0 0 6px; font-size: 13px; color: var(--muted); font-weight: 600; }
.slicer button { margin: 0 4px 4px 0; border: 1px solid var(--line); background: var(--panel); border-radius: 14px;
  padding: 2px 10px; cursor: pointer; font-size: 13px; max-width: 100%; overflow: hidden; text-overflow: ellipsis; }
.slicer button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--chip-ink); }
.slicer button .n { color: inherit; opacity: .7; margin-left: 4px; }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px; }
.chart { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-width: 0; }
.chart h3 { margin: 0 0 8px; font-size: 13px; color: var(--muted); font-weight: 600; }
.chart svg { display: block; width: 100%; height: auto; }
.chart svg text { fill: var(--ink); font-size: 11px; }
.chart .track { fill: var(--track); }
.legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 12px; color: var(--muted); margin-top: 6px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: -1px; }
.done-head { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; margin: 0 0 12px; }
.done-head strong { font-size: 18px; }
@media (max-width: 640px) {
  table.board, table.board tbody, table.board tr, table.board td { display: block; width: 100%; }
  table.board thead, table.board tfoot { display: none; }
  table.board tr { border-left: 6px solid var(--rail); border-bottom: 1px solid var(--line); padding: 6px 0; }
  table.board td { border: 0; height: auto; padding: 2px 10px; white-space: normal; max-width: none; position: static; }
  table.board td.sel, table.board td:empty { display: none; }
  table.board td[data-label]::before { content: attr(data-label) ": "; color: var(--muted); font-size: 12px; }
  table.board td.k-label { display: inline-block; width: auto; margin: 2px 4px 2px 10px; border-radius: 4px; }
  table.board td.k-label::before { content: none; }
  .item { max-width: none !important; }
}
</style>
</head>
<body>
<header class="top">
  <h1 id="title"></h1>
  <div class="meta" id="meta"></div>
</header>
<nav class="tabs" role="tablist" aria-label="Board views">
  <button type="button" role="tab" data-tab="dashboard" aria-selected="false">Dashboard</button>
  <button type="button" role="tab" data-tab="roadmap" aria-selected="true">Roadmap</button>
  <button type="button" role="tab" data-tab="completed" aria-selected="false">Completed</button>
</nav>
<main>
  <section id="dashboard" hidden>
    <div class="toolbar"><button type="button" class="tool" id="clear-filters">Clear all</button>
      <span class="note" id="filter-note"></span></div>
    <div class="slicers" id="slicers"></div>
    <div class="tiles" id="tiles"></div>
    <div class="charts" id="charts"></div>
  </section>
  <section id="roadmap">
    <div class="toolbar" id="roadmap-toolbar"></div>
    <div id="roadmap-groups"></div>
  </section>
  <section id="completed" hidden>
    <div class="done-head" id="done-head"></div>
    <div class="toolbar" id="done-toolbar"></div>
    <div class="problems" id="done-problems"></div>
    <div id="done-groups"></div>
  </section>
</main>
<script id="board-data" type="application/json">__BOARD_JSON__</script>
<script>
"use strict";
const BOARD = JSON.parse(document.getElementById("board-data").textContent);
const ROWS = BOARD.rows || [];
const BY_ID = new Map(ROWS.map((r) => [r.id, r]));
// The Roadmap tab's rows, every grouping: the generator's one terminal filter (board.live).
const LIVE = ((BOARD.roadmap && BOARD.roadmap.live) || []).map((id) => BY_ID.get(id)).filter(Boolean);
const DONE = (BOARD.completed && BOARD.completed.rows) || [];
const DONE_BY_ID = new Map(DONE.map((r) => [r.id, r]));
const STORE_PREFIX = "virtuoso-board:" + (BOARD.root || BOARD.project || "") + ":";
const SVG = "http://www.w3.org/2000/svg";  // a namespace name, never fetched

// --- small helpers -----------------------------------------------------------------
function el(tag, attrs, text) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function svg(tag, attrs, text) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs || {})) node.setAttribute(key, String(value));
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function store(key, value) {
  try {
    if (value === undefined) return window.localStorage.getItem(STORE_PREFIX + key);
    if (value === null) window.localStorage.removeItem(STORE_PREFIX + key);
    else window.localStorage.setItem(STORE_PREFIX + key, value);
  } catch (e) { /* storage unavailable: the page still works without it */ }
  return null;
}
function storedKeys(prefix) {
  const out = [];
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith(STORE_PREFIX + prefix)) out.push(key.slice(STORE_PREFIX.length + prefix.length));
    }
  } catch (e) { /* no storage */ }
  return out;
}
function slot(value) {
  let h = 0;
  for (const ch of String(value).toLowerCase()) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return "var(--p" + (h % 10) + ")";
}
function show(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}
function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }
// A register value becomes a link only as a web or file address, or a path under the
// project root; any other scheme (javascript:, data:, ...) is never clickable.
function href(path) {
  const text = String(path || "").trim();
  if (!text) return "";
  if (/^[a-z]:[\\/]/i.test(text)) return "file:///" + encodeURI(text.replace(/\\/g, "/"));
  if (/^[a-z][a-z0-9+.-]*:/i.test(text)) return /^(https?|file|mailto):/i.test(text) ? text : "";
  try { return new URL(text.replace(/\\/g, "/"), BOARD.rootUri || document.baseURI).href; }
  catch (e) { return ""; }
}
function statusColour(status) {
  if (status === "completed") return "var(--s-completed)";
  if (status === "dissolved" || status === "superseded") return "var(--s-retired)";
  return "var(--s-" + (status || "unknown") + ")";
}
function labelColour(key, row, value) {
  if (key === "status") return statusColour(row.status);
  if (key === "result") return statusColour(row.result);
  if (key === "written_status") return row.written === "full-spec" ? "var(--w-full)" : "var(--w-stub)";
  return value ? slot(value) : "transparent";
}

// --- copy --------------------------------------------------------------------------
function copyText(text, button) {
  if (button && button.classList.contains("copied")) return;
  const done = () => {
    if (!button) return;
    const before = button.textContent;
    button.textContent = "Copied";
    button.classList.add("copied");
    setTimeout(() => {
      button.textContent = button.dataset.label || before;
      button.classList.remove("copied");
    }, 1200);
  };
  const fallback = () => {
    const area = el("textarea", { "aria-hidden": "true" });
    area.value = text;
    area.style.position = "fixed"; area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let copied = false;
    try { copied = document.execCommand("copy"); } catch (e) { copied = false; }
    area.remove();
    if (copied) done();
    else if (button) button.title = "Copy failed: select the name and copy it by hand";
  };
  if (navigator.clipboard && window.isSecureContext !== false) {
    navigator.clipboard.writeText(text).then(done, fallback);
  } else {
    fallback();
  }
}

// --- comments: browser storage first, the sidecar file as the durable copy ---------
// mergeEntry and dumpJson mirror comments.merge_entry and comments.dumps in the
// generator; a test runs both on the same data and requires the same result.
function cmpCodePoints(a, b) {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (d) return d;
  }
  return x.length - y.length;
}
// The newer copy (newest `updated`; a tie keeps the durable one) supplies the time; a
// note only the older copy holds is kept; a note resolved in either copy stays resolved.
function mergeEntry(durable, local) {
  if (!local) return durable;
  if (!durable) return local;
  const localNewer = String(local.updated || "") > String(durable.updated || "");
  const newer = localNewer ? local : durable, older = localNewer ? durable : local;
  const twins = new Map((older.notes || []).map((n) => [JSON.stringify([n.at, n.text]), n]));
  const notes = (newer.notes || []).map((n) => {
    const merged = Object.assign({}, n);
    const twin = twins.get(JSON.stringify([n.at, n.text]));
    if (twin && twin.resolved && !n.resolved) {
      merged.resolved = true;
      if ("answer" in twin) merged.answer = twin.answer;
    }
    return merged;
  });
  const seen = new Set(notes.map((n) => JSON.stringify([n.at, n.text])));
  (older.notes || []).forEach((n) => { if (!seen.has(JSON.stringify([n.at, n.text]))) notes.push(Object.assign({}, n)); });
  notes.sort((a, b) => cmpCodePoints(String(a.at || ""), String(b.at || "")));
  return Object.assign({}, newer, { notes: notes });
}
function mergeComments(durable, local) {
  const out = Object.assign({}, durable);
  Object.keys(local).forEach((id) => { out[id] = mergeEntry(out[id], local[id]); });
  return out;
}
// json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False), byte for byte: keys
// in code-point order (an object's own order would put "9" before "10").
function dumpJson(value, depth) {
  const pad = "  ".repeat(depth || 0);
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    return "[\n" + value.map((v) => pad + "  " + dumpJson(v, (depth || 0) + 1)).join(",\n") + "\n" + pad + "]";
  }
  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort(cmpCodePoints);
    if (!keys.length) return "{}";
    return "{\n" + keys.map((k) => pad + "  " + JSON.stringify(k) + ": " + dumpJson(value[k], (depth || 0) + 1)).join(",\n") + "\n" + pad + "}";
  }
  return JSON.stringify(value);
}
const COMMENTS = Object.assign({}, BOARD.comments || {});
storedKeys("c:").forEach((id) => {
  try {
    const local = JSON.parse(store("c:" + id));
    if (local && Array.isArray(local.notes) && typeof local.updated === "string") COMMENTS[id] = mergeEntry(COMMENTS[id], local);
  } catch (e) { /* a damaged local entry is ignored */ }
});
const OPEN_EDITORS = new Set();
function openNotes(id) { return ((COMMENTS[id] || {}).notes || []).filter((n) => !n.resolved); }
function hasComments(id) { return ((COMMENTS[id] || {}).notes || []).length > 0; }
function addComment(id, text) {
  const now = new Date().toISOString().replace(/\.\d+Z$/, "Z");
  const entry = COMMENTS[id] ? JSON.parse(JSON.stringify(COMMENTS[id])) : { notes: [], updated: now };
  entry.notes.push({ at: now, resolved: false, text: text });
  entry.updated = now > entry.updated ? now : entry.updated;
  COMMENTS[id] = entry;
  store("c:" + id, JSON.stringify(entry));
}
function sidecarText(comments) { return dumpJson({ comments: comments || COMMENTS, version: 1 }, 0) + "\n"; }
function exportComments() {
  const blob = new Blob([sidecarText()], { type: "application/json" });
  const link = el("a", { download: (BOARD.commentsFile || "roadmap-board.comments.json").split(/[\\/]/).pop() });
  link.href = URL.createObjectURL(blob);
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}
async function saveComments(button) {
  if (!window.showSaveFilePicker) { exportComments(); return; }
  try {
    const handle = await window.showSaveFilePicker({ suggestedName: (BOARD.commentsFile || "roadmap-board.comments.json").split(/[\\/]/).pop(),
      types: [{ description: "Board comments", accept: { "application/json": [".json"] } }] });
    // Merge with what the file holds now (a teammate's comments, a review's
    // resolutions); an entry this page does not know is kept exactly as it is.
    let onDisk = {};
    const text = await (await handle.getFile()).text();
    if (text.trim()) {
      let parsed = null;
      try { parsed = JSON.parse(text); } catch (e) { parsed = null; }
      if (!parsed || typeof parsed.comments !== "object" || parsed.comments === null) {
        if (button) button.title = "That file is not a board comments file: nothing was written";
        return;
      }
      onDisk = parsed.comments;
    }
    const writable = await handle.createWritable();
    await writable.write(sidecarText(mergeComments(onDisk, COMMENTS)));
    await writable.close();
    if (button) { button.textContent = "Saved"; setTimeout(() => { button.textContent = button.dataset.label; }, 1200); }
  } catch (e) { /* cancelled */ }
}
function commentButton(row) {
  const open = openNotes(row.id);
  const all = (COMMENTS[row.id] || {}).notes || [];
  const button = el("button", { type: "button", "aria-expanded": String(OPEN_EDITORS.has(row.id)),
    "aria-label": "Comments on " + row.id, title: open.length ? open[open.length - 1].text.split("\n")[0] : "Add a comment" }, "💬");
  if (all.length) button.append(el("span", { class: "count" }, String(open.length || all.length)));
  button.addEventListener("click", () => {
    OPEN_EDITORS.has(row.id) ? OPEN_EDITORS.delete(row.id) : OPEN_EDITORS.add(row.id);
    renderAll();
    const box = document.querySelector('textarea[data-item="' + CSS.escape(row.id) + '"]');
    if (box) box.focus();
  });
  return button;
}
function commentRow(row, span) {
  const tr = el("tr", { class: "comment-row" });
  const td = el("td", { colspan: String(span) });
  const list = el("ul", { class: "notes" });
  ((COMMENTS[row.id] || {}).notes || []).forEach((note) => {
    const li = el("li", { class: note.resolved ? "resolved" : "" });
    li.append(el("span", { class: "when" }, note.at), document.createTextNode(note.text));
    if (note.answer) li.append(el("span", { class: "answer" }, "answered: " + note.answer));
    list.append(li);
  });
  const box = el("textarea", { "data-item": row.id, "aria-label": "Comment on " + row.id,
    placeholder: row.terminal ? "A follow-up on finished work (Ctrl+Enter or leave the box to save)" : "Comment for the next review (Ctrl+Enter or leave the box to save)" });
  const save = () => {
    const text = box.value.trim();
    if (!text) return;
    box.value = "";
    addComment(row.id, text);
    renderAll();
  };
  box.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); save(); } });
  box.addEventListener("blur", save);
  td.append(list, box);
  tr.append(td);
  return tr;
}

// --- the shared filter: slicers, cross-filtering, URL-hash state -------------------
const FILTER = { sel: {}, link: true };
function slicerDefs() {
  const defs = (BOARD.dashboard && BOARD.dashboard.slicers) || [];
  const withComments = ROWS.some((r) => hasComments(r.id));
  return withComments ? defs.concat([{ key: "comments", label: "Has comments", values: ["with", "without"],
    labels: { with: "With comments", without: "Without" } }]) : defs;
}
function facet(row, key) {
  if (key === "comments") return hasComments(row.id) ? "with" : "without";
  const value = (row.facets || {})[key];
  return value === undefined || value === null ? "" : String(value);
}
function passes(row, skip) {
  for (const [key, values] of Object.entries(FILTER.sel)) {
    if (key === skip || !values.length) continue;
    if (!values.includes(facet(row, key))) return false;
  }
  return true;
}
function filtering() { return Object.values(FILTER.sel).some((v) => v.length); }
function saveHash() {
  const sel = {};
  Object.entries(FILTER.sel).forEach(([k, v]) => { if (v.length) sel[k] = v; });
  const state = { f: sel };
  if (!FILTER.link) state.u = 1;
  const hash = Object.keys(sel).length || !FILTER.link ? "#" + encodeURIComponent(JSON.stringify(state)) : "";
  history.replaceState(null, "", hash || location.pathname + location.search);
}
function loadHash() {
  if (!location.hash) return;
  try {
    const state = JSON.parse(decodeURIComponent(location.hash.slice(1)));
    // Only slicers and values this page offers: a stale bookmark cannot empty every tab.
    const defs = new Map(slicerDefs().map((d) => [d.key, d.values]));
    Object.entries((state && state.f) || {}).forEach(([k, v]) => {
      if (Array.isArray(v) && defs.has(k)) FILTER.sel[k] = v.map(String).filter((x) => defs.get(k).includes(x));
    });
    FILTER.link = !(state && state.u);
  } catch (e) { /* a hand-edited hash is ignored */ }
}
function toggleSlice(key, value) {
  const values = FILTER.sel[key] || [];
  FILTER.sel[key] = values.includes(value) ? values.filter((v) => v !== value) : values.concat([value]);
  saveHash();
  renderAll();
}

// --- header and tabs -----------------------------------------------------------------
function renderHeader() {
  document.getElementById("title").textContent = (BOARD.project || "Project") + " — Roadmap board";
  const p = BOARD.provenance || {};
  const meta = document.getElementById("meta");
  meta.append(el("span", {}, "snapshot " + (p.takenAt || "unknown")),
              el("span", {}, "provider " + (p.provider || "unknown")),
              el("span", {}, "source " + (p.source || "unknown")),
              el("span", {}, "generated " + (BOARD.generatedAt || "")));
  const taken = Date.parse(p.takenAt || "");
  const hours = isNaN(taken) ? null : (Date.now() - taken) / 3600000;
  if (p.stale) meta.append(el("span", { class: "badge", title: p.staleReason || "" }, "stale snapshot"));
  else if (hours !== null && hours > 24) meta.append(el("span", { class: "badge" }, Math.floor(hours / 24) + "d old"));
  const save = el("button", { type: "button", class: "tool", "data-label": "Save comments",
    title: "Write the comments file (roadmap-board.comments.json) for the next review" }, "Save comments");
  save.addEventListener("click", () => saveComments(save));
  const exp = el("button", { type: "button", class: "tool", title: "Download the comments file to drop into the project root" }, "Export comments");
  exp.addEventListener("click", exportComments);
  meta.append(save, exp);
  const damaged = BOARD.commentProblems || [];
  if (damaged.length) meta.append(el("span", { class: "badge", title: damaged.join("\n") },
    plural(damaged.length, "damaged comment entry") + " skipped — fix the comments file"));
}
function selectTab(name) {
  document.querySelectorAll("[data-tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll("main > section").forEach((s) => { s.hidden = s.id !== name; });
  store("tab", name);
}

// --- board tables (Roadmap and Completed) -----------------------------------------------
const VIEW = { search: "", sort: "", desc: false, groupBy: "pipeline", hidden: new Set(), selected: new Set(), collapsed: new Set() };
const DONE_VIEW = { search: "", from: "", to: "", groupBy: "result" };
const RAILS = { amber: "var(--r-amber)", blue: "var(--r-blue)", red: "var(--r-red)", green: "var(--r-green)", grey: "var(--r-grey)" };

function visibleColumns(columns) { return columns.filter((c) => !VIEW.hidden.has(c.key)); }
function matches(row, search) {
  if (!search) return true;
  const hay = [row.name, ...Object.values(row.values || {}).map(show)].join(" ").toLowerCase();
  return hay.includes(search.toLowerCase());
}
function roadmapFilter(row) { return matches(row, VIEW.search) && (!FILTER.link || passes(row)); }
function doneFilter(row) {
  const day = show(row.values.completedOn).slice(0, 10);
  if (DONE_VIEW.from && (!day || day < DONE_VIEW.from)) return false;
  if (DONE_VIEW.to && (!day || day > DONE_VIEW.to)) return false;
  return matches(row, DONE_VIEW.search) && passes(row);
}
function sortRows(rows) {
  if (!VIEW.sort) return rows;
  const key = VIEW.sort;
  const value = (r) => { const v = r.values[key]; return Array.isArray(v) ? v.join(",") : v; };
  return rows.slice().sort((a, b) => {
    const x = value(a), y = value(b);
    if (x === y) return 0;
    if (x === null || x === undefined || x === "") return 1;
    if (y === null || y === undefined || y === "") return -1;
    const nx = Number(String(x).replace(/,/g, "")), ny = Number(String(y).replace(/,/g, ""));
    const cmp = !isNaN(nx) && !isNaN(ny) ? nx - ny : String(x).localeCompare(String(y));
    return VIEW.desc ? -cmp : cmp;
  });
}
function groupings(columns, rows, first) {
  const out = [first];
  columns.forEach((c) => {
    if (["label", "chip"].includes(c.kind) || c.key.startsWith("extra:")) {
      const values = new Set(rows.map((r) => show(r.values[c.key])));
      if (values.size >= 2 && values.size <= 12 && c.key !== "status" && c.key !== "result") out.push([c.key, c.header]);
    }
  });
  return out;
}
function groupByValue(rows, key) {
  const groups = new Map();
  rows.forEach((r) => {
    const value = key === "month" ? show(r.values.completedOn).slice(0, 7) || "(no date)" : show(r.values[key]) || "(none)";
    if (!groups.has(value)) groups.set(value, { key: value, title: value, rail: slot(value), rows: [] });
    groups.get(value).rows.push(r);
  });
  return [...groups.values()];
}
function liveGroups() {
  if (VIEW.groupBy === "pipeline") {
    return (BOARD.roadmap.groups || []).map((g) => ({ key: g.key, title: g.title, rail: RAILS[g.rail], rows: g.ids.map((id) => BY_ID.get(id)) }));
  }
  return groupByValue(LIVE, VIEW.groupBy);
}
function doneGroups() {
  if (DONE_VIEW.groupBy === "result") {
    return ((BOARD.completed && BOARD.completed.groups) || []).map((g) => ({ key: g.key, title: g.title, rail: RAILS[g.rail], rows: g.ids.map((id) => DONE_BY_ID.get(id)) }));
  }
  return groupByValue(DONE, DONE_VIEW.groupBy);
}

function rowTarget(id) {
  if (DONE_BY_ID.has(id) && !(BY_ID.has(id) && !BY_ID.get(id).terminal)) return "done-";
  return BY_ID.has(id) ? "row-" : "";
}
function refLink(td, id) {
  if (!rowTarget(id)) { td.append(document.createTextNode(id)); return; }
  const a = el("a", { href: "#", class: "link" }, id);
  a.addEventListener("click", (ev) => { ev.preventDefault(); jumpTo(id); });
  td.append(a);
}
function cell(column, row) {
  const value = row.values[column.key];
  const text = show(value);
  const td = el("td", { class: "k-" + column.kind, "data-label": column.kind === "label" ? null : column.header });
  if (column.kind === "label") {
    td.style.background = text ? labelColour(column.key, row, text) : "transparent";
    td.textContent = text;
  } else if (column.kind === "number") {
    // Seq gets a thousands separator, as the reference board shows it; any other
    // number keeps the register's own spelling (a year, a zero-padded ticket).
    const n = Number(String(text).replace(/,/g, ""));
    td.textContent = column.key === "sequence" && text !== "" && !isNaN(n) ? n.toLocaleString("en-US") : text;
  } else if (column.kind === "chip") {
    if (text) td.append(el("span", { class: "chip" }, text));
  } else if (column.kind === "link") {
    const target = href(text);
    if (target) td.append(el("a", { href: target, target: "_blank", rel: "noopener", title: text }, text));
    else td.textContent = text;
  } else if (column.kind === "deps") {
    (Array.isArray(value) ? value : []).forEach((dep, i) => {
      if (i) td.append(document.createTextNode(", "));
      refLink(td, dep);
    });
  } else if (column.kind === "ref") {
    if (text) refLink(td, text);
  } else if (column.kind === "estimate") {
    td.textContent = text;
    if (row.over) { td.classList.add("over"); td.title = "Actual exceeded the estimate"; }
  } else {
    td.textContent = text;
  }
  if (text && !["deps", "estimate"].includes(column.kind)) td.title = text;
  return td;
}
function jumpTo(id) {
  const prefix = rowTarget(id);
  if (!prefix) return;
  selectTab(prefix === "done-" ? "completed" : "roadmap");
  const target = document.getElementById(prefix + id);
  if (!target) return;
  document.querySelectorAll("tr.target").forEach((t) => t.classList.remove("target"));
  target.classList.add("target");
  target.scrollIntoView({ block: "center" });
}
function actionsCell(row) {
  const td = el("td", { class: "actions" });
  td.append(commentButton(row));
  const copy = el("button", { type: "button", title: "Copy name (Shift: with spec and branch)", "aria-label": "Copy " + row.id, "data-label": "⧉" }, "⧉");
  copy.addEventListener("click", (ev) => copyText(ev.shiftKey ? row.copyDispatch : row.copy, copy));
  td.append(copy);
  return td;
}
function itemCell(row) {
  const td = el("td", { class: "item", title: row.name });
  td.append(document.createTextNode(row.name));
  if (row.warn) td.append(el("span", { class: "warn", title: row.warn, "aria-label": row.warn }, "⚠"));
  if (row.unreconciled) td.append(el("span", { class: "mark", title: row.unreconciled }, "unreconciled"));
  const history = (row.history || []).map((v) => v.record + ": " + [v.completed, v.result, v.estimate && "est " + v.estimate, v.actual && "actual " + v.actual].filter(Boolean).join(" · ")).join("\n");
  if (row.corrected) td.append(el("span", { class: "mark", title: history }, "corrected"));
  if (row.earlier) td.append(el("span", { class: "mark", title: history }, "+" + plural(row.earlier, "earlier record")));
  return td;
}
function footer(columns, rows) {
  const tr = el("tr");
  tr.append(el("td", { class: "sel" }), el("td", { class: "item note" }, plural(rows.length, "item")), el("td", { class: "actions" }));
  columns.forEach((c) => {
    const td = el("td", { class: c.kind === "number" ? "k-number" : "" });
    if (c.kind === "label") {
      const counts = new Map();
      rows.forEach((r) => { const v = show(r.values[c.key]); if (v) counts.set(v, (counts.get(v) || 0) + 1); });
      const bar = el("div", { class: "battery" });
      counts.forEach((n, v) => {
        const seg = el("span", { title: v + ": " + n + " (" + Math.round(100 * n / rows.length) + "%)" });
        seg.style.width = (100 * n / rows.length) + "%";
        seg.style.background = labelColour(c.key, rows.find((r) => show(r.values[c.key]) === v), v);
        bar.append(seg);
      });
      td.append(bar);
    } else if (c.kind === "number" && c.key.startsWith("extra:")) {
      const sum = rows.reduce((s, r) => s + (Number(String(r.values[c.key] || "").replace(/,/g, "")) || 0), 0);
      td.textContent = sum.toLocaleString("en-US");
    }
    tr.append(td);
  });
  return tr;
}
function boardTable(columns, rows, rail, idPrefix) {
  const table = el("table", { class: "board" });
  const head = el("tr");
  head.append(el("th", { class: "sel" }), el("th", { class: "item" }, "Item"), el("th", { class: "actions" }, ""));
  columns.forEach((c) => head.append(el("th", { class: c.kind === "number" ? "k-number" : "" }, c.header)));
  table.appendChild(el("thead")).appendChild(head);
  const body = el("tbody");
  rows.forEach((row) => {
    const tr = el("tr", { id: idPrefix + row.id });
    tr.style.setProperty("--rail", rail);
    const sel = el("td", { class: "sel" });
    const box = el("input", { type: "checkbox", "aria-label": "Select " + row.id });
    box.checked = VIEW.selected.has(row.id);
    box.addEventListener("change", () => { box.checked ? VIEW.selected.add(row.id) : VIEW.selected.delete(row.id); updateSelection(); });
    sel.append(box);
    tr.append(sel, itemCell(row), actionsCell(row));
    columns.forEach((c) => tr.append(cell(c, row)));
    body.append(tr);
    if (OPEN_EDITORS.has(row.id)) body.append(commentRow(row, columns.length + 3));
  });
  table.append(body);
  if (rows.length) table.appendChild(el("tfoot")).appendChild(footer(columns, rows));
  return table;
}
function renderGroups(container, groups, columns, idPrefix, filter, empty) {
  container.replaceChildren();
  let shown = 0;
  groups.forEach((g) => {
    const rows = sortRows(g.rows.filter(filter));
    if (!rows.length) return;
    shown += rows.length;
    const box = el("div", { class: "group" });
    const title = el("div", { class: "group-title" });
    title.style.color = g.rail;
    const open = !VIEW.collapsed.has(idPrefix + g.key);
    const toggle = el("button", { type: "button", "aria-expanded": String(open), "aria-label": (open ? "Collapse " : "Expand ") + g.title }, open ? "▾" : "▸");
    toggle.addEventListener("click", () => {
      open ? VIEW.collapsed.add(idPrefix + g.key) : VIEW.collapsed.delete(idPrefix + g.key);
      renderAll();
    });
    title.append(toggle, el("span", {}, g.title), el("span", { class: "count" }, plural(rows.length, "item")));
    box.append(title);
    if (open) box.appendChild(el("div", { class: "frame" })).appendChild(boardTable(columns, rows, g.rail, idPrefix));
    container.append(box);
  });
  if (!shown) container.append(el("p", { class: "empty" }, empty));
}
function updateSelection() {
  const button = document.getElementById("copy-selected");
  if (!button) return;
  button.dataset.label = "Copy selected (" + VIEW.selected.size + ")";
  if (!button.classList.contains("copied")) button.textContent = button.dataset.label;
}
function linkToggle() {
  const button = el("button", { type: "button", class: "tool", id: "link-filter", title: "Apply the Dashboard's slicers to this tab" });
  const paint = () => {
    button.setAttribute("aria-pressed", String(FILTER.link));
    button.textContent = (FILTER.link ? "Filter: linked" : "Filter: unlinked") + (filtering() ? " •" : "");
  };
  button.addEventListener("click", () => { FILTER.link = !FILTER.link; saveHash(); renderAll(); });
  RENDERERS.push(paint);
  return button;
}
function buildToolbar() {
  const bar = document.getElementById("roadmap-toolbar");
  const search = el("input", { type: "search", placeholder: "Search", "aria-label": "Search the board" });
  search.addEventListener("input", () => { VIEW.search = search.value.trim(); renderAll(); });

  const sort = el("select", { "aria-label": "Sort" });
  sort.append(el("option", { value: "" }, "Sort: Seq"));
  (BOARD.columns || []).forEach((c) => sort.append(el("option", { value: c.key }, "Sort: " + c.header)));
  const dir = el("button", { type: "button", class: "tool", "aria-label": "Sort direction" }, "↑");
  sort.addEventListener("change", () => { VIEW.sort = sort.value; renderAll(); });
  dir.addEventListener("click", () => { VIEW.desc = !VIEW.desc; dir.textContent = VIEW.desc ? "↓" : "↑"; renderAll(); });

  const hide = el("div", { class: "menu" });
  const hideButton = el("button", { type: "button", class: "tool", "aria-haspopup": "true" }, "Hide");
  const panel = el("div", { class: "panel" });
  panel.hidden = true;
  (BOARD.columns || []).forEach((c) => {
    const box = el("input", { type: "checkbox" });
    box.checked = !VIEW.hidden.has(c.key);
    box.addEventListener("change", () => {
      box.checked ? VIEW.hidden.delete(c.key) : VIEW.hidden.add(c.key);
      store("hidden", JSON.stringify([...VIEW.hidden]));
      renderAll();
    });
    const label = el("label");
    label.append(box, document.createTextNode(" " + c.header));
    panel.append(label);
  });
  hideButton.addEventListener("click", () => { panel.hidden = !panel.hidden; });
  hide.append(hideButton, panel);

  const groupBy = el("select", { "aria-label": "Group by" });
  groupings(BOARD.columns || [], LIVE, ["pipeline", "Pipeline state"])
    .forEach(([key, label]) => groupBy.append(el("option", { value: key }, "Group by: " + label)));
  groupBy.addEventListener("change", () => { VIEW.groupBy = groupBy.value; renderAll(); });

  const copySelected = el("button", { type: "button", class: "tool", id: "copy-selected", "data-label": "Copy selected (0)" }, "Copy selected (0)");
  copySelected.addEventListener("click", () => {
    const names = ROWS.concat(DONE).filter((r, i, all) => VIEW.selected.has(r.id) && all.findIndex((x) => x.id === r.id) === i).map((r) => r.copy);
    if (names.length) copyText(names.join("\n"), copySelected);
  });
  bar.append(search, linkToggle(), sort, dir, hide, groupBy, copySelected);
}
function renderRoadmap() {
  renderGroups(document.getElementById("roadmap-groups"), liveGroups(),
               visibleColumns(BOARD.columns || []), "row-", roadmapFilter, "No live work matches.");
}

// --- the Completed tab ---------------------------------------------------------------
// Dates are hand-typed in many registers: only an ISO day (YYYY-MM-DD) is counted, and a
// date that is not one is skipped, never fatal.
function weekStart(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const d = new Date(day + "T00:00:00Z");
  if (isNaN(d)) return null;
  d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
  return d.toISOString().slice(0, 10);
}
function weeklyCounts(rows, weeks) {
  const days = rows.map((r) => show(r.values.completedOn).slice(0, 10)).filter((d) => weekStart(d));
  const last = weekStart(new Date().toISOString().slice(0, 10));
  const out = [];
  for (let i = weeks - 1; i >= 0; i--) {
    const d = new Date(last + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() - 7 * i);
    out.push({ week: d.toISOString().slice(0, 10), n: 0 });
  }
  days.forEach((day) => { const w = weekStart(day); const hit = out.find((o) => o.week === w); if (hit) hit.n += 1; });
  return out;
}
function sparkline(points, width, height) {
  const max = Math.max(1, ...points.map((p) => p.n));
  const box = svg("svg", { viewBox: "0 0 " + width + " " + height, width: width, height: height, role: "img",
    "aria-label": "Completions per week" });
  const step = points.length > 1 ? width / (points.length - 1) : width;
  const path = points.map((p, i) => (i ? "L" : "M") + (i * step).toFixed(1) + " " + (height - 2 - (height - 4) * p.n / max).toFixed(1)).join(" ");
  box.append(svg("path", { d: path, fill: "none", stroke: "var(--accent)", "stroke-width": 2 }));
  box.append(svg("title", {}, points.map((p) => p.week + ": " + p.n).join("\n")));
  return box;
}
function buildDoneToolbar() {
  const bar = document.getElementById("done-toolbar");
  const search = el("input", { type: "search", placeholder: "Search", "aria-label": "Search completed work" });
  search.addEventListener("input", () => { DONE_VIEW.search = search.value.trim(); renderAll(); });
  const from = el("input", { type: "date", "aria-label": "Completed from" });
  const to = el("input", { type: "date", "aria-label": "Completed to" });
  from.addEventListener("change", () => { DONE_VIEW.from = from.value; renderAll(); });
  to.addEventListener("change", () => { DONE_VIEW.to = to.value; renderAll(); });
  const groupBy = el("select", { "aria-label": "Group by" });
  const columns = (BOARD.completed && BOARD.completed.columns) || [];
  groupings(columns, DONE, ["result", "Completed / Retired"]).concat([["month", "Completion month"]])
    .forEach(([key, label]) => groupBy.append(el("option", { value: key }, "Group by: " + label)));
  groupBy.addEventListener("change", () => { DONE_VIEW.groupBy = groupBy.value; renderAll(); });
  bar.append(search, el("span", { class: "note" }, "from"), from, el("span", { class: "note" }, "to"), to, groupBy);
  const problems = (BOARD.completed && BOARD.completed.problems) || [];
  const box = document.getElementById("done-problems");
  problems.forEach((p) => box.append(el("div", {}, "⚠ " + p)));
}
function renderCompleted() {
  const rows = DONE.filter(doneFilter);
  const head = document.getElementById("done-head");
  head.replaceChildren();
  const retired = rows.filter((r) => r.retired).length;
  head.append(el("strong", {}, plural(rows.length - retired, "item") + " completed"),
              el("span", { class: "note" }, retired + " retired"),
              sparkline(weeklyCounts(rows, 12), 160, 32),
              el("span", { class: "note" }, "per week, last 12 weeks"));
  renderGroups(document.getElementById("done-groups"), doneGroups(),
               (BOARD.completed && BOARD.completed.columns) || [], "done-", doneFilter, "No completed or retired work matches.");
}

// --- the Dashboard -------------------------------------------------------------------
function renderSlicers() {
  const box = document.getElementById("slicers");
  box.replaceChildren();
  slicerDefs().forEach((def) => {
    const card = el("div", { class: "slicer" });
    card.append(el("h3", {}, def.label));
    const chosen = FILTER.sel[def.key] || [];
    def.values.forEach((value) => {
      const n = ROWS.filter((r) => passes(r, def.key) && facet(r, def.key) === value).length;
      const button = el("button", { type: "button", "aria-pressed": String(chosen.includes(value)), "data-slicer": def.key, "data-value": value });
      button.append(document.createTextNode((def.labels && def.labels[value]) || value), el("span", { class: "n" }, String(n)));
      button.addEventListener("click", () => toggleSlice(def.key, value));
      card.append(button);
    });
    box.append(card);
  });
  document.getElementById("filter-note").textContent = filtering()
    ? ROWS.filter((r) => passes(r)).length + " of " + ROWS.length + " items match" + (FILTER.link ? "; the Roadmap tab is linked" : "")
    : "";
}
function renderTiles(rows) {
  const box = document.getElementById("tiles");
  box.replaceChildren();
  const recount = {
    total: rows.length,
    complete: rows.filter((r) => r.terminal).length,
    incomplete: rows.filter((r) => !r.terminal).length,
    blocked: rows.filter((r) => r.status === "blocked").length,
  };
  recount.percent = rows.length ? Math.round(1000 * recount.complete / rows.length) / 10 : null;
  ((BOARD.dashboard && BOARD.dashboard.tiles) || []).forEach((t) => {
    const filtered = filtering() && t.key in recount;
    const value = filtered ? recount[t.key] : t.value;
    const tile = el("div", { class: "tile", title: t.source + (t.missing ? "\nnot computable: " + t.missing.join("; ") : ""), "data-tile": t.key });
    tile.append(el("span", {}, t.label),
                el("strong", {}, value === null || value === undefined ? "not computable" : (t.key === "percent" ? value + "%" : String(value))));
    const detail = filtered ? "of the filtered items" : (filtering() && !(t.key in recount) ? "whole register" : t.detail);
    if (detail) tile.append(el("small", {}, detail));
    box.append(tile);
  });
}
function stackedByLane(rows) {
  const lanes = [...new Set(rows.map((r) => facet(r, "lane") || "(none)"))];
  const statuses = ["in-flight", "queued", "blocked", "unknown", "completed", "dissolved", "superseded"].filter((s) => rows.some((r) => r.status === s));
  const width = 320, bar = 18, gap = 8, labelW = 90;
  const height = Math.max(bar, lanes.length * (bar + gap));
  const box = svg("svg", { viewBox: "0 0 " + width + " " + height, role: "img", "aria-label": "Status by lane" });
  const max = Math.max(1, ...lanes.map((l) => rows.filter((r) => (facet(r, "lane") || "(none)") === l).length));
  lanes.forEach((lane, i) => {
    const y = i * (bar + gap);
    box.append(svg("text", { x: 0, y: y + 13 }, lane.length > 14 ? lane.slice(0, 13) + "…" : lane));
    let x = labelW;
    statuses.forEach((s) => {
      const n = rows.filter((r) => (facet(r, "lane") || "(none)") === lane && r.status === s).length;
      if (!n) return;
      const w = (width - labelW) * n / max;
      const rect = svg("rect", { x: x, y: y, width: Math.max(w, 1), height: bar, fill: statusColour(s) });
      rect.append(svg("title", {}, lane + " · " + s + ": " + n));
      box.append(rect);
      x += w;
    });
  });
  const legend = el("div", { class: "legend" });
  statuses.forEach((s) => { const i = el("i"); i.style.background = statusColour(s); const span = el("span"); span.append(i, document.createTextNode(s)); legend.append(span); });
  return [box, legend];
}
function progressByGroup(rows) {
  const groups = [...new Set(rows.map((r) => facet(r, "group") || "(none)"))];
  const width = 320, bar = 14, gap = 10, labelW = 90;
  const box = svg("svg", { viewBox: "0 0 " + width + " " + Math.max(bar, groups.length * (bar + gap)), role: "img", "aria-label": "Completion by group" });
  groups.forEach((g, i) => {
    const mine = rows.filter((r) => (facet(r, "group") || "(none)") === g);
    const done = mine.filter((r) => r.terminal).length;
    const y = i * (bar + gap);
    box.append(svg("text", { x: 0, y: y + 11 }, g.length > 14 ? g.slice(0, 13) + "…" : g));
    box.append(svg("rect", { class: "track", x: labelW, y: y, width: width - labelW - 40, height: bar, rx: 3 }));
    const fill = svg("rect", { x: labelW, y: y, width: (width - labelW - 40) * done / mine.length, height: bar, rx: 3, fill: "var(--r-green)" });
    fill.append(svg("title", {}, g + ": " + done + " of " + mine.length + " complete"));
    box.append(fill);
    box.append(svg("text", { x: width - 34, y: y + 11 }, Math.round(100 * done / mine.length) + "%"));
  });
  return [box];
}
function completionsOverTime() {
  const points = weeklyCounts(DONE.filter((r) => passes(r)), 12);
  const width = 320, height = 120, max = Math.max(1, ...points.map((p) => p.n));
  const box = svg("svg", { viewBox: "0 0 " + width + " " + (height + 16), role: "img", "aria-label": "Completions per week" });
  const step = width / points.length;
  points.forEach((p, i) => {
    const h = (height - 4) * p.n / max;
    const rect = svg("rect", { x: i * step + 2, y: height - h, width: step - 4, height: Math.max(h, 0), fill: "var(--accent)" });
    rect.append(svg("title", {}, "week of " + p.week + ": " + p.n));
    box.append(rect);
  });
  box.append(svg("text", { x: 0, y: height + 13 }, points[0].week), svg("text", { x: width - 62, y: height + 13 }, points[points.length - 1].week));
  return [box];
}
function chart(title, parts) {
  const card = el("div", { class: "chart" });
  card.append(el("h3", {}, title), ...parts);
  return card;
}
function renderDashboard() {
  renderSlicers();
  const rows = ROWS.filter((r) => passes(r));
  renderTiles(rows);
  const charts = document.getElementById("charts");
  charts.replaceChildren(
    chart("Status by lane", stackedByLane(rows)),
    chart("Completion by group", progressByGroup(rows)),
    chart("Completions per week (last 12)", completionsOverTime()));
}

// --- wiring -------------------------------------------------------------------------
const RENDERERS = [];
function renderAll() { RENDERERS.forEach((render) => render()); }
function boot() {
  try { JSON.parse(store("hidden") || "[]").forEach((k) => VIEW.hidden.add(k)); } catch (e) { /* ignore */ }
  loadHash();
  renderHeader();
  RENDERERS.push(renderRoadmap, renderCompleted, renderDashboard);
  buildToolbar();
  buildDoneToolbar();
  document.getElementById("clear-filters").addEventListener("click", () => { FILTER.sel = {}; saveHash(); renderAll(); });
  document.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => selectTab(b.dataset.tab)));
  renderAll();
  const tab = store("tab");
  if (tab && document.getElementById(tab)) selectTab(tab);
}
boot();
</script>
</body>
</html>
"""
