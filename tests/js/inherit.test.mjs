// Dědění v JS proti stejným fixturám jako pytest (tests/test_model.py).
import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { missing, resolve } from "../../fotoarchiv/static/inherit.js";

const dir = join(import.meta.dirname, "..", "fixtures", "inheritance");

for (const name of readdirSync(dir).filter((n) => n.endsWith(".json"))) {
  test(`fixtura ${name}`, () => {
    const c = JSON.parse(readFileSync(join(dir, name), "utf8"));
    for (const [file, expected] of Object.entries(c.ocekavano)) {
      assert.deepEqual(resolve(c.metadata, file), expected);
    }
  });
}

test("skupina bez autorů", () => {
  const doc = {
    akce: { nazev: "x", datum_od: "2026-04-28", datum_do: "2026-04-28" },
    skupiny: { a: {}, b: { autori: ["Spáčil, David"] }, c: {} },
    soubory: {
      "1.jpg": { skupina: "a", datum: "2026-04-28" },
      "2.jpg": { skupina: "b" },
      "3.jpg": { skupina: "c", autori: ["Kopáčová, Zuzana"] },
      "4.jpg": { skupina: "zmizela", datum: "2026-04-28" },
    },
  };
  assert.deepEqual(missing(doc), {
    akce: [],
    skupinyBezAutoru: ["a"],
    souboryBezData: ["2.jpg", "3.jpg"],
    souboryBezSkupiny: ["4.jpg"],
    souboryBezMista: [],
  });
});

test("soubory bez místa jen při víc místech akce", () => {
  const doc = (mista) => ({
    akce: { mista },
    skupiny: {},
    soubory: { "a.jpg": {}, "b.jpg": { misto: "Housko" } },
  });
  assert.deepEqual(missing(doc(["Holštejn"])).souboryBezMista, []);
  assert.deepEqual(missing(doc(["Molenburk", "Housko"])).souboryBezMista,
    ["a.jpg"]);
});
