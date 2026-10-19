// Smazání akce do koše: potvrzení opsáním názvu a důvod (scénáře ze
// specifikace event-trash, „Potvrzení smazání“ a „Stránka Koš“).
import { test } from "node:test";
import assert from "node:assert/strict";

import { lzeSmazat, nazevSedi, zbyvaText } from "../../fotoarchiv/static/kos.js";

const NAZEV = "2026-04-28 kontrola Stezky";

test("opsaný název musí sedět přesně", () => {
  assert.ok(nazevSedi(NAZEV, NAZEV));
  assert.ok(nazevSedi(`  ${NAZEV} `, NAZEV));
  assert.ok(nazevSedi("2026-03-14 výzkum Hradisko".normalize("NFD"),
    "2026-03-14 výzkum Hradisko"));
  assert.ok(!nazevSedi("2026-04-28 Kontrola Stezky", NAZEV));
  assert.ok(!nazevSedi("2026-04-28 kontrola", NAZEV));
  assert.ok(!nazevSedi("", NAZEV));
  assert.ok(!nazevSedi(undefined, NAZEV));
});

test("smazání potřebuje i důvod", () => {
  assert.ok(lzeSmazat(NAZEV, NAZEV, "duplicita"));
  assert.ok(!lzeSmazat(NAZEV, NAZEV, "   "));
  assert.ok(!lzeSmazat(NAZEV, NAZEV, ""));
  assert.ok(!lzeSmazat("jiná akce", NAZEV, "duplicita"));
});

test("zbývající dny do trvalého smazání", () => {
  assert.equal(zbyvaText(7), "za 7 dní");
  assert.equal(zbyvaText(5), "za 5 dní");
  assert.equal(zbyvaText(2), "za 2 dny");
  assert.equal(zbyvaText(1), "za 1 den");
  assert.equal(zbyvaText(0), "při nejbližším vysypání");
});
