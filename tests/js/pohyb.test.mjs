// Pohyb klávesnicí v mřížce a lupě (scénáře ze změny sipky-v-mrizce,
// „Cíl pohybu jako čisté funkce v static/pohyb.js“).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  klavesa, naPas, oddil, radek, stranka, vLupeKroku,
} from "../../fotoarchiv/static/pohyb.js";

// Mřížka: 5 sloupců, dlaždice 100×100, mezera 20 px, každý oddíl
// začíná novým řádkem a mezi oddíly je předěl (hlavička) 60 px.
const KROK = 120, MEZERA = 20, PREDEL = 60;
const rect = (c, top) => ({ left: c * KROK, top, width: 100, height: 100 });

// rects/order/secOf z rozložení: pole oddílů, každý jako seznam souborů.
function mrizka(oddily) {
  const order = [], rects = [], secOf = new Map();
  let top = 0;
  oddily.forEach((files, s) => {
    files.forEach((nazev, k) => {
      order.push(nazev);
      rects.push(rect(k % 5, top + Math.floor(k / 5) * KROK));
      secOf.set(nazev, `skupina ${s + 1}`);
    });
    top += Math.max(1, Math.ceil(files.length / 5)) * KROK - MEZERA
      + PREDEL;
  });
  return { order, rects, secOf };
}

const soubory = (od, kolik) => Array.from({ length: kolik },
  (_, k) => `IMG_${String(od + k).padStart(4, "0")}.JPG`);

// A: sedm souborů (řádky 5 + 2), B: osm souborů (řádky 5 + 3).
const AB = mrizka([soubory(1, 7), soubory(8, 8)]);

test("radek: dolů do kratšího řádku, nejbližší střed", () => {
  // 4. soubor A (index 3, 4. sloupec) → 7. soubor A (index 6)
  assert.equal(radek(AB.rects, 3, 1), 6);
});

test("radek: dolů přes předěl oddílu na stejný sloupec", () => {
  // 7. soubor A (index 6, 2. sloupec) → 2. soubor B (index 8)
  assert.equal(radek(AB.rects, 6, 1), 8);
});

test("radek: nahoru z konce řádku na kratší řádek před ním", () => {
  // 12. soubor (index 11, 5. sloupec 1. řádku B) → 2. řádek A má jen
  // 1.–2. sloupec, nejbližší je 2. = 7. soubor A (index 6)
  assert.equal(radek(AB.rects, 11, -1), 6);
});

test("radek: při shodě vzdálenosti vybere levější dlaždici", () => {
  // start ve 3. sloupci, pod ním 4. a 2. sloupec stejně daleko
  const rects = [rect(2, 0), rect(3, 120), rect(1, 120)];
  assert.equal(radek(rects, 0, 1), 2);
});

test("radek: jediný řádek se nehýbe nahoru ani dolů", () => {
  const rects = [0, 1, 2, 3, 4].map((c) => rect(c, 0));
  assert.equal(radek(rects, 2, -1), 2);
  assert.equal(radek(rects, 2, 1), 2);
});

test("radek: subpixelové topy ve stejné řadě splynou", () => {
  const rects = [
    { left: 0, top: 0, width: 100, height: 100 },
    { left: 120, top: 0.4, width: 100, height: 100 },
    { left: 0, top: 120, width: 100, height: 100 },
    { left: 120, top: 120.6, width: 100, height: 100 },
  ];
  assert.equal(radek(rects, 1, 1), 3);
  assert.equal(radek(rects, 3, -1), 1);
});

// Jeden oddíl, šest řádků po pěti souborech; stránka = čtyři řádky.
const VELKA = mrizka([soubory(1, 30)]);
const STRANKA = 4 * KROK;

test("stranka: PageDown o čtyři řádky, stejný sloupec", () => {
  // 3. sloupec 1. řádku (index 2) → 3. sloupec 5. řádku (index 22)
  assert.equal(stranka(VELKA.rects, 2, 1, STRANKA), 22);
  // obráceně: 3. sloupec 6. řádku (index 27) → 3. sloupec 2. řádku
  assert.equal(stranka(VELKA.rects, 27, -1, STRANKA), 7);
});

test("stranka: za koncem skočí na poslední řádek", () => {
  // index 17 (3. sloupec 4. řádku): žádný řádek není o stránku dál,
  // cílem je poslední řádek, v něm nejbližší sloupec (index 27)
  assert.equal(stranka(VELKA.rects, 17, 1, STRANKA), 27);
});

test("stranka: PageUp z prvního řádku se nehýbe", () => {
  assert.equal(stranka(VELKA.rects, 1, -1, STRANKA), 1);
});

test("oddil: dolů na začátek dalšího oddílu", () => {
  assert.equal(oddil(AB.order, AB.secOf, 3, 1), 7);
  assert.equal(oddil(AB.order, AB.secOf, 6, 1), 7);
});

