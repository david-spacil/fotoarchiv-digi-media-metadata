// Odkaz na objekt OpenStreetMap, ze kterého jsou souřadnice místa
// (klíč `osm` v `souradnice_mist`; čistá funkce, testy
// v tests/js/osm.test.mjs).

const OSM_OBJECT = /^(node|way|relation)\/[1-9]\d*$/;

// URL objektu, nebo null pro chybějící či neplatnou hodnotu
// (např. `None/None` ze staré cache geokódování).
export function osmUrl(osm) {
  return typeof osm === "string" && OSM_OBJECT.test(osm)
    ? `https://www.openstreetmap.org/${osm}` : null;
}
