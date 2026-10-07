// Rozdělení souborů po dnech (scénáře ze specifikace metadata-workspace,
// „Zobrazení podle data“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  byDay, dayLabel, personIndex, REST_COLOR, stripeStops,
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
