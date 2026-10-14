// Seznam akcí: filtry, hledání a řazení (scénáře ze specifikace
// archive-browsing, „Filtry a hledání“ a „Řazení seznamu“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  filterCounts, listHash, matchesSearch, parseListHash, visibleEvents,
} from "../../fotoarchiv/static/fronta.js";

const ME = "Spáčil, David";
const full = { autori: [38, 38], datum: [38, 38], misto: [38, 38] };
const gaps = { autori: [38, 38], datum: [30, 38], misto: [10, 38] };

function ev(nazev, extra = {}) {
  return { nazev, stav: "rozpracovano", zmeneno_po_exportu: false,
    hotovost: gaps, upravili: {}, drzitel: null, ...extra };
}

const view = (v = {}) => ({ filtr: "vse", hledat: "", razeni: "datum",
  ...v });
const names = (list) => list.map((e) => e.nazev);

test("Moje rozpracované: rozpracovaná ano, hotová beze změn ne", () => {
  const events = [
    ev("2026-01-01 A", { upravili: { [ME]: "2026-10-12T10:00:00" } }),
    ev("2026-01-02 B", { stav: "hotovo", hotovost: full,
      upravili: { [ME]: "2026-10-13T10:00:00" } }),
    ev("2026-01-03 C", { upravili: { "Kopáčová, Zuzana": "2026-10-13" } }),
    ev("2026-01-04 D", { drzitel: { jmeno: ME, vase: true } }),
    ev("2026-01-05 E", { stav: "hotovo", zmeneno_po_exportu: true,
      upravili: { [ME]: "2026-10-13T10:00:00" } }),
  ];
  assert.deepEqual(names(visibleEvents(events, view({ filtr: "moje" }), ME)),
    ["2026-01-05 E", "2026-01-04 D", "2026-01-01 A"]);
  assert.deepEqual(visibleEvents(events, view({ filtr: "moje" }), null)
    .map((e) => e.nazev), ["2026-01-04 D"]);
});

test("K dokončení: úplná rozpracovaná a hotová se změnami", () => {
  const events = [
    ev("2026-01-01 úplná", { hotovost: full }),
    ev("2026-01-02 s mezerami"),
    ev("2026-01-03 změněná", { stav: "hotovo", zmeneno_po_exportu: true }),
    ev("2026-01-04 nová", { stav: "nezpracovano", hotovost: null }),
    ev("2026-01-05 prázdná", { hotovost: { autori: [0, 0], datum: [0, 0],
      misto: [0, 0] } }),
  ];
  assert.deepEqual(names(visibleEvents(events, view({ filtr: "dokoncit" }))),
    ["2026-01-05 prázdná", "2026-01-03 změněná", "2026-01-01 úplná"]);
  assert.deepEqual(
    names(visibleEvents(events, view({ filtr: "nezpracovane" }))),
    ["2026-01-04 nová"]);
});

test("hledání bez diakritiky a velikosti písmen, s filtrem", () => {
  const name = "2026-04-28 kontrola Stezky Drahanskou vrchovinou";
  assert.ok(matchesSearch(name, "stezky drahanska"));
  assert.ok(matchesSearch("2026-09-08 Konference Dějiny", "DEJINY"));
  assert.ok(matchesSearch(name, "  "));
  assert.ok(!matchesSearch(name, "stezky brno"));
  assert.ok(matchesSearch("2026-05-25 PPA 2026 Telč", "ppa"));
  const events = [ev(name), ev("2026-05-25 PPA 2026 Telč",
    { stav: "nezpracovano", hotovost: null })];
  assert.deepEqual(filterCounts(events, view({ hledat: "telc" }), ME),
    { vse: 1, moje: 0, dokoncit: 0, nezpracovane: 1 });
});

test("řazení podle poslední úpravy: B, A, C", () => {
  const events = [
    ev("2026-03-01 A", { upravili: { x: "2026-10-12T09:00:00" } }),
    ev("2026-01-01 B", { upravili: { x: "2026-10-01T09:00:00",
      y: "2026-10-14T08:00:00" } }),
    ev("2026-05-01 C"),
  ];
  assert.deepEqual(names(visibleEvents(events, view({ razeni: "uprava" }))),
    ["2026-01-01 B", "2026-03-01 A", "2026-05-01 C"]);
});

test("řazení podle hotovosti: nejméně hotové nahoře, nezpracované dole",
  () => {
    const events = [
      ev("2026-01-01 nová", { stav: "nezpracovano", hotovost: null }),
      ev("2026-02-01 úplná", { hotovost: full }),
      ev("2026-03-01 mezery"),
      ev("2026-04-01 nová", { stav: "nezpracovano", hotovost: null }),
    ];
    assert.deepEqual(
      names(visibleEvents(events, view({ razeni: "hotovost" }))),
      ["2026-03-01 mezery", "2026-02-01 úplná", "2026-04-01 nová",
        "2026-01-01 nová"]);
  });

test("výchozí řazení podle data sestupně", () => {
  const events = [ev("2025-01-02 x"), ev("2026-04-28 y"), ev("2010-02-26 z")];
  assert.deepEqual(names(visibleEvents(events, parseListHash("#/"))),
    ["2026-04-28 y", "2025-01-02 x", "2010-02-26 z"]);
});

test("stav seznamu v hash adrese", () => {
  assert.deepEqual(parseListHash(""), view());
  assert.deepEqual(parseListHash("#/?filtr=nezpracovane&hledat=telč"),
    view({ filtr: "nezpracovane", hledat: "telč" }));
  assert.deepEqual(parseListHash("#/?filtr=nesmysl&razeni=x"), view());
  assert.equal(listHash(view()), "#/");
  const v = view({ filtr: "moje", hledat: "stezky d", razeni: "uprava" });
  assert.deepEqual(parseListHash(listHash(v)), v);
});
