// Kontrola poškozených souborů v průvodci importem (scénáře ze specifikace
// photo-import, „Kontrola souborů v přehledu“, „Volba u podezřelých
// souborů“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  checkCounts, damagedFiles, toggleAllowed, unchecked,
} from "../../fotoarchiv/static/integrity.js";

const ok = { stav: "ok", duvody: [], nuly: null };
const necitelny = { stav: "necitelny", nuly: null,
  duvody: ["soubor nejde otevřít jako obrázek", "768 KiB nul od začátku"] };
const podezrely = { stav: "podezrely", nuly: null,
  duvody: ["119 KiB nul na konci"] };

const soubory = [
  { cesta: "20151107_135155.jpg", typ: "foto", kontrola: podezrely },
  { cesta: "20151107_140851.jpg", typ: "foto", kontrola: necitelny },
  { cesta: "P1.JPG", typ: "foto", kontrola: ok },
  { cesta: "v.mp4", typ: "video", kontrola: null },
  { cesta: "prezentace.pptx", typ: "nepodporovany", kontrola: null },
];

test("nezkontrolované jsou jen podporované soubory bez výsledku", () => {
  assert.deepEqual(unchecked(soubory).map((f) => f.cesta), ["v.mp4"]);
});

test("souhrn kontroly", () => {
  assert.deepEqual(checkCounts(soubory),
    { ok: 1, podezrely: 1, necitelny: 1, nezkontrolovano: 1 });
});

test("výchozí stav: podezřelý se nepřenese", () => {
  assert.deepEqual(damagedFiles(soubory), [
    { cesta: "20151107_135155.jpg", stav: "podezrely",
      duvod: "119 KiB nul na konci", povoleno: false },
    { cesta: "20151107_140851.jpg", stav: "necitelny",
      duvod: "soubor nejde otevřít jako obrázek; 768 KiB nul od začátku",
      povoleno: false },
  ]);
});

test("povolení platí jen pro podezřelý", () => {
  const d = damagedFiles(soubory,
    ["20151107_135155.jpg", "20151107_140851.jpg"]);
  assert.deepEqual(d.map((x) => x.povoleno), [true, false]);
});

test("přepnutí povolení", () => {
  assert.deepEqual(toggleAllowed([], "b.jpg", true), ["b.jpg"]);
  assert.deepEqual(toggleAllowed(["b.jpg", "a.jpg"], "c.jpg", true),
    ["a.jpg", "b.jpg", "c.jpg"]);
  assert.deepEqual(toggleAllowed(["a.jpg", "b.jpg"], "a.jpg", false),
    ["b.jpg"]);
});
