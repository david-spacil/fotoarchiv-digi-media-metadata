// Rozdělení souborů po dnech (scénáře ze specifikace metadata-workspace,
// „Zobrazení podle data“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  byDay, dayLabel, personIndex, REST_COLOR, sectionInfo, stripeSegments,
  stripeStops,
} from "../../fotoarchiv/static/sections.js";

const dates = {
  "P1503701.JPG": "2026-04-27T10:00:00",
  "20260427_103000.jpg": "2026-04-27T10:30:00",
  "P1503702.JPG": "2026-04-27T11:00:00",
  "20260428_090000.jpg": "2026-04-28T09:00:00",
  "P1503710.JPG": "2026-04-28T09:00:00",
  "IMG-20260428-WA0003.jpg": "2026-04-28",
  "scan_001.jpg": undefined,
};
const dateOf = (f) => dates[f];

test("vícedenní akce: dny vzestupně, přístroje promíchané podle času", () => {
  const files = Object.keys(dates).reverse();
  assert.deepEqual(byDay(files, dateOf), [
    { day: "2026-04-27",
      files: ["P1503701.JPG", "20260427_103000.jpg", "P1503702.JPG"] },
    { day: "2026-04-28",
      files: ["IMG-20260428-WA0003.jpg", "20260428_090000.jpg",
        "P1503710.JPG"] },
    { day: null, files: ["scan_001.jpg"] },
  ]);
});

test("datum bez času je před časy téhož dne", () => {
  const secs = byDay(["P1503710.JPG", "IMG-20260428-WA0003.jpg"], dateOf);
  assert.deepEqual(secs[0].files, ["IMG-20260428-WA0003.jpg", "P1503710.JPG"]);
});

test("shoda času → podle názvu", () => {
  const secs = byDay(["P1503710.JPG", "20260428_090000.jpg"], dateOf);
  assert.deepEqual(secs[0].files, ["20260428_090000.jpg", "P1503710.JPG"]);
});

test("bez dat jen oddíl bez data, prázdný vstup bez oddílů", () => {
  assert.deepEqual(byDay(["b.jpg", "a.jpg"], () => ""),
    [{ day: null, files: ["a.jpg", "b.jpg"] }]);
  assert.deepEqual(byDay([], dateOf), []);
});

test("popisek dne", () => {
  assert.equal(dayLabel("2026-04-28"), "út 28. 4. 2026");
  assert.equal(dayLabel("2026-03-01"), "ne 1. 3. 2026");
});

// Značka autorů (scénáře „Značka autorů v zobrazení po skupinách“).
const key = (n) => n.normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
  .toLowerCase().match(/[\p{L}\p{N}_]+/gu)?.sort().join(" ") || "";

test("barvy osob: pořadí podle klíče, jiný zápis téže osoby", () => {
  const idx = personIndex(["Zkušební, Petr", "Spáčil, David",
    "spacil, david", "David Spáčil", ""], key);
  assert.deepEqual([...idx], [["david spacil", 0], ["petr zkusebni", 1]]);
});

test("pruh: jeden, dva a tři úseky", () => {
  assert.equal(stripeStops(["red"]), "red 0% 100%");
  assert.equal(stripeStops(["red", "blue"]), "red 0% 50%, blue 50% 100%");
  assert.equal(stripeStops(["a", "b", "c"]),
    "a 0% 33.33%, b 33.33% 66.67%, c 66.67% 100%");
});

test("pruh: víc než tři autoři → šedý úsek", () => {
  assert.equal(stripeStops(["a", "b", "c", "d", "e"]),
    `a 0% 25%, b 25% 50%, c 50% 75%, ${REST_COLOR} 75% 100%`);
});

// Navigátor akce (scénáře „Chybějící údaje v navigátoru“ a „Pruh autorů
// oddílu“ ze specifikace metadata-workspace).
const JANA = "Testová, Jana";
const PETR = "Zkušební, Petr";
const none = { akce: [], skupinyBezAutoru: [], souboryBezData: [],
  souboryBezSkupiny: [], souboryBezMista: [], mistaBezSouradnic: {} };

function info(sec, m, authors, discarded = []) {
  return sectionInfo(sec, { ...none, ...m }, {
    authorsOf: (f) => authors[f] || [], keyOf: key,
    counted: (f) => !discarded.includes(f),
  });
}

