// Kontrola poškozených souborů v průvodci importem (issue #10): co ještě
// zkontrolovat, souhrn a seznam poškozených z přehledu importu
// (`soubory[].kontrola`, `povolene_poskozene`).

export const STAV_KONTROLY = {
  ok: "v pořádku",
  podezrely: "podezřelý",
  necitelny: "nečitelný",
};

const checkable = (f) => f.typ !== "nepodporovany";

// Podporované soubory bez výsledku kontroly (nezkontrolované nebo změněné).
export function unchecked(soubory) {
  return soubory.filter((f) => checkable(f) && !f.kontrola);
}

// Počty podle stavu kontroly: { ok, podezrely, necitelny, nezkontrolovano }.
export function checkCounts(soubory) {
  const c = { ok: 0, podezrely: 0, necitelny: 0, nezkontrolovano: 0 };
  for (const f of soubory.filter(checkable)) {
    c[f.kontrola ? f.kontrola.stav : "nezkontrolovano"]++;
  }
  return c;
}

// Poškozené soubory s důvodem a tím, zda se přenesou: nečitelný nikdy,
// podezřelý jen povolený (stejně jako `Imports._damaged` na serveru).
export function damagedFiles(soubory, povolene = []) {
  const allowed = new Set(povolene);
  return soubory
    .filter((f) => checkable(f) && f.kontrola && f.kontrola.stav !== "ok")
    .map((f) => ({
      cesta: f.cesta,
      stav: f.kontrola.stav,
      duvod: f.kontrola.duvody.join("; "),
      povoleno: f.kontrola.stav === "podezrely" && allowed.has(f.cesta),
    }));
}

// Nový seznam povolených po přepnutí volby „přesto importovat“.
export function toggleAllowed(povolene, cesta, on) {
  const set = new Set(povolene);
  if (on) set.add(cesta);
  else set.delete(cesta);
  return [...set].sort();
}

// Souhrn `poskozene` z detailu akce omezený na aktuální dokument:
// soubory s `overeno` nebo `vyradit` se vyřadí (stejná pravidla jako
// `integrity.summary` na serveru), aby přepnutí přepínačů svítilo
// hned po uložení, než server odpověď spočítá znovu.
export function damagedMap(poskozene, soubory = {}) {
  const out = {};
  for (const [name, info] of Object.entries(poskozene || {})) {
    const record = soubory[name] || {};
    if (record.overeno || record.vyradit) continue;
    out[name] = info;
  }
  return out;
}

// Text dlaždice/tooltipu: stav + důvody kontroly.
export function damagedText(info) {
  const duvody = (info.duvody || []).join("; ");
  const stav = STAV_KONTROLY[info.stav] || info.stav;
  return duvody ? `${stav}: ${duvody}` : stav;
}
