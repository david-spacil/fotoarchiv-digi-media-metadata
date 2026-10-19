// Kontrast dvojic tokenů barev ze style.css pro tmavý i světlý režim
// (WCAG 2: 4,5 : 1 běžný text, 3 : 1 velký text, okraje a grafika).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(
  new URL("../../fotoarchiv/static/style.css", import.meta.url), "utf8")
  .replace(/\/\*[\s\S]*?\*\//g, "");

// Deklarace `--x: …;` z prvního bloku za selektorem.
function block(selector) {
  const i = css.indexOf(`${selector} {`);
  assert.ok(i >= 0, `blok ${selector} ve style.css`);
  const body = css.slice(i + selector.length + 2, css.indexOf("}", i));
  const vars = {};
  for (const m of body.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) {
    vars[m[1]] = m[2].trim();
  }
  return vars;
}

const base = block(":root");
const THEMES = {
  tmavý: base,
  světlý: { ...base, ...block(':root[data-rezim="svetly"]') },
};
const DARK = ["tmavý"];

function hex(vars, name, seen = []) {
  const v = vars[name];
  assert.ok(v, `token ${name}`);
  const ref = v.match(/^var\((--[\w-]+)\)$/);
  if (ref) {
    assert.ok(!seen.includes(name), `cyklus u ${name}`);
    return hex(vars, ref[1], [...seen, name]);
  }
  assert.match(v, /^#[0-9a-f]{6}$/i, `${name} musí být hex`);
  return v;
}

function luminance(h) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(h.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

const TEXT = [
  ["--text", "--bg"], ["--text", "--surface"], ["--text", "--surface-2"],
  ["--text", "--selected"], ["--text", "--stage"],
  ["--text", "--tile-surface"], ["--text", "--field-bg"],
  ["--text", "--field-inherited-bg"], ["--text", "--panel-bg"],
  ["--text-muted", "--bg"], ["--text-muted", "--surface"],
  ["--text-muted", "--stage"], ["--text-muted", "--tile-surface"],
  ["--text-muted", "--field-bg"], ["--text-muted", "--field-inherited-bg"],
  ["--text-muted", "--panel-bg"],
  ["--link", "--bg"], ["--link", "--surface"],
  ["--accent-text", "--accent"],
  ["--header-text", "--header-bg"], ["--header-muted", "--header-bg"],
  ["--header-strong", "--header-bg"], ["--header-ok", "--header-bg"],
  ["--header-warn", "--header-bg"], ["--header-danger", "--header-bg"],
  ["--ok", "--ok-bg"], ["--ok", "--surface"],
  ["--warn", "--warn-bg"], ["--warn", "--surface"],
  ["--danger", "--danger-bg"], ["--danger", "--surface"],
  ["--danger", "--discard-bg"], ["--danger", "--tile-surface"],
  ["--todo", "--todo-bg"], ["--text", "--incomplete-bg"],
  ["--text", "--info-bg"], ["--text", "--warn-bg"],
  ["--text", "--danger-bg"], ["--text", "--mine-bg"],
  ["--src-inherited", "--panel-bg"], ["--src-mixed", "--panel-bg"],
  ["--src-own", "--panel-bg"], ["--src-place", "--panel-bg"],
  ["--loupe-text", "--loupe-bg"], ["--loupe-text", "--loupe-surface"],
  ["--loupe-text", "--loupe-selected"], ["--loupe-muted", "--loupe-surface"],
];
const GRAPHIC = [
  ["--border-strong", "--field-bg"], ["--border-strong", "--surface"],
  ["--accent", "--surface"], ["--accent", "--stage"],
  ["--accent", "--tile-surface"], ["--focus", "--bg"],
  ["--loupe-current", "--loupe-surface"],
  ["--current", "--tile-surface"], ["--current", "--selected"],
  ["--current", "--stage"],
];
const PEOPLE = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => `--p${i}`);

for (const [theme, vars] of Object.entries(THEMES)) {
  test(`kontrast textu: ${theme}`, () => {
    for (const [fg, bg] of TEXT) {
      const r = ratio(hex(vars, fg), hex(vars, bg));
      assert.ok(r >= 4.5, `${fg} na ${bg}: ${r.toFixed(2)}`);
    }
  });
  test(`kontrast okrajů a grafiky: ${theme}`, () => {
    for (const [fg, bg] of GRAPHIC) {
      const r = ratio(hex(vars, fg), hex(vars, bg));
      assert.ok(r >= 3, `${fg} na ${bg}: ${r.toFixed(2)}`);
    }
  });
}

// Pruh autorů sousedí s pozadím mřížky; na tmavém musí být vidět.
for (const theme of DARK) {
  test(`barvy osob na tmavé mřížce: ${theme}`, () => {
    const vars = THEMES[theme];
    const colors = PEOPLE.map((p) => hex(vars, p));
    for (const [i, c] of colors.entries()) {
      const r = ratio(c, hex(vars, "--stage"));
      assert.ok(r >= 3, `${PEOPLE[i]} na --stage: ${r.toFixed(2)}`);
    }
    assert.equal(new Set(colors).size, colors.length);
  });
}
