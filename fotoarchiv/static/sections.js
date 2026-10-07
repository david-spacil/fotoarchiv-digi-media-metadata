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
