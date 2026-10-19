// Vyloučení z importu (krok skupiny a autoři): množina vyloučených cest
// ve výběru importu (`vyloucene` v `import.json`), přepínání nad výběrem,
// páry fotka–RAW a počty. Cesty jsou `cesta` záznamů importu, RAWy
// `raw` z `POST /api/import/<id>/skupiny` (RAWy posledního plánu).

// Klíč páru: cesta bez přípony, bez ohledu na velikost písmen
// (`DSC/P1503712.JPG` ↔ `DSC/P1503712.RW2`).
export function pairKey(cesta) {
  const dot = cesta.lastIndexOf(".");
  const base = dot > cesta.lastIndexOf("/") ? cesta.slice(0, dot) : cesta;
  return base.toLowerCase();
}

// RAWy (z `raws`) se stejným klíčem jako některé z médií `media`.
export function pairedRaws(media, raws) {
  const keys = new Set(media.map(pairKey));
  return raws.filter((r) => keys.has(pairKey(r)));
}

// Co udělá Del nad vybranými médii `selected`: jsou-li všechna vyloučená,
// vrátí je (`exclude` false) i s jejich vyloučenými RAWy; jinak vyloučí
// všechna a `raws` jsou jejich dosud nevyloučené RAWy (na ty se průvodce
// zeptá).
export function planToggle(excluded, selected, raws) {
  const exclude = !selected.every((c) => excluded.has(c));
  const paired = pairedRaws(selected, raws);
  return { exclude,
    raws: paired.filter((r) => excluded.has(r) !== exclude) };
}

// Nová množina vyloučených po přepnutí; `raws` = RAWy, které jdou spolu
// s médii (při vyloučení jen ty, které uživatel zvolil).
export function applyToggle(excluded, selected, exclude, raws = []) {
  const result = new Set(excluded);
  for (const c of [...selected, ...raws]) {
    if (exclude) result.add(c);
    else result.delete(c);
  }
  return result;
}

// Operace plánu podle aktuálního vyloučení klienta: `ok` vyloučené cesty
// je `vylouceny`, `vylouceny` už nevyloučené je zase `ok` (plán mohl
// vzniknout před poslední úpravou).
export function withExcluded(ops, excluded) {
  return ops.map((o) => {
    if (o.stav === "ok" && excluded.has(o.z)) {
      return { ...o, stav: "vylouceny", blocked: true,
        duvod: "vyloučeno z importu" };
    }
    if (o.stav === "vylouceny" && !excluded.has(o.z)) {
      return { ...o, stav: "ok", blocked: false, duvod: null };
    }
    return o;
  });
}

// Počet souborů, které Importovat přenese.
export function importCount(ops, excluded) {
  return withExcluded(ops, excluded).filter((o) => o.stav === "ok").length;
}

// Vyloučená média a RAWy (jen ty, které krok zná).
export function excludedCounts(excluded, media, raws) {
  return { media: media.filter((c) => excluded.has(c)).length,
    raw: raws.filter((c) => excluded.has(c)).length };
}
