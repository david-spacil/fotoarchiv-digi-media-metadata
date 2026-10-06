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

// `2026-04-28` → `út 28. 4. 2026`.
export function dayLabel(day) {
  const [y, m, d] = day.split("-").map(Number);
  const weekday = DNY[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  return `${weekday} ${d}. ${m}. ${y}`;
}
