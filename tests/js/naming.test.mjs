// Čistá část nástroje pojmenování osob: výřez z obdélníku obličeje
// na zmenšenině a pořadí kroků kola (naming.js).
import { test } from "node:test";
import assert from "node:assert/strict";

import { OKRAJ, pocetadlo, posunVyberu, poradiOsob, prechod, vyrez,
  vyrid, zkratka } from "../../fotoarchiv/static/naming.js";

test("výřez: čtverec s okrajem kolem obličeje", () => {
  const q = vyrez({ x1: 100, y1: 100, x2: 200, y2: 250 }, 1600, 1200, 256);
  // větší strana 150 → strana 150 × OKRAJ, střed obličeje (150, 175)
  const side = 150 * OKRAJ;
  assert.ok(Math.abs(q.sw - side) < 1e-9 && Math.abs(q.sh - side) < 1e-9);
  assert.ok(Math.abs(q.sx - (150 - side / 2)) < 1e-9);
  assert.ok(Math.abs(q.sy - (175 - side / 2)) < 1e-9);
  assert.deepEqual({ dw: q.dw, dh: q.dh }, { dw: 256, dh: 256 });
});

test("výřez: ořezání u okraje fotky", () => {
  // obličej v levém horním rohu — čtverec se posune dovnitř, ne ven
  const q = vyrez({ x1: 0, y1: 0, x2: 40, y2: 40 }, 100, 100);
  assert.ok(q.sx >= 0 && q.sy >= 0);
  assert.ok(q.sx + q.sw <= 100 + 1e-9, "vejde se na šířku");
  assert.ok(q.sy + q.sh <= 100 + 1e-9, "vejde se na výšku");
});

test("výřez: u pravého dolního rohu se čtverec vejde dovnitř", () => {
  const q = vyrez({ x1: 90, y1: 95, x2: 100, y2: 100 }, 100, 100);
  assert.ok(q.sx + q.sw <= 100 + 1e-9);
  assert.ok(q.sy + q.sh <= 100 + 1e-9);
  assert.ok(q.sx >= 0 && q.sy >= 0);
});

test("výřez: obdélník přesahující zmenšeninu se ořízne", () => {
  const q = vyrez({ x1: -10, y1: -10, x2: 2000, y2: 2000 }, 1600, 1200);
  assert.ok(q.sx >= 0 && q.sy >= 0);
  assert.ok(q.sx + q.sw <= 1600 + 1e-9);
  assert.ok(q.sy + q.sh <= 1200 + 1e-9);
});

test("výřez: nulová a obrácená plocha = null", () => {
  assert.equal(vyrez({ x1: 10, y1: 10, x2: 10, y2: 40 }, 100, 100), null);
  assert.equal(vyrez({ x1: 40, y1: 10, x2: 10, y2: 40 }, 100, 100), null);
  // obdélník oříznutý na hranu → nulová plocha
  assert.equal(vyrez({ x1: 120, y1: 0, x2: 200, y2: 40 }, 100, 100), null);
});

test("výřez: neplatné rozměry a chybějící souřadnice = null", () => {
  assert.equal(vyrez({ x1: 0, y1: 0, x2: 10, y2: 10 }, 0, 100), null);
  assert.equal(vyrez({ x1: 0, y1: 0, x2: 10, y2: 10 }, 100, -5), null);
  assert.equal(vyrez(null, 100, 100), null);
  assert.equal(vyrez({ x1: 0, y1: 0 }, 100, 100), null);
  assert.equal(vyrez({ x1: NaN, y1: 0, x2: 10, y2: 10 }, 100, 100), null);
});

test("pořadí osob: więcej obličejů dřív, při shodě podle id", () => {
  const r = poradiOsob([{ id: "b", pocet: 2 }, { id: "a", pocet: 12 },
    { id: "c", pocet: 2 }]);
  assert.deepEqual(r.map((o) => o.id), ["a", "b", "c"]);
});

test("přechod: další osoba z fronty", () => {
  const a = { id: "a", pocet: 3 };
  const krok = prechod([a, { id: "b", pocet: 1 }], 0);
  assert.equal(krok.krok, "osoba");
  assert.equal(krok.osoba, a);
});

test("přechod: konec kola s odloženými nabízí projít znovu", () => {
  const krok = prechod([], 2);
  assert.equal(krok.krok, "konec");
  assert.equal(krok.odlozene, 2);
  assert.equal(krok.nabizi, true);
});

test("přechod: bez odložených je hotovo a nenabízí", () => {
  const krok = prechod([], 0);
  assert.equal(krok.krok, "konec");
  assert.equal(krok.nabizi, false);
});

test("vyřízení osoby: pojmenovat → další, po poslední konec", () => {
  let fronta = poradiOsob([{ id: "x", pocet: 5 }, { id: "y", pocet: 1 }]);
  let krok = prechod(fronta, 0);
  assert.equal(krok.osoba.id, "x");
  fronta = vyrid(fronta, "x");          // pojmenovat / sloučit / skrýt
  krok = prechod(fronta, 0);
  assert.equal(krok.osoba.id, "y");
  fronta = vyrid(fronta, "y");          // nevim → odložena, fronta beze ní
  assert.equal(prechod(fronta, 1).krok, "konec");
  assert.equal(prechod(fronta, 1).nabizi, true);
});

test("vyřízení neexistující id frontu nemění", () => {
  const fronta = [{ id: "x" }];
  assert.deepEqual(vyrid(fronta, "jiné"), fronta);
});

test("počítadlo osob", () => {
  assert.equal(pocetadlo(0, 3), "Osoba 1 z 3");
  assert.equal(pocetadlo(2, 1), "Osoba 3 z 3");
});

test("zkratky: PageDown odloží, Alt+Delete skryje", () => {
  assert.equal(zkratka({ key: "PageDown" }), "odlozit");
  assert.equal(zkratka({ key: "Delete", altKey: true }), "skryt");
});

test("zkratky: klávesy pro editaci pole a prohlížeč nic nedělají", () => {
  for (const e of [
    { key: "Delete" },                              // smaže znak
    { key: "Delete", ctrlKey: true },               // smaže slovo
    { key: "Delete", shiftKey: true },              // vyjmout (Windows)
    { key: "Delete", altKey: true, ctrlKey: true },
    { key: "ArrowRight", ctrlKey: true },           // skok o slovo
    { key: "PageDown", ctrlKey: true },             // další panel
    { key: "PageDown", shiftKey: true },
    { key: "PageDown", altKey: true },
    { key: "Enter" }, { key: "Escape" }, { key: "a" },
  ]) assert.equal(zkratka(e), null, JSON.stringify(e));
});

test("zkratky: podržená klávesa se neopakuje", () => {
  assert.equal(zkratka({ key: "PageDown", repeat: true }), null);
  assert.equal(zkratka({ key: "Delete", altKey: true, repeat: true }), null);
});

test("našeptávání: šipky posouvají výběr a přetáčejí se", () => {
  // bez výběru: dolů první, nahoru poslední
  assert.equal(posunVyberu(-1, 3, true), 0);
  assert.equal(posunVyberu(-1, 3, false), 2);
  // chybějící výběr (NaN) se chová stejně
  assert.equal(posunVyberu(NaN, 3, true), 0);
  assert.equal(posunVyberu(0, 3, true), 1);
  assert.equal(posunVyberu(2, 3, true), 0);
  assert.equal(posunVyberu(0, 3, false), 2);
});
