// Rámečky obličejů v lupě a jména osob ve formuláři (čisté funkce,
// testy v tests/js/obliceje.test.mjs).

// `oblast` [x, y, w, h] (střed a velikost, podíly otočené fotky) →
// styl rámečku v procentech obalu s rozměrem fotky.
export function ramecek(oblast) {
  const [x, y, w, h] = oblast;
  const pct = (v) => `${+(v * 100).toFixed(2)}%`;
  return { left: pct(x - w / 2), top: pct(y - h / 2),
    width: pct(w), height: pct(h) };
}

// Jména z `obliceje` vybraných souborů: `naFotce` jsou na aktuální
// fotce (`aktualni`, null = všechna), `ostatni` jen na jiných
// vybraných. Obě seřazená česky, bez opakování.
export function jmenaOsob(soubory, vybrane, aktualni) {
  const jmena = (f) => (soubory[f]?.obliceje || []).map((o) => o.jmeno);
  const vse = new Set(vybrane.flatMap(jmena));
  const tady = aktualni == null ? vse : new Set(jmena(aktualni));
  const serad = (a) => a.sort((p, q) => p.localeCompare(q, "cs"));
  return {
    naFotce: serad([...vse].filter((j) => tady.has(j))),
    ostatni: serad([...vse].filter((j) => !tady.has(j))),
  };
}
