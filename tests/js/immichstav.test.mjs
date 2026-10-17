// Texty stavů akce v Immichi na kartě a ploše (immichstav.js).
import { test } from "node:test";
import assert from "node:assert/strict";

import { immichStav } from "../../fotoarchiv/static/immichstav.js";

test("načítání a rozpoznávání", () => {
  assert.equal(immichStav({ stav: "nacitani" }), "Immich načítá fotky");
  assert.equal(immichStav({ stav: "rozpoznavani" }),
    "Rozpoznávání obličejů probíhá");
});

test("nenalezeno", () => {
  assert.equal(immichStav({ stav: "nenalezeno" }),
    "Immich fotky akce zatím nenašel");
});

test("rozpoznáno s datem (d. m. rrrr)", () => {
  const text = immichStav({ stav: "rozpoznano",
    cas: "2026-10-17T12:34:56" });
  // Bez NBSP: porovnání odolné vůči variantám ICU.
  assert.match(text.replace(/\u00a0/g, " "),
    /^Obličeje rozpoznány \(17\. 10\. 2026\)$/);
});

test("rozpoznáno bez času", () => {
  assert.equal(immichStav({ stav: "rozpoznano" }), "Obličeje rozpoznány");
});

test("bez záznamu nebo s neznámým stavem prázdný text", () => {
  assert.equal(immichStav(null), "");
  assert.equal(immichStav({}), "");
  assert.equal(immichStav({ album: true }), "");   // zatím jen chyba
  assert.equal(immichStav({ stav: "cosi-noveho" }), "");
});
