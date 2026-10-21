// Rámečky obličejů a jména na aktuální fotce (změna ramecky-obliceju).
import { test } from "node:test";
import assert from "node:assert/strict";

import { jmenaOsob, ramecek } from "../../fotoarchiv/static/obliceje.js";

const face = (jmeno, oblast = [0.5, 0.5, 0.1, 0.1]) => ({ jmeno, oblast });

test("rámeček ze středu a velikosti", () => {
  assert.deepEqual(ramecek([0.5, 0.4, 0.1, 0.2]),
    { left: "45%", top: "30%", width: "10%", height: "20%" });
});

test("rámeček bez chyb zaokrouhlení", () => {
  assert.deepEqual(ramecek([0.2725, 0.432, 0.041, 0.0747]),
    { left: "25.2%", top: "39.47%", width: "4.1%", height: "7.47%" });
});

test("osoba na fotce dvakrát je jedno jméno", () => {
  const soubory = { "a.jpg": { obliceje: [face("Vzorný, Tomáš"),
    face("Vzorný, Tomáš", [0.2, 0.2, 0.1, 0.1])] } };
  assert.deepEqual(jmenaOsob(soubory, ["a.jpg"], "a.jpg"),
    { naFotce: ["Vzorný, Tomáš"], ostatni: [] });
});

test("výběr dvou fotek: jméno z druhé mezi ostatními", () => {
  const soubory = {
    "a.jpg": { obliceje: [face("Vzorný, Tomáš")] },
    "b.jpg": {
      obliceje: [face("Ukázková, Věra"), face("Vzorný, Tomáš")],
    },
  };
  assert.deepEqual(jmenaOsob(soubory, ["a.jpg", "b.jpg"], "a.jpg"),
    { naFotce: ["Vzorný, Tomáš"], ostatni: ["Ukázková, Věra"] });
});

test("bez aktuální fotky (mřížka) jsou všechna jména na fotce", () => {
  const soubory = {
    "a.jpg": { obliceje: [face("Vzorný, Tomáš")] },
    "b.jpg": { obliceje: [face("Ukázková, Věra")] },
  };
  assert.deepEqual(jmenaOsob(soubory, ["a.jpg", "b.jpg"], null),
    { naFotce: ["Ukázková, Věra", "Vzorný, Tomáš"], ostatni: [] });
});

test("soubor bez obliceje", () => {
  const soubory = { "a.jpg": {}, "b.jpg": { obliceje: [face("Čapek, Jan")] } };
  assert.deepEqual(jmenaOsob(soubory, ["a.jpg", "b.jpg"], "a.jpg"),
    { naFotce: [], ostatni: ["Čapek, Jan"] });
  assert.deepEqual(jmenaOsob(soubory, ["a.jpg"], "a.jpg"),
    { naFotce: [], ostatni: [] });
});
