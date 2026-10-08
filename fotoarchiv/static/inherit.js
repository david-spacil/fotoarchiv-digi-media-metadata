// Dědění akce → skupina → soubor a chybějící údaje.
//
// Stejný výpočet má server ve `fotoarchiv/model.py`; obě implementace se
// ověřují proti fixturám v `tests/fixtures/inheritance/` (JS přes
// `node --test tests/js`).

// Klíče, které patří jen své úrovni a nedědí se. `obliceje` (jen
// u souboru, zapisuje synchronizace z Immiche) a starší `osoby` se do
// výsledných hodnot nedostanou na žádné úrovni.
export const LOCAL_KEYS = {
  // Účastníci a místa akce jsou výčty pro celou akci, ne údaje každé
  // fotky. Jediné místo akce se ale jako `misto` dědí (viz collect).
  // `overeno` je ruční potvrzení integrity u konkrétního souboru
  // (issue #10) — nikdy se nedění ani nedostane do výstupů.
  akce: new Set(["ucastnici", "mista", "obliceje", "osoby"]),
  skupina: new Set(["nazev", "obliceje", "osoby"]),
  soubor: new Set(["skupina", "sha256", "obliceje", "osoby", "overeno"]),
};

// `levels` začíná vždy akcí. `misto` se z akce dědí, jen když má akce
// v `mista` právě jedno místo.
function collect(levels) {
  const result = {};
  const mista = levels[0][1]?.mista || [];
  if (mista.length === 1) {
    result.misto = { hodnota: mista[0], uroven: "akce" };
  }
  for (const [level, values] of levels) {
    for (const [key, value] of Object.entries(values || {})) {
      if (LOCAL_KEYS[level].has(key)) continue;
      result[key] = { hodnota: value, uroven: level };
    }
  }
  return result;
}

// Výsledné hodnoty polí souboru s úrovní, odkud pocházejí. Bez vlastního
// či zděděného `gps` se bere `gps` z `souradnice_mist` výsledného místa,
// s úrovní `misto`.
export function resolve(doc, filename) {
  const record = (doc.soubory || {})[filename] || {};
  const group = (doc.skupiny || {})[record.skupina] || {};
  const result = collect([
    ["akce", doc.akce],
    ["skupina", group],
    ["soubor", record],
  ]);
  const gps = placeGps(doc, result);
  if (gps) result.gps = { hodnota: gps, uroven: "misto" };
  return result;
}

// GPS z `souradnice_mist`, jen pokud soubor nemá žádné vlastní.
function placeGps(doc, result) {
  if (result.gps?.hodnota) return null;
  const misto = result.misto?.hodnota;
  if (!misto) return null;
  return (doc.souradnice_mist || {})[misto]?.gps || null;
}

// Výsledné hodnoty polí skupiny (zděděné z akce).
export function resolveGroup(doc, groupId) {
  return collect([
    ["akce", doc.akce],
    ["skupina", (doc.skupiny || {})[groupId]],
  ]);
}

function isEmpty(value) {
  return value === undefined || value === null || value === "" ||
    (Array.isArray(value) && value.length === 0);
}

// Co chybí: akce bez názvu nebo data, skupiny bez autorů (a ne všechny
// jejich soubory autory přepisují), soubory bez data, bez skupiny a bez
// místa (jen když má akce víc míst — jedno místo se dědí) a místa bez
// rozhodnutých souřadnic (`mistaBezSouradnic`: místo → soubory bez GPS).
// `present` = názvy souborů, které v kořeni akce skutečně jsou. Soubory
// označené k vyřazení (`vyradit`) se nepočítají; skupina, jejíž všechny
// soubory jsou označené, tak nechybí ani autorům.
export function missing(doc, present) {
  const akce = doc.akce || {};
  const result = {
    akce: ["nazev", "datum_od", "datum_do"].filter((k) => isEmpty(akce[k])),
    skupinyBezAutoru: [],
    souboryBezData: [],
    souboryBezSkupiny: [],
    souboryBezMista: [],
    mistaBezSouradnic: {},
  };
  const souradnice = doc.souradnice_mist || {};
  const viceMist = (akce.mista || []).length > 1;
  const groups = doc.skupiny || {};
  const files = Object.keys(doc.soubory || {})
    .filter((f) => (!present || present.has(f)) && !doc.soubory[f].vyradit);
  for (const gid of Object.keys(groups)) {
    if (!isEmpty(resolveGroup(doc, gid).autori?.hodnota)) continue;
    const own = files.filter((f) => doc.soubory[f].skupina === gid);
    if (own.length && own.some((f) => isEmpty(doc.soubory[f].autori))) {
      result.skupinyBezAutoru.push(gid);
    }
  }
  for (const f of files) {
    const record = doc.soubory[f];
    const fields = resolve(doc, f);
    if (isEmpty(fields.datum?.hodnota)) {
      result.souboryBezData.push(f);
    }
    if (!record.skupina || !groups[record.skupina]) {
      result.souboryBezSkupiny.push(f);
    }
    if (viceMist && isEmpty(fields.misto?.hodnota)) {
      result.souboryBezMista.push(f);
    }
    const misto = fields.misto?.hodnota;
    if (!isEmpty(misto) && !Object.hasOwn(souradnice, misto) &&
        isEmpty(fields.gps?.hodnota)) {
      (result.mistaBezSouradnic[misto] ||= []).push(f);
    }
  }
  return result;
}
