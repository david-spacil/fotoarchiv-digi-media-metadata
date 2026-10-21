// Dědění v JS proti stejným fixturám jako pytest (tests/test_model.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { missing, resolve } from "../../fotoarchiv/static/inherit.js";

const dir = join(import.meta.dirname, "..", "fixtures", "inheritance");

for (const name of readdirSync(dir).filter((n) => n.endsWith(".json"))) {
  test(`fixtura ${name}`, () => {
    const c = JSON.parse(readFileSync(join(dir, name), "utf8"));
    for (const [file, expected] of Object.entries(c.ocekavano)) {
      assert.deepEqual(resolve(c.metadata, file), expected);
    }
  });
}

test("skupina bez autorů", () => {
  const doc = {
    akce: { nazev: "x", datum_od: "2026-04-28", datum_do: "2026-04-28" },
    skupiny: { a: {}, b: { autori: ["Příkladný, Daniel"] }, c: {} },
    soubory: {
      "1.jpg": { skupina: "a", datum: "2026-04-28" },
      "2.jpg": { skupina: "b" },
      "3.jpg": { skupina: "c", autori: ["Modelová, Zuzana"] },
      "4.jpg": { skupina: "zmizela", datum: "2026-04-28" },
    },
  };
  assert.deepEqual(missing(doc), {
    akce: [],
    skupinyBezAutoru: ["a"],
    souboryBezData: ["2.jpg", "3.jpg"],
    souboryBezSkupiny: ["4.jpg"],
    souboryBezMista: [],
    mistaBezSouradnic: {},
  });
});

test("soubory bez místa jen při víc místech akce", () => {
  const doc = (mista) => ({
    akce: { mista },
    skupiny: {},
    soubory: { "a.jpg": {}, "b.jpg": { misto: "Zkušebnice" } },
  });
  assert.deepEqual(missing(doc(["Vzorkov"])).souboryBezMista, []);
  assert.deepEqual(missing(doc(["Pokusín", "Zkušebnice"])).souboryBezMista,
    ["a.jpg"]);
});

test("místa bez souřadnic jen u souborů bez GPS", () => {
  const doc = {
    akce: { mista: ["Zkušebná"] },
    souradnice_mist: { Vzorkov: null },
    skupiny: {},
    soubory: {
      "a.jpg": {},
      "b.jpg": { gps: [49.4, 16.8] },
      "c.jpg": { misto: "Vzorkov" },
      "d.jpg": { misto: "Zkušebnice", gps: [49.4, 16.8] },
      "e.jpg": {},
    },
  };
  assert.deepEqual(missing(doc).mistaBezSouradnic,
    { "Zkušebná": ["a.jpg", "e.jpg"] });
  doc.souradnice_mist.Zkušebná = { gps: [49.15, 16.45] };
  assert.deepEqual(missing(doc).mistaBezSouradnic, {});
});

test("soubory k vyřazení se nepočítají", () => {
  const doc = {
    akce: { mista: ["Zkušebnice", "Vzorkov"] },
    skupiny: { a: {}, b: {} },
    soubory: {
      "1.jpg": { skupina: "a", vyradit: true },
      "2.jpg": { skupina: "b", vyradit: true },
      "3.jpg": { skupina: "b", datum: "2026-04-28", misto: "Zkušebnice" },
      "4.jpg": { vyradit: true },
    },
  };
  const m = missing(doc);
  assert.deepEqual(m.skupinyBezAutoru, ["b"]);
  assert.deepEqual(m.souboryBezData, []);
  assert.deepEqual(m.souboryBezSkupiny, []);
  assert.deepEqual(m.souboryBezMista, []);
});

test("autoři u akce skupině autory nedodají", () => {
  // Starší dokument s `akce.autori` (vypuštěný klíč schématu /2).
  const doc = {
    akce: { autori: ["Příkladný, Daniel"] },
    skupiny: { g9: { nazev: "G9" }, mobil: {} },
    soubory: {
      "P1503712.JPG": { skupina: "g9" },
      "20260428_101500.jpg": { skupina: "mobil" },
    },
  };
  assert.deepEqual(missing(doc).skupinyBezAutoru, ["g9", "mobil"]);
});
