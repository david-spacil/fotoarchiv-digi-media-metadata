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

// Souhrn `poskozene` z detailu omezený na soubory bez ručního potvrzení
// a bez označení k vyřazení — ať už příznak přišel ze serveru, nebo ho
// klient teprve chystá v rozepsaném dokumentu (`soubory`). Stejná
// pravidla jako `integrity.counted` na serveru.
export function damagedMap(poskozene, soubory = {}) {
  const out = {};
  for (const [name, info] of Object.entries(poskozene || {})) {
    const record = soubory[name] || {};
    if (info.overeno || info.vyradit || record.overeno || record.vyradit) {
      continue;
    }
    out[name] = info;
  }
  return out;
}

// Rozhodnutí řádků dialogu úklidu: {název: "vyradit" | "overeno" | null}.
// Výchozí je uložený stav — potvrzený „v pořádku“, označený k vyřazení,
// jinak bez rozhodnutí (soubor zůstane, jak je). Značky bere ze souhrnu
// serveru (`poskozene`) i z rozepsaného dokumentu (`soubory`).
export function cleanupDecisions(files, poskozene, soubory = {}) {
  const out = {};
  for (const f of files) {
    const info = poskozene?.[f] || {};
    const record = soubory[f] || {};
    out[f] = info.vyradit || record.vyradit ? "vyradit"
      : info.overeno || record.overeno ? "overeno" : null;
  }
  return out;
}

// Rozdíl rozhodnutí proti dokumentu: co při spuštění zapsat.
// `vyradit` = nově k vyřazení (přesune je úklid), `overeno` = nově
// potvrzené, `zrusit` = potvrzení zrušené (řádek odškrtnutý nebo
// přepnutý na vyřazení).
export function decisionChanges(decisions, soubory = {}) {
  const out = { vyradit: [], overeno: [], zrusit: [] };
  for (const [f, d] of Object.entries(decisions)) {
    const record = soubory[f] || {};
    if (d === "vyradit" && !record.vyradit) out.vyradit.push(f);
    if (d === "overeno" && !record.overeno) out.overeno.push(f);
    if (d !== "overeno" && record.overeno) out.zrusit.push(f);
  }
  for (const list of Object.values(out)) list.sort();
  return out;
}

// Zapíše změny z `decisionChanges` do `soubory` (vyřazení ruší
// potvrzení). Vrátí funkci, která vrátí záznamy do původního stavu —
// pro případ, že se uložení nepovede.
export function applyDecisionChanges(soubory, changes) {
  const touched = [...new Set([...changes.vyradit, ...changes.overeno,
    ...changes.zrusit])];
  const before = Object.fromEntries(touched.map((f) => [f,
    soubory[f] === undefined ? undefined : { ...soubory[f] }]));
  for (const f of changes.zrusit) {
    if (soubory[f]) delete soubory[f].overeno;
  }
  for (const f of changes.vyradit) (soubory[f] ??= {}).vyradit = true;
  for (const f of changes.overeno) (soubory[f] ??= {}).overeno = true;
  return () => {
    for (const f of touched) {
      if (before[f] === undefined) delete soubory[f];
      else soubory[f] = before[f];
    }
  };
}

// Text dlaždice/tooltipu: stav + důvody kontroly.
export function damagedText(info) {
  const duvody = (info.duvody || []).join("; ");
  const stav = STAV_KONTROLY[info.stav] || info.stav;
  return duvody ? `${stav}: ${duvody}` : stav;
}
