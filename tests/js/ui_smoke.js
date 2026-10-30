// Drives the demo UI (docs/index.html + docs/app.js) against a tiny fake DOM,
// because the test suite has no browser and no npm dependencies. It checks that
// the page boots on the first sample, reacts to edits, shows validation errors,
// switches scenarios and loads every sample without throwing.
// Prints a JSON summary for tests/test_demo.py.
"use strict";
const fs = require("fs");
const path = require("path");
const docs = path.join(__dirname, "..", "..", "docs");
const html = fs.readFileSync(path.join(docs, "index.html"), "utf8");

const byId = {};
class El {
  constructor(tag) {
    this.tagName = tag.toLowerCase(); this.children = []; this.attrs = {}; this.listeners = {};
    this._text = ""; this.hidden = false; this.value = ""; this.checked = false; this.className = "";
    this.parentNode = null;
  }
  appendChild(c) { this.children.push(c); c.parentNode = this; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === "id") byId[v] = this; }
  getAttribute(k) { return this.attrs[k]; }
  removeAttribute(k) { delete this.attrs[k]; }
  querySelectorAll(tag) { return this.descendants().filter((d) => d.tagName === tag); }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  dispatch(t) { (this.listeners[t] || []).forEach((f) => f({ target: this })); }
  click() { this.dispatch("click"); }
  focus() { document.activeElement = this; }
  remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((c) => c !== this); }
  set textContent(v) { this.children = []; this._text = String(v); }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); }
  descendants() { return this.children.flatMap((c) => [c].concat(c.descendants())); }
  querySelector(tag) { return this.descendants().find((d) => d.tagName === tag) || null; }
}
// one fake element per id in the real page, so missing ids fail loudly
for (const m of html.matchAll(/<(\w+)[^>]*\sid="([^"]+)"/g)) {
  const e = new El(m[1]); e.setAttribute("id", m[2]);
  if (/\shidden[\s>]/.test(m[0])) e.hidden = true;
}
const document = {
  readyState: "complete",
  activeElement: null,
  body: new El("body"),
  getElementById(id) { if (!byId[id]) throw new Error("no element #" + id); return byId[id]; },
  createElement: (t) => new El(t),
  createElementNS: (ns, t) => new El(t),
  querySelectorAll(sel) {
    const m = sel.match(/^#([\w-]+) (\w+)$/);
    return byId[m[1]].descendants().filter((d) => d.tagName === m[2]);
  },
  addEventListener() {},
};
global.document = document;
global.window = global;
global.STARTUP_SAMPLES = JSON.parse(
  fs.readFileSync(path.join(docs, "samples.js"), "utf8").replace(/^[\s\S]*?window\.STARTUP_SAMPLES = /, "").replace(/;\s*$/, "")
);
require(path.join(docs, "app.js"));

const $ = (id) => document.getElementById(id);
const text = (id) => $(id).textContent;
const out = { steps: [] };
function snap(name) {
  out.steps.push({
    name,
    problemsHidden: $("problems").hidden,
    problems: text("problems"),
    resultsHidden: $("results").hidden,
    totals: text("totals"),
    runway: text("runway-msg"),
    breakEven: text("be-msg"),
    compareRows: $("compare-rows").children.length,
    winners: $("winners").children.map((c) => c.textContent),
    scenarioOptions: $("scenario-switcher").children.length,
    burnChart: $("burn-chart").descendants().filter((d) => d.tagName === "path").length,
    beChart: $("be-chart").descendants().filter((d) => d.tagName === "path").length,
    oneTimeRows: $("one-time-rows").children.length,
    label: text("sample-label"),
    invalidCash: $("starting-cash").getAttribute("aria-invalid") === "true",
    invalidRowInputs: $("one-time-rows").querySelectorAll("input").filter((i) => i.getAttribute("aria-invalid") === "true").length,
    focused: document.activeElement ? (document.activeElement.attrs.id || document.activeElement.tagName) : null,
  });
}
snap("boot");
// edit starting cash to garbage -> validation error, results hidden
$("starting-cash").value = "lots";
$("starting-cash").dispatch("input");
snap("bad cash");
$("starting-cash").value = "18000";
$("starting-cash").dispatch("input");
snap("fixed cash");
// pick the "lean" scenario (radio index 1 = first scenario)
const radio = $("scenario-switcher").children[1].children[0];
radio.checked = true; radio.dispatch("change");
snap("lean scenario");
// add then remove a one-time row
$("add-one-time").click();
snap("added row");
const rows = $("one-time-rows").children;
rows[rows.length - 1].children[4].children[0].click();
snap("removed row");
// price below variable cost -> break-even undefined
$("rev-unit_price").value = "1"; $("rev-unit_price").dispatch("input");
snap("price below variable");
// every sample loads
for (let i = 0; i < global.STARTUP_SAMPLES.length; i++) {
  $("sample-select").value = String(i);
  $("load-sample").click();
  snap("sample " + i);
}
$("start-blank").click();
snap("blank");
process.stdout.write(JSON.stringify(out));
