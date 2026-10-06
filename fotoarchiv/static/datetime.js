// Datum pořízení po částech: den `RRRR-MM-DD` a čas `HH:MM[:SS]`.
// Hodnota je `RRRR-MM-DD` nebo `RRRR-MM-DDTHH:MM[:SS]`; prázdno = nezadáno.

const dayOf = (v) => (v || "").slice(0, 10);
const timeOf = (v) => (v || "").slice(11);

// Nový den, čas zůstane. Prázdný den smaže celou hodnotu.
export function withDay(value, day) {
  if (!day) return "";
  const time = timeOf(value);
  return time ? `${day}T${time}` : day;
}

// Nový čas, den zůstane. Prázdný čas nechá jen den; bez dne nic.
export function withTime(value, time) {
  const day = dayOf(value);
  if (!day) return value || "";
  return time ? `${day}T${time}` : day;
}

// Společný den a čas hodnot výběru (jinak prázdno) a zda se liší.
export function parts(values) {
  const days = new Set(values.map(dayOf));
  const times = new Set(values.map(timeOf));
  return {
    day: days.size === 1 ? [...days][0] : "",
    time: times.size === 1 ? [...times][0] : "",
    mixed: days.size > 1 || times.size > 1,
  };
}
