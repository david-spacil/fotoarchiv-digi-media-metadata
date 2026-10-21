// Seznam akcí jako fronta práce: filtry, hledání a řazení nad výpisem
// `GET /api/akce` (čisté funkce, testy v tests/js/fronta.test.mjs).

export const POLE = ["autori", "datum", "misto"];

// Hledání ignoruje diakritiku a velikost písmen.
export function fold(text) {
  return (text || "").normalize("NFKD").replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

// Každé slovo dotazu musí být v názvu akce. Delším slovům se ořežou
// koncové samohlásky, aby „naucna“ našlo „Naučné“.
export function matchesSearch(nazev, query) {
  const name = fold(nazev);
  return fold(query).split(/\s+/).filter(Boolean)
    .map((word) => word.length > 3 ? word.replace(/[aeiouy]+$/, "") : word)
    .every((word) => name.includes(word));
}

// Hotovost všech polí úplná (akce bez metadat úplná není).
export function isComplete(e) {
  return !!e.hotovost && POLE.every((k) => {
    const [vyplneno, celkem] = e.hotovost[k];
    return vyplneno === celkem;
  });
}

const changedAfterExport = (e) => e.stav === "hotovo" &&
  e.zmeneno_po_exportu;

// Filtry v pořadí nabídky: [id, popisek, predikát(akce, jméno)].
export const FILTRY = [
  ["vse", "Vše", () => true],
  ["moje", "Moje rozpracované", (e, me) =>
    (e.stav === "rozpracovano" || changedAfterExport(e)) &&
    ((!!me && me in (e.upravili || {})) || !!e.drzitel?.vase)],
  ["dokoncit", "K dokončení", (e) =>
    (e.stav === "rozpracovano" && isComplete(e)) || changedAfterExport(e)],
  ["nezpracovane", "Nezpracované", (e) => e.stav === "nezpracovano"],
];

export function filterFn(id) {
  return (FILTRY.find(([f]) => f === id) || FILTRY[0])[2];
}

// Podíl vyplněných polí všech souborů; null u akce bez metadat.
export function ratio(e) {
  if (!e.hotovost) return null;
  let vyplneno = 0, celkem = 0;
  for (const k of POLE) {
    vyplneno += e.hotovost[k][0];
    celkem += e.hotovost[k][1];
  }
  return celkem ? vyplneno / celkem : 1;
}

// Nejnovější čas v `upravili` (ISO řetězce se řadí jako text).
export function lastEdit(e) {
  const times = Object.values(e.upravili || {}).sort();
  return times.length ? times[times.length - 1] : null;
}

// Název akce začíná datem, takže sestupně podle názvu = podle data.
const byDate = (a, b) => (a.nazev < b.nazev ? 1 : a.nazev > b.nazev ? -1 : 0);

// Řazení: [id, popisek, porovnání]; prázdné hodnoty vždy na konci.
export const RAZENI = [
  ["datum", "Podle data akce", byDate],
  ["hotovost", "Podle hotovosti", (a, b) => {
    const ra = ratio(a), rb = ratio(b);
    if (ra === null || rb === null) {
      return (ra === null) - (rb === null) || byDate(a, b);
    }
    return ra - rb || byDate(a, b);
  }],
  ["uprava", "Podle poslední úpravy", (a, b) => {
    const la = lastEdit(a), lb = lastEdit(b);
    if (!la || !lb) return (!la) - (!lb) || byDate(a, b);
    return (la < lb ? 1 : la > lb ? -1 : 0) || byDate(a, b);
  }],
  ["velikost", "Podle velikosti", (a, b) => {
    const va = a.bajtu ?? null, vb = b.bajtu ?? null;
    if (va === null || vb === null) {
      return (va === null) - (vb === null) || byDate(a, b);
    }
    return vb - va || byDate(a, b);
  }],
];

// Velikost v desítkových jednotkách s desetinnou čárkou (4,2 GB).
export function fmtSize(n) {
  const units = ["B", "kB", "MB", "GB", "TB"];
  let i = 0;
  while (n >= 1000 && i < units.length - 1) { n /= 1000; i++; }
  return `${n.toLocaleString("cs", { maximumFractionDigits: i ? 1 : 0 })} ` +
    units[i];
}

// Řádek součtu z `GET /api/velikost`; prázdný koš bez závorky.
export function celkemText(akce, kos) {
  return `Celkem ${fmtSize(akce || 0)}` +
    (kos ? ` (+${fmtSize(kos)} v koši)` : "");
}

// Akce podle filtru, hledání a řazení; `me` = jméno uživatele.
export function visibleEvents(events, view, me) {
  const keep = filterFn(view.filtr);
  const cmp = (RAZENI.find(([r]) => r === view.razeni) || RAZENI[0])[2];
  return events.filter((e) => keep(e, me) &&
    matchesSearch(e.nazev, view.hledat)).sort(cmp);
}

// Počty akcí pro každý filtr (s hledáním).
export function filterCounts(events, view, me) {
  const found = events.filter((e) => matchesSearch(e.nazev, view.hledat));
  return Object.fromEntries(FILTRY.map(([id, , fn]) =>
    [id, found.filter((e) => fn(e, me)).length]));
}

// Stav seznamu v hash adrese `#/?filtr=…&hledat=…&razeni=…`;
// výchozí hodnoty se do adresy nepíšou.
export const DEFAULT_VIEW = { filtr: "vse", hledat: "", razeni: "datum" };

export function parseListHash(hash) {
  const q = new URLSearchParams((hash || "").replace(/^#\/?\??/, ""));
  const pick = (key, list) => list.some(([id]) => id === q.get(key))
    ? q.get(key) : DEFAULT_VIEW[key];
  return { filtr: pick("filtr", FILTRY), hledat: q.get("hledat") || "",
    razeni: pick("razeni", RAZENI) };
}

export function listHash(view) {
  const q = new URLSearchParams();
  for (const key of ["filtr", "hledat", "razeni"]) {
    if (view[key] && view[key] !== DEFAULT_VIEW[key]) q.set(key, view[key]);
  }
  const s = q.toString();
  return s ? `#/?${s}` : "#/";
}
