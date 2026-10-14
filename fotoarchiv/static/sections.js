// Rozvržení plochy podle data: oddíly po kalendářních dnech.
// Datum je `RRRR-MM-DD` nebo `RRRR-MM-DDTHH:MM[:SS]`; prázdno = bez data.

// Pevně, ne Intl: výsledek nezávisí na ICU prohlížeče ani Node.
const DNY = ["ne", "po", "út", "st", "čt", "pá", "so"];

// Oddíly `{ day, files }` podle dne, vzestupně; uvnitř dne podle hodnoty
// data (den bez času před časy), při shodě podle názvu. Soubory bez data
// na konci v oddílu `day: null`.
export function byDay(files, dateOf) {
  const days = new Map();
  const none = [];
  for (const f of files) {
    const value = dateOf(f) || "";
    const day = value.slice(0, 10);
    if (!day) {
      none.push(f);
      continue;
    }
    if (!days.has(day)) days.set(day, []);
    days.get(day).push([value, f]);
  }
  const byValue = (a, b) =>
    a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1].localeCompare(b[1]);
  const result = [...days.keys()].sort().map((day) => ({
    day, files: days.get(day).sort(byValue).map(([, f]) => f),
  }));
  if (none.length) {
    result.push({ day: null, files: none.sort((a, b) => a.localeCompare(b)) });
  }
  return result;
}

// Barvy osob: klíč jména → index podle seřazených klíčů. `keyOf`
// sjednotí zápisy téže osoby (bez diakritiky, velikosti písmen
// a pořadí slov).
export function personIndex(names, keyOf) {
  const keys = [...new Set(names.map(keyOf).filter(Boolean))].sort();
  return new Map(keys.map((k, i) => [k, i]));
}

// Zarážky `linear-gradient` pro stejně dlouhé úseky barev; nad `max`
// barev zbytek jako jeden šedý úsek.
export const REST_COLOR = "#a0aec0";

export function stripeStops(colors, max = 3) {
  const shown = colors.length > max
    ? [...colors.slice(0, max), REST_COLOR] : colors;
  const pct = (i) => `${+(i * 100 / shown.length).toFixed(2)}%`;
  return shown.map((c, i) => `${c} ${pct(i)} ${pct(i + 1)}`).join(", ");
}

// `2026-04-28` → `út 28. 4. 2026`.
export function dayLabel(day) {
  const [y, m, d] = day.split("-").map(Number);
  const weekday = DNY[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  return `${weekday} ${d}. ${m}. ${y}`;
}

// Chybějící údaje a autoři oddílu pro navigátor: průnik výsledku
// `missing()` (inherit.js) se soubory oddílu, v pořadí oddílu. Oddíl
// `{ gid, key, files }` má klíč `g:<skupina>` (`g:` = bez skupiny)
// v zobrazení po skupinách, `d:<den>` (`d:` = bez data) podle data.
// `authorsOf(f)` = výslední autoři souboru, `keyOf` sjednotí zápisy
// téže osoby, `counted(f)` = soubor se počítá (v kořeni, ne k vyřazení).
// Bez skupiny jen podle data, bez data ne v oddílu „Bez data“.
export function sectionInfo(sec, m, { authorsOf, keyOf, counted }) {
  const files = sec.files.filter(counted);
  const pick = (list) => {
    const set = new Set(list);
    return files.filter((f) => set.has(f));
  };
  const byDate = sec.key.startsWith("d:");
  const people = new Map();
  const bezAutoru = [];
  for (const f of files) {
    const names = authorsOf(f);
    if (!names.length) bezAutoru.push(f);
    for (const k of new Set(names.map(keyOf).filter(Boolean))) {
      if (!people.has(k)) {
        people.set(k, { key: k, name: names.find((n) => keyOf(n) === k),
          count: 0 });
      }
      people.get(k).count++;
    }
  }
  return {
    bezAutoru,
    bezData: sec.key === "d:" ? [] : pick(m.souboryBezData),
    bezMista: pick(m.souboryBezMista),
    bezSkupiny: byDate ? pick(m.souboryBezSkupiny) : [],
    skupinaBezAutoru: !!sec.gid && m.skupinyBezAutoru.includes(sec.gid),
    // Nejčastější první, při shodě podle klíče (stálé pořadí).
    autori: [...people.values()].sort((a, b) =>
      b.count - a.count || a.key.localeCompare(b.key)),
  };
}

// Úseky pruhu autorů oddílu `{ color, count, names }` v poměru počtu
// souborů: nejvýš `max` nejčastějších barevně, ostatní jedním šedým
// úsekem, soubory bez autorů na konci s `color: null` (šrafování).
export function stripeSegments(autori, noAuthors, colorOf, max = 3) {
  const result = autori.slice(0, max).map((p) =>
    ({ color: colorOf(p.key), count: p.count, names: [p.name] }));
  const rest = autori.slice(max);
  if (rest.length) {
    result.push({ color: REST_COLOR,
      count: rest.reduce((n, p) => n + p.count, 0),
      names: rest.map((p) => p.name) });
  }
  if (noAuthors) result.push({ color: null, count: noAuthors, names: [] });
  return result;
}
