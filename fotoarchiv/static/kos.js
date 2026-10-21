// Smazání akce do koše a stránka Koš (jen admin): potvrzení opsáním
// názvu a texty lhůty. Server porovnává opsaný název přesně; klient
// povolí potvrzení až při shodě a pošle název akce.

// Opsaný název odpovídá akci? Bez okrajových mezer a rozdílu NFC/NFD
// (macOS píše diakritiku rozloženě), jinak přesně včetně velikosti písmen.
export function nazevSedi(zadany, nazev) {
  return (zadany || "").trim().normalize("NFC") ===
    (nazev || "").normalize("NFC");
}

// Smazání jde potvrdit: opsaný název sedí a důvod není prázdný.
export function lzeSmazat(zadany, nazev, duvod) {
  return nazevSedi(zadany, nazev) && !!(duvod || "").trim();
}

// Kdy se akce z koše smaže natrvalo, podle `zbyva_dni` z `/api/kos`.
export function zbyvaText(dni) {
  if (dni <= 0) return "při nejbližším vysypání";
  if (dni === 1) return "za 1 den";
  if (dni < 5) return `za ${dni} dny`;
  return `za ${dni} dní`;
}
