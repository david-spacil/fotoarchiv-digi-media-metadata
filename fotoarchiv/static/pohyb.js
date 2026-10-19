// Klávesy a cíle klávesnicového pohybu v mřížce dlaždic, počítané
// z jejich obdélníků (čisté funkce, testy v tests/js/pohyb.test.mjs).

// Řádky se liší podle `top`; tolerance 1 px pokryje subpixely flexu.
const TOLERANCE = 1;

// Pohybové klávesy: key → [druh, smer].
const POHYB = {
  ArrowLeft: ["vodorovne", -1], ArrowRight: ["vodorovne", 1],
  ArrowUp: ["svisle", -1], ArrowDown: ["svisle", 1],
  PageUp: ["stranka", -1], PageDown: ["stranka", 1],
  Home: ["kraj", -1], End: ["kraj", 1],
};

// Rozhodnutí pro klávesu: { druh, smer, rozsir } nebo null, aby
// nepřebírala zkratky prohlížeče ani ostatních komponent.
export function klavesa(e) {
  const pohyb = POHYB[e.key];
  if (pohyb) {
    if (e.ctrlKey || e.metaKey || e.altKey) return null;
    return { druh: pohyb[0], smer: pohyb[1], rozsir: !!e.shiftKey };
  }
  if ((e.key === "a" || e.key === "A") && !e.altKey &&
      (e.ctrlKey || e.metaKey)) {
    return { druh: "vse", smer: 0, rozsir: false };
  }
  return null;
}

const stred = (r) => r.left + r.width / 2;

// Hranice řádků: setříděné hodnoty `top`; do vzdálenosti tolerance
// splývají v jeden řádek.
function rady(rects) {
  const topy = [...new Set(rects.map((r) => r.top))]
    .sort((a, b) => a - b);
  const vysledek = [];
  for (const t of topy) {
    if (!vysledek.length ||
        t - vysledek[vysledek.length - 1] > TOLERANCE) {
      vysledek.push(t);
    }
  }
  return vysledek;
}

// Index řádku v `rady` pro obdélník (nejbližší hranice).
function indexRadu(r, rady) {
  let best = 0;
  for (let a = 1; a < rady.length; a++) {
    if (Math.abs(r.top - rady[a]) < Math.abs(r.top - rady[best])) best = a;
  }
  return best;
}

// Index dlaždice v řádku `ri` s nejbližším vodorovným středem k `r0`;
// při stejné vzdálenosti levější. Vrací -1, když řádek nemá dlaždici.
function nejblizsiVRadu(rects, rady, ri, r0) {
  let best = -1, bestD = Infinity;
  for (let j = 0; j < rects.length; j++) {
    const r = rects[j];
    if (Math.abs(r.top - rady[ri]) > TOLERANCE) continue;
    const d = Math.abs(stred(r) - stred(r0));
    const blize = d < bestD ||
      (d === bestD && r.left < rects[best].left);
    if (blize) {
      best = j;
      bestD = d;
    }
  }
  return best;
}

// Šipka nahoru/dolů: dlaždice v nejbližším řádku nad (smer -1) / pod
// (+1); bez takového řádku vrátí `i`. Předěl oddílu je jen větší
// rozestup, takže nepotřebuje zvláštní případ.
export function radek(rects, i, smer) {
  const r = rady(rects);
  const ri = indexRadu(rects[i], r);
  const cil = ri + smer;
  if (cil < 0 || cil >= r.length) return i;
  const j = nejblizsiVRadu(rects, r, cil, rects[i]);
  return j === -1 ? i : j;
}

// PageUp/PageDown: první řádek ve směru, jehož `top` je aspoň o `vyska`
// dál (s tolerancí), jinak krajní řádek; v něm nejbližší sloupec.
// Je-li výchozí řádek sám krajní ve směru, vrátí `i`.
export function stranka(rects, i, smer, vyska) {
  const r = rady(rects);
  const ri = indexRadu(rects[i], r);
  if ((smer === 1 && ri === r.length - 1) || (smer === -1 && ri === 0)) {
    return i;
  }
  let cil = -1;
  for (let x = ri + smer; x >= 0 && x < r.length; x += smer) {
    if (Math.abs(r[x] - r[ri]) >= vyska - TOLERANCE) {
      cil = x;
      break;
    }
  }
  if (cil === -1) cil = smer === 1 ? r.length - 1 : 0;
  const j = nejblizsiVRadu(rects, r, cil, rects[i]);
  return j === -1 ? i : j;
}

// Sipka v lupě po oddílech. smer +1: začátek dalšího oddílu za `i`,
// když žádný není, `i`. smer -1: začátek vlastního oddílu, ze jeho
// začátku začátek předchozího; bez předchozího (i = 0) vrátí `i`.
export function oddil(order, secOf, i, smer) {
  const sek = (j) => secOf.get(order[j]);
  if (smer === 1) {
    for (let j = i + 1; j < order.length; j++) {
      if (sek(j) !== sek(i)) return j;
    }
    return i;
  }
  let start = i;
  while (start > 0 && sek(start - 1) === sek(i)) start--;
  if (start < i) return start;
  if (i === 0) return i;
  let pred = i - 1;
  while (pred > 0 && sek(pred - 1) === sek(i - 1)) pred--;
  return pred;
}

// Počet dlaždic vejdoucích na šířku pásu, nejméně jedna; neplatné
// rozměry (nula, zápor, nečíslo) znamenají jednu.
export function naPas(sirkaPasu, sirkaDlazdice) {
  if (!Number.isFinite(sirkaPasu) || !Number.isFinite(sirkaDlazdice) ||
      sirkaDlazdice <= 0) return 1;
  return Math.max(1, Math.floor(sirkaPasu / sirkaDlazdice));
}
