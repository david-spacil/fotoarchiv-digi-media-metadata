// Popis importu: dokument ve tvaru `_metadata.json` (`akce`, `skupiny`,
// `soubory: {název: {skupina}}`) plus `pripojit` (nová skupina →
// existující skupina cíle) a pracovní klíče klienta: `cil` (pro který cíl
// jsou skupiny sestavené), `typ` (`akce` nese údaje nové akce, nebo jen
// autory stávající), `nova_akce` (odložené údaje nové akce) a `upraveno`.
// Server zapíše při provedení jen nové skupiny s přenesenými soubory
// (`importer.describe`); existující skupiny cíle jsou v popisu jen kopie
// ke čtení a dědění.
//
// `defaults` = odpověď `POST /api/import/<id>/skupiny`: výchozí rozdělení
// (`skupiny`, `prirazeni`) přenášených médií `soubory` a skupiny cíle
// `existujici`.

import { missing } from "./inherit.js";

// Klíč cíle popisu: nová akce, nebo název stávající.
export function targetKey(defaults) {
  return defaults.nova ? "nova" : defaults.cil;
}

// Nový popis z výchozího rozdělení. `popis` = dosavadní popis (údaje
// nové akce z kroku cíl); skupiny a přiřazení se sestaví znovu.
export function freshDescription(defaults, popis) {
  const old = popis || {};
  const result = {
    cil: targetKey(defaults),
    typ: null,
    akce: {},
    skupiny: { ...structuredClone(defaults.existujici || {}),
      ...structuredClone(defaults.skupiny) },
    soubory: {},
    pripojit: {},
    upraveno: false,
  };
  if (defaults.nova) {
    result.typ = "nova";
    result.akce = structuredClone(old.typ === "nova" ? old.akce
      : old.nova_akce || {});
  } else {
    result.typ = "stavajici";
    const nova = old.typ === "nova" ? old.akce : old.nova_akce;
    if (nova) result.nova_akce = nova;
    const autori = defaults.akce_autori || [];
    if (autori.length) result.akce.autori = [...autori];
  }
  for (const f of defaults.soubory) {
    const gid = defaults.prirazeni[f.nazev];
    result.soubory[f.nazev] = gid ? { skupina: gid } : {};
  }
  return result;
}

// Sladění popisu s novým plánem: média, která se nepřenesou, vypadnou;
// nově přenášená dostanou skupinu z výchozího rozdělení; ruční úpravy
// ostatních zůstanou. Kopie existujících skupin se obnoví, připojení
// k zmizelé skupině se zruší. Mění `popis` na místě a vrací ho.
export function reconcile(popis, defaults) {
  const existing = defaults.existujici || {};
  const names = new Set(defaults.soubory.map((f) => f.nazev));
  for (const name of Object.keys(popis.soubory)) {
    if (!names.has(name)) delete popis.soubory[name];
  }
  for (const gid of Object.keys(existing)) {
    popis.skupiny[gid] = structuredClone(existing[gid]);
  }
  for (const f of defaults.soubory) {
    if (popis.soubory[f.nazev]) continue;
    const gid = defaults.prirazeni[f.nazev];
    if (gid && !popis.skupiny[gid]) {
      popis.skupiny[gid] = structuredClone(defaults.skupiny[gid]);
    }
    popis.soubory[f.nazev] = gid ? { skupina: gid } : {};
  }
  for (const [gid, target] of Object.entries(popis.pripojit)) {
    if (!existing[target] || !popis.skupiny[gid]) delete popis.pripojit[gid];
  }
  return popis;
}

// Popis, jak se zapíše: soubory připojených skupin patří do cílové
// skupiny (s jejími autory).
export function effectiveDoc(popis) {
  const doc = structuredClone(popis);
  for (const record of Object.values(doc.soubory)) {
    const target = popis.pripojit[record.skupina];
    if (target) record.skupina = target;
  }
  for (const gid of Object.keys(popis.pripojit)) delete doc.skupiny[gid];
  return doc;
}

// Skupiny přenášených médií bez autorů (ani zděděných z akce).
export function groupsWithoutAuthors(popis) {
  return missing(effectiveDoc(popis)).skupinyBezAutoru;
}
