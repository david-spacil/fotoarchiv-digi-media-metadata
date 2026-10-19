// Odkaz na objekt OSM u místa (scénáře ze specifikace place-geocoding,
// „Odkaz na objekt OSM“).
import { test } from "node:test";
import assert from "node:assert/strict";

import { osmUrl } from "../../fotoarchiv/static/osm.js";

test("platné typy objektů", () => {
  assert.equal(osmUrl("relation/439179"),
    "https://www.openstreetmap.org/relation/439179");
  assert.equal(osmUrl("way/12"), "https://www.openstreetmap.org/way/12");
  assert.equal(osmUrl("node/7"), "https://www.openstreetmap.org/node/7");
});

test("chybějící hodnota bez odkazu", () => {
  for (const v of [undefined, null, "", 439179]) {
    assert.equal(osmUrl(v), null);
  }
});

test("neplatná hodnota bez odkazu", () => {
  for (const v of ["None/None", "relation/0", "relation/12a",
    "relation/../x", "area/1", "relation/", "/1", "relation/1/",
    " relation/1", "relation/1\n", "Relation/1",
    "javascript:alert(1)//relation/1"]) {
    assert.equal(osmUrl(v), null, v);
  }
});
