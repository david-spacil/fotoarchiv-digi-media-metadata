// Kontrola poškozených souborů v průvodci importem (scénáře ze specifikace
// photo-import, „Kontrola souborů v přehledu“, „Volba u podezřelých
// souborů“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  applyDecisionChanges, checkCounts, cleanupDecisions, damagedFiles,
  damagedMap, damagedText, decisionChanges, odebranaPolohaFiles,
  toggleAllowed, unchecked,
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

// --- odznak a přehodnocení na ploše akce (issue #10, varianta C) -----------

test("damagedMap vyřadí potvrzené a vyřazené", () => {
  const poskozene = {
    "a.jpg": { stav: "podezrely", duvody: ["119 KiB nul na konci"] },
    "b.jpg": { stav: "necitelny", duvody: ["soubor nejde otevřít"] },
    "c.jpg": { stav: "podezrely", duvody: ["8 KiB nul"] },
  };
  const soubory = { "b.jpg": { overeno: true } };
  assert.deepEqual(Object.keys(damagedMap(poskozene, soubory)),
    ["a.jpg", "c.jpg"]);
  // Vyřazený se též počítá mimo; bez dokumentu zůstává vše.
  soubory["a.jpg"] = { vyradit: true };
  assert.deepEqual(Object.keys(damagedMap(poskozene, soubory)), ["c.jpg"]);
  assert.deepEqual(damagedMap(null, {}), {});
});

test("damagedText: stav a důvody", () => {
  assert.equal(
    damagedText({ stav: "necitelny", duvody: ["nejde otevřít", "768 KiB"] }),
    "nečitelný: nejde otevřít; 768 KiB");
  assert.equal(damagedText({ stav: "podezrely", duvody: [] }),
    "podezřelý");
});

test("damagedMap respektuje znacky ze serveroveho souhrnu", () => {
  const poskozene = {
    "a.jpg": { stav: "podezrely", duvody: ["d"] },
    "b.jpg": { stav: "necitelny", duvody: ["d"], overeno: true },
    "c.jpg": { stav: "necitelny", duvody: ["d"], vyradit: true },
  };
  assert.deepEqual(Object.keys(damagedMap(poskozene)), ["a.jpg"]);
  assert.equal(Object.keys(damagedMap(poskozene)).length, 1);
  // Nezapsana znacka v rozepsanem dokumentu hosti take.
  assert.deepEqual(damagedMap(poskozene, { "a.jpg": { overeno: true } }), {});
});

test("cleanupDecisions: výchozí stav řádků dialogu úklidu", () => {
  const poskozene = {
    "a.jpg": { stav: "podezrely" },
    "b.jpg": { stav: "necitelny", overeno: true },
    "c.jpg": { stav: "necitelny", vyradit: true },
    "d.jpg": { stav: "podezrely" },
  };
  // d.jpg: potvrzení zatím jen v rozepsaném dokumentu.
  const soubory = { "d.jpg": { overeno: true } };
  assert.deepEqual(
    cleanupDecisions(["a.jpg", "b.jpg", "c.jpg", "d.jpg"], poskozene,
      soubory),
    { "a.jpg": null, "b.jpg": "overeno", "c.jpg": "vyradit",
      "d.jpg": "overeno" });
});

test("decisionChanges: jen rozdíly proti dokumentu", () => {
  const soubory = {
    "a.jpg": {}, "b.jpg": { overeno: true }, "c.jpg": { overeno: true },
    "d.jpg": { vyradit: true }, "e.jpg": { overeno: true },
  };
  const changes = decisionChanges({
    "a.jpg": "overeno",   // nově potvrzený
    "b.jpg": null,        // potvrzení zrušené
    "c.jpg": "vyradit",   // z potvrzeného rovnou k vyřazení
    "d.jpg": "vyradit",   // už označený: beze změny
    "e.jpg": "overeno",   // potvrzený: beze změny
  }, soubory);
  assert.deepEqual(changes, {
    vyradit: ["c.jpg"], overeno: ["a.jpg"], zrusit: ["b.jpg", "c.jpg"],
  });
  assert.deepEqual(decisionChanges({ "a.jpg": null }, soubory),
    { vyradit: [], overeno: [], zrusit: [] });
});

test("applyDecisionChanges zapíše změny a umí je vrátit", () => {
  const soubory = { "a.jpg": { popis: "x" }, "b.jpg": { overeno: true },
    "c.jpg": { overeno: true } };
  const original = structuredClone(soubory);
  const changes = { vyradit: ["c.jpg", "n.jpg"], overeno: ["a.jpg"],
    zrusit: ["b.jpg", "c.jpg"] };
  const revert = applyDecisionChanges(soubory, changes);
  assert.deepEqual(soubory, {
    "a.jpg": { popis: "x", overeno: true }, "b.jpg": {},
    "c.jpg": { vyradit: true }, "n.jpg": { vyradit: true },
  });
  revert();
  assert.deepEqual(soubory, original);
});

// --- odebraná poloha (blokovat-odebranou-polohu, úkol 3.1) -----------------

const souboryPoloha = [
  { cesta: "PXL_20260917.MP.jpg", typ: "foto", poloha_odebrana: true,
    kontrola: ok },
  { cesta: "mailem.jpg", typ: "foto", kontrola: podezrely },
  { cesta: "IMG-20260428-WA0003.jpg", typ: "foto", kontrola: ok },
];

test("odebraná poloha z příznaku i ze seznamu cest", () => {
  assert.deepEqual(odebranaPolohaFiles(souboryPoloha, ["mailem.jpg"]), [
    { cesta: "PXL_20260917.MP.jpg", duvod: "telefon odebral polohu" },
    { cesta: "mailem.jpg", duvod: "telefon odebral polohu" },
  ]);
  assert.deepEqual(odebranaPolohaFiles(souboryPoloha).map((f) => f.cesta),
    ["PXL_20260917.MP.jpg"]);
});

test("odebraná poloha nevstoupí do bloku poškozených", () => {
  const d = damagedFiles(souboryPoloha, [], ["mailem.jpg"]);
  assert.deepEqual(d.map((x) => x.cesta), []);
  // Bez seznamu zůstává podezřelý v bloku poškozených jako dosud.
  assert.deepEqual(damagedFiles(souboryPoloha).map((x) => x.cesta),
    ["mailem.jpg"]);
});