test("oddil: nahoru uprostřed oddílu na jeho začátek", () => {
  assert.equal(oddil(AB.order, AB.secOf, 9, -1), 7);
});

test("oddil: nahoru ze začátku oddílu na začátek předchozího", () => {
  assert.equal(oddil(AB.order, AB.secOf, 7, -1), 0);
  assert.equal(oddil(AB.order, AB.secOf, 0, -1), 0);
});

test("oddil: dolů v posledním oddílu se nehýbe", () => {
  assert.equal(oddil(AB.order, AB.secOf, 9, 1), 9);
  assert.equal(oddil(AB.order, AB.secOf, 14, 1), 14);
});

test("naPas: počet dlaždic na šířku pásu, nejméně jedna", () => {
  assert.equal(naPas(1000, 100), 10);
  assert.equal(naPas(50, 100), 1);
  assert.equal(naPas(1000, 0), 1);
});

const kl = (key, m = {}) => klavesa({
  key, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false,
  ...m,
});

test("klavesa: Ctrl+A i Cmd+A vyberou vše, samotné a ne", () => {
  assert.deepEqual(kl("a", { ctrlKey: true }),
    { druh: "vse", smer: 0, rozsir: false });
  assert.deepEqual(kl("A", { metaKey: true }),
    { druh: "vse", smer: 0, rozsir: false });
  assert.equal(kl("a"), null);
  assert.equal(kl("a", { altKey: true, ctrlKey: true }), null);
});

test("klavesa: Alt a Ctrl u pohybových kláves necháme prohlížeči", () => {
  assert.equal(kl("ArrowLeft", { altKey: true }), null);
  assert.equal(kl("ArrowDown", { ctrlKey: true }), null);
  assert.equal(kl("ArrowRight", { metaKey: true }), null);
});

test("klavesa: šipky, stránka, kraj, Shift a nic neznámého", () => {
  assert.deepEqual(kl("ArrowLeft"),
    { druh: "vodorovne", smer: -1, rozsir: false });
  assert.deepEqual(kl("ArrowDown", { shiftKey: true }),
    { druh: "svisle", smer: 1, rozsir: true });
  assert.deepEqual(kl("PageUp"),
    { druh: "stranka", smer: -1, rozsir: false });
  assert.deepEqual(kl("Home"), { druh: "kraj", smer: -1, rozsir: false });
  assert.deepEqual(kl("End"), { druh: "kraj", smer: 1, rozsir: false });
  assert.equal(kl("x"), null);
});

// Lehká lupa kroku skupin (změna lupa-ve-skupinach).
const PORADI = ["P1503718.JPG", "P1503719.JPG", "P1503720.JPG",
  "P1503721.JPG"]; // první dva skupina DOD 2015_Lenka, pak DOD 2015_Olga
const k = (key, mod = {}) => ({ key, ...mod });

test("lupa kroku: šipka vpravo přejde přes hranici skupin", () => {
  assert.equal(vLupeKroku(PORADI, "P1503719.JPG", k("ArrowRight")),
    "P1503720.JPG");
  assert.equal(vLupeKroku(PORADI, "P1503720.JPG", k("ArrowLeft")),
    "P1503719.JPG");
});

test("lupa kroku: za krajem nepřeteče", () => {
  assert.equal(vLupeKroku(PORADI, "P1503721.JPG", k("ArrowRight")), null);
  assert.equal(vLupeKroku(PORADI, "P1503718.JPG", k("ArrowLeft")), null);
  assert.equal(vLupeKroku(PORADI, "P1503718.JPG", k("Home")), null);
});

test("lupa kroku: Home a End skočí na kraje", () => {
  assert.equal(vLupeKroku(PORADI, "P1503720.JPG", k("Home")),
    "P1503718.JPG");
  assert.equal(vLupeKroku(PORADI, "P1503719.JPG", k("End")),
    "P1503721.JPG");
});

test("lupa kroku: ostatní klávesy a modifikátory ignoruje", () => {
  for (const key of ["ArrowUp", "ArrowDown", "PageUp", "PageDown", "a",
    "Enter", "Delete"]) {
    assert.equal(vLupeKroku(PORADI, "P1503719.JPG", k(key)), null, key);
  }
  for (const mod of [{ shiftKey: true }, { ctrlKey: true },
    { metaKey: true }, { altKey: true }]) {
    assert.equal(vLupeKroku(PORADI, "P1503719.JPG", k("ArrowRight", mod)),
      null, JSON.stringify(mod));
  }
});

test("lupa kroku: bez aktuálního začne prvním, prázdné pořadí nic", () => {
  assert.equal(vLupeKroku(PORADI, null, k("ArrowRight")), "P1503718.JPG");
  assert.equal(vLupeKroku([], null, k("End")), null);
});
