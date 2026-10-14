## Why

Ve velké akci (stovky fotek, desítky skupin) se plocha prochází
posouváním mřížky: hlavičky skupin jsou mezi dlaždicemi a co kde
chybí, ukazuje jen souhrn v liště. Navazuje na archivované změny
`graficky-overhaul` (tokeny, jedna lišta akce, skládací panel)
a `import-a-popis`.

## What Changes

Odsouhlasený směr (varianta A z porovnání 2026-10-13, s dlaždicemi
s překryvem; informační architektura a řádek oddílu odsouhlaseny
2026-10-14 na prototypu s akcí DOD 2015):

- **Navigátor akce:** vlevo úzký sloupec.
  - Nahoře řádek **Akce**: klik zruší výběr (formulář upravuje akci);
    nese chybějící údaje, které nejdou rozpočítat na oddíly — akce bez
    názvu nebo data, místa bez souřadnic.
  - Pod ním **oddíly** (skupiny, nebo dny podle přepínače zobrazení):
    název, počet souborů, barvy autorů (jako pruh na dlaždici)
    a co v oddílu chybí (soubory bez data, bez místa, bez autorů;
    u skupiny i skupina bez autorů). Soubory bez skupiny jsou
    v zobrazení po skupinách vlastním oddílem.
  - Řádek oddílu (varianta „Řádek“ z prototypu): název a počet,
    pod nimi tenký pruh autorů v poměru jejich souborů a ikonky
    chybějících údajů s počtem.
  - Okrajem jsou označené všechny oddíly, které jsou v mřížce právě
    vidět.
  - Klik na skupinu vybere skupinu, klik na den vybere soubory dne
    (náhrada za klik na hlavičku v mřížce) a mřížka na oddíl skočí
    tak, že je vidět i předěl nad ním.
  - Tažení vybraných souborů na skupinu je přesune do skupiny; na den
    tažení nejde (měnilo by datum).
- **Mřížka bez hlaviček oddílů:** předěly mezi oddíly zůstanou, výběr
  oddílu jde přes navigátor.
- **Lišta akce** dál nese název akce, přepínače, Importovat, Dokončit
  akci, nálezy kontroly a počet k vyřazení; chybějící údaje se z ní
  přesunou do navigátoru.
- **Lupa:** navigátor slouží ke skoku — klik na oddíl udělá jeho první
  soubor aktuálním a jediným vybraným.
- **Dlaždice s překryvem:** bez popisků pod náhledem; stav, autoři
  a vyřazení jako překryv v rohu, název a datum při najetí. Hustší
  mřížka.
- Sada ikon (inline SVG) místo části textových tlačítek.

Mimo rozsah: formulář jako kaskáda dědění (vrstvy akce → skupina →
výběr pod sebou) — samostatná změna po této, staví na vrstvách
navigátoru. Přepínání mezi akcemi z plochy — nebude.

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `metadata-workspace`: nové požadavky Navigátor akce, Chybějící údaje
  v navigátoru, Místa bez souřadnic v navigátoru, Lišta akce, Přesun
  do skupiny tažením; upravené Mřížka a výběr, Formulář podle výběru,
  Zobrazení podle data, Značka autorů na dlaždici (překryv místo
  popisku), Dokončení akce a Osoby jen pro čtení (odkazy na lištu);
  vypuštěné Lišta chybějících údajů a Místa bez souřadnic v liště.
- `loupe-view`: navigátor v lupě jako skok na oddíl.
- `photo-import`: scénář importu odkazuje na navigátor místo lišty.

## Impact

- `fotoarchiv/static/app.js`, `style.css` (plocha, mřížka, lišta).
- `fotoarchiv/static/inherit.js` beze změny výpočtu — `missing()`
  vrací seznamy souborů, počty za oddíl jsou průnik.
- `README.md`, oddíl Aplikace.
- Server a datový model beze změny.
