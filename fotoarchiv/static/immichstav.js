// Text stavu akce v Immichi ze záznamu `.work/immich-alba.json`
// ({stav, cas}) — tabulka stavů viz design změny pojmenovani-osob.
// Bez záznamu, bez stavu nebo s neznámým stavem prázdný text: stav se
// nezobrazuje (např. bez nastaveného Immiche).

const DATUM = { day: "numeric", month: "numeric", year: "numeric" };

export function immichStav(polozka) {
  if (!polozka || !polozka.stav) return "";
  switch (polozka.stav) {
    case "nacitani":
      return "Immich načítá fotky";
    case "rozpoznavani":
      return "Rozpoznávání obličejů probíhá";
    case "nenalezeno":
      return "Immich fotky akce zatím nenašel";
    case "rozpoznano": {
      // `cas` je ISO čas zápisu stavu; datum formátem d. m. rrrr.
      const datum = polozka.cas
        ? new Date(polozka.cas).toLocaleDateString("cs", DATUM) : "";
      return datum ? `Obličeje rozpoznány (${datum})`
        : "Obličeje rozpoznány";
    }
    default:
      return "";
  }
}