test("navigátor: soubory bez data ve skupině, v pořadí oddílu", () => {
  const files = ["a.jpg", "b.jpg", "c.jpg"];
  const r = info({ gid: "jana", key: "g:jana", files },
    { souboryBezData: ["c.jpg", "a.jpg", "x.jpg"] },
    { "a.jpg": [JANA], "b.jpg": [JANA], "c.jpg": [JANA] });
  assert.deepEqual(r.bezData, ["a.jpg", "c.jpg"]);
  assert.deepEqual(r.bezAutoru, []);
  assert.equal(r.skupinaBezAutoru, false);
});

test("navigátor: skupina bez autorů a soubory bez autorů", () => {
  const r = info({ gid: "g", key: "g:g", files: ["a.jpg", "b.jpg"] },
    { skupinyBezAutoru: ["g"] }, { "b.jpg": [PETR] });
  assert.equal(r.skupinaBezAutoru, true);
  assert.deepEqual(r.bezAutoru, ["a.jpg"]);
});

test("navigátor: soubory bez místa jen z výsledku missing()", () => {
  const r = info({ gid: "g", key: "g:g", files: ["a.jpg", "b.jpg"] },
    { souboryBezMista: ["b.jpg"] }, {});
  assert.deepEqual(r.bezMista, ["b.jpg"]);
  assert.deepEqual(info({ gid: "g", key: "g:g", files: ["a.jpg"] }, {}, {})
    .bezMista, []);
});

test("navigátor: označený soubor se nepočítá", () => {
  const r = info({ gid: null, key: "d:2015-11-07", files: ["a.jpg", "b.jpg"] },
    { souboryBezData: [] }, { "a.jpg": [JANA] }, ["b.jpg"]);
  assert.deepEqual(r.bezAutoru, []);
  assert.deepEqual(r.autori.map((p) => p.count), [1]);
});

test("navigátor: bez skupiny jen podle data, ne v oddílu Bez skupiny", () => {
  const m = { souboryBezSkupiny: ["a.jpg", "b.jpg"],
    souboryBezData: ["a.jpg", "b.jpg"] };
  const files = ["a.jpg", "b.jpg"];
  const day = info({ gid: null, key: "d:2015-11-07", files }, m, {});
  assert.deepEqual(day.bezSkupiny, files);
  const noDate = info({ gid: null, key: "d:", files }, m, {});
  assert.deepEqual(noDate.bezData, []);
  assert.deepEqual(noDate.bezSkupiny, files);
  const noGroup = info({ gid: null, key: "g:", files }, m, {});
  assert.deepEqual(noGroup.bezSkupiny, []);
  assert.deepEqual(noGroup.bezData, files);
});

test("navigátor: autoři s počty, jiný zápis téže osoby", () => {
  const r = info({ gid: "g", key: "g:g", files: ["a", "b", "c"] }, {},
    { a: [PETR], b: [JANA, PETR], c: ["petr zkusebni"] });
  assert.deepEqual(r.autori.map((p) => [p.name, p.count]),
    [[PETR, 3], [JANA, 1]]);
});

test("pruh autorů oddílu: poměr 2 : 1", () => {
  const files = Array.from({ length: 30 }, (_, i) => `f${i}.jpg`);
  const authors = Object.fromEntries(files.map((f, i) =>
    [f, [i < 20 ? JANA : PETR]]));
  const r = info({ gid: "g", key: "g:g", files }, {}, authors);
  const colors = { [key(JANA)]: "var(--p0)", [key(PETR)]: "var(--p1)" };
  assert.deepEqual(stripeSegments(r.autori, r.bezAutoru.length,
    (k) => colors[k]), [
    { color: "var(--p0)", count: 20, names: [JANA] },
    { color: "var(--p1)", count: 10, names: [PETR] },
  ]);
});

test("pruh autorů oddílu: zbytek šedě, bez autorů šrafovaně", () => {
  const autori = ["a", "b", "c", "d", "e"].map((k, i) =>
    ({ key: k, name: k.toUpperCase(), count: 5 - i }));
  assert.deepEqual(stripeSegments(autori, 4, (k) => k), [
    { color: "a", count: 5, names: ["A"] },
    { color: "b", count: 4, names: ["B"] },
    { color: "c", count: 3, names: ["C"] },
    { color: REST_COLOR, count: 3, names: ["D", "E"] },
    { color: null, count: 4, names: [] },
  ]);
});
