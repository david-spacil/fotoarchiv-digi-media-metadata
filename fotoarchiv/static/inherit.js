// Dědění akce → skupina → soubor a chybějící údaje.
//
// Stejný výpočet má server ve `fotoarchiv/model.py`; obě implementace se
// ověřují proti fixturám v `tests/fixtures/inheritance/` (JS přes
// `node --test tests/js`).

// Klíče, které patří jen své úrovni a nedědí se.
export const LOCAL_KEYS = {
  // Účastníci a místa akce jsou výčty pro celou akci, ne údaje každé
  // fotky. Jediné místo akce se ale jako `misto` dědí (viz collect).
  akce: new Set(["ucastnici", "mista"]),
  skupina: new Set(["nazev"]),
  soubor: new Set(["skupina", "sha256"]),
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

// Výsledné hodnoty polí souboru s úrovní, odkud pocházejí.
export function resolve(doc, filename) {
  const record = (doc.soubory || {})[filename] || {};
  const group = (doc.skupiny || {})[record.skupina] || {};
  return collect([
    ["akce", doc.akce],
    ["skupina", group],
    ["soubor", record],
  ]);
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
// místa (jen když má akce víc míst — jedno místo se dědí).
// `present` = názvy souborů, které v kořeni akce skutečně jsou.
export function missing(doc, present) {
  const akce = doc.akce || {};
  const result = {
    akce: ["nazev", "datum_od", "datum_do"].filter((k) => isEmpty(akce[k])),
    skupinyBezAutoru: [],
    souboryBezData: [],
    souboryBezSkupiny: [],
    souboryBezMista: [],
  };
  const viceMist = (akce.mista || []).length > 1;
  const groups = doc.skupiny || {};
  const files = Object.keys(doc.soubory || {})
    .filter((f) => !present || present.has(f));
  for (const gid of Object.keys(groups)) {
    if (!isEmpty(resolveGroup(doc, gid).autori?.hodnota)) continue;
    const own = files.filter((f) => doc.soubory[f].skupina === gid);
    if (own.length && own.some((f) => isEmpty(doc.soubory[f].autori))) {
      result.skupinyBezAutoru.push(gid);
    }
  }
  for (const f of files) {
    const record = doc.soubory[f];
    if (isEmpty(resolve(doc, f).datum?.hodnota)) {
      result.souboryBezData.push(f);
    }
    if (!record.skupina || !groups[record.skupina]) {
      result.souboryBezSkupiny.push(f);
    }
    if (viceMist && isEmpty(resolve(doc, f).misto?.hodnota)) {
      result.souboryBezMista.push(f);
    }
  }
  return result;
}
