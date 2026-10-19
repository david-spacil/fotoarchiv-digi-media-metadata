// Vyloučení z importu: přepínání nad výběrem, páry fotka–RAW a počty
// (scénáře ze specifikace photo-import, „Vyloučení z importu“,
// „Počty a uložení vyloučených“ a „Vyloučení RAWu k fotce“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  applyToggle, excludedCounts, importCount, pairKey, pairedRaws, planToggle,
  withExcluded,
} from "../../fotoarchiv/static/vylouceni.js";

const raws = ["DSC/P1503712.RW2", "DSC/P1503713.rw2", "jinde/P1503714.RW2"];

test("klíč páru: cesta bez přípony, bez velikosti písmen", () => {
  assert.equal(pairKey("DSC/P1503712.JPG"), "dsc/p1503712");
  assert.equal(pairKey("DSC/P1503712.RW2"), "dsc/p1503712");
  assert.equal(pairKey("a.b/soubor"), "a.b/soubor");
  assert.deepEqual(pairedRaws(["DSC/p1503712.jpg", "DSC/P1503713.JPG",
    "DSC/P1503714.JPG"], raws), ["DSC/P1503712.RW2", "DSC/P1503713.rw2"]);
});

test("vyloučení a zrušení: přepínač nad výběrem", () => {
  const sel = ["a.jpg", "b.jpg"];
  let ex = new Set();
  let t = planToggle(ex, sel, []);
  assert.deepEqual(t, { exclude: true, raws: [] }); // bez RAWu bez dotazu
  ex = applyToggle(ex, sel, t.exclude);
  assert.deepEqual([...ex], ["a.jpg", "b.jpg"]);
  t = planToggle(ex, sel, []);
  assert.equal(t.exclude, false);
  ex = applyToggle(ex, sel, t.exclude);
  assert.equal(ex.size, 0);
});

test("smíšený výběr se vyloučí celý", () => {
  const ex = new Set(["b.jpg"]);
  const sel = ["a.jpg", "b.jpg", "c.jpg"];
  const t = planToggle(ex, sel, []);
  assert.equal(t.exclude, true);
  assert.deepEqual([...applyToggle(ex, sel, t.exclude)].sort(), sel);
});

test("RAW k fotce: dotaz jen na nevyloučené, vrácení bez dotazu", () => {
  const foto = ["DSC/P1503712.JPG"];
  let t = planToggle(new Set(), foto, raws);
  assert.deepEqual(t, { exclude: true, raws: ["DSC/P1503712.RW2"] });
  // Vyloučit i RAWy.
  let ex = applyToggle(new Set(), foto, true, t.raws);
  assert.deepEqual(excludedCounts(ex, foto, raws), { media: 1, raw: 1 });
  t = planToggle(ex, foto, raws);
  assert.deepEqual(t, { exclude: false, raws: ["DSC/P1503712.RW2"] });
  ex = applyToggle(ex, foto, t.exclude, t.raws);
  assert.equal(ex.size, 0);
  // Jen fotky: RAW zůstane, vrácení fotky nic dalšího nevrací.
  ex = applyToggle(new Set(), foto, true);
  assert.deepEqual(excludedCounts(ex, foto, raws), { media: 1, raw: 0 });
  t = planToggle(ex, foto, raws);
  assert.deepEqual(t, { exclude: false, raws: [] });
});

test("počet pro Importovat a plán podle vyloučení klienta", () => {
  const ops = [
    { z: "a.jpg", stav: "ok" }, { z: "b.jpg", stav: "ok" },
    { z: "c.jpg", stav: "vylouceny", blocked: true },
    { z: "d.jpg", stav: "duplicita" },
    { z: "DSC/P1.RW2", stav: "ok" },
  ];
  assert.equal(importCount(ops, new Set(["c.jpg"])), 3);
  const ex = new Set(["a.jpg", "DSC/P1.RW2"]);
  assert.equal(importCount(ops, ex), 2); // b.jpg a vrácený c.jpg
  assert.deepEqual(withExcluded(ops, ex).map((o) => o.stav),
    ["vylouceny", "ok", "ok", "duplicita", "vylouceny"]);
  assert.equal(importCount(ops, new Set(["a.jpg", "b.jpg", "c.jpg",
    "DSC/P1.RW2"])), 0);
});
