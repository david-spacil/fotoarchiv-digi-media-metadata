# Spec Delta

## MODIFIED Requirements

### Requirement: Volba souřadnic místa
Pro každý název místa použitý jako výsledné `misto` některého souboru
bez vlastního GPS SHALL uživatel rozhodnout o souřadnicích: vybrat
kandidáta, zadat souřadnice ručně, nebo zvolit „bez souřadnic“.
Rozhodnutí SHALL být uložené v `_metadata.json` akce v klíči
`souradnice_mist` (název → `{gps, popis[, osm]}`, nebo `null` pro „bez
souřadnic“) a platí pro všechny soubory akce s tímto místem. `osm` je
objekt OSM, ze kterého souřadnice pocházejí (`<typ>/<id>`); ukládá se
jen u kandidáta z Nominatimu, který ho má. Má-li
služba jediného kandidáta, SHALL se předvybrat; při víc kandidátech
SHALL být předvybraný ten nejbližší souborům akce, které mají GPS.
Předvýběr MUST uživatel potvrdit.

#### Scenario: Předvýběr podle GPS akce
- **WHEN** akce obsahuje fotky Samsung s GPS u Holštejna a u souboru
  bez GPS je místo `Vysočany`
- **THEN** předvybrané jsou Vysočany, okres Blansko

#### Scenario: Jedno rozhodnutí na akci
- **WHEN** uživatel potvrdí souřadnice pro `Vysočany` u jedné fotky
- **THEN** ostatní fotky akce s místem `Vysočany` mají stejné
  souřadnice bez dalšího dotazu

#### Scenario: Ruční souřadnice
- **WHEN** služba místo nenajde a uživatel zadá `49.4063, 16.7777`
- **THEN** místo má tyto souřadnice

#### Scenario: Kandidát s objektem OSM
- **WHEN** uživatel potvrdí kandidáta Holštejn, kterého Nominatim
  vrátil jako `relation` s id `439179`
- **THEN** `souradnice_mist["Holštejn"]` obsahuje `"osm":
  "relation/439179"` vedle `gps` a `popis`

#### Scenario: Kandidát bez objektu OSM
- **WHEN** Nominatim vrátí kandidáta bez typu nebo id objektu
- **THEN** kandidát ani uložené rozhodnutí klíč `osm` nemají

#### Scenario: Změna na ruční souřadnice
- **WHEN** místo má souřadnice kandidáta s `osm` a uživatel je změní
  na ručně zadané
- **THEN** uložené rozhodnutí už `osm` nemá

## ADDED Requirements

### Requirement: Odkaz na objekt OSM
U místa, jehož uložené rozhodnutí má `osm`, SHALL panel souřadnic
ukázat odkaz na `https://www.openstreetmap.org/<typ>/<id>`. Odkaz
SHALL mít i každý kandidát ve volbě souřadnic. Odkaz MUST se otevřít
v nové kartě, aby neuložené úpravy zůstaly. Odkaz SHALL vzniknout jen
z hodnoty ve tvaru `node`, `way` nebo `relation`, lomítko a kladné
celé číslo; jinak se neukáže a zbytek panelu funguje beze změny.
Ručně zadaná místa a místa bez souřadnic odkaz nemají.

#### Scenario: Uložené místo z Nominatimu
- **WHEN** vybrané fotky mají místo `Holštejn` s rozhodnutím
  `{"gps": […], "popis": "…", "osm": "relation/439179"}`
- **THEN** panel souřadnic místa ukazuje odkaz na
  `https://www.openstreetmap.org/relation/439179`

#### Scenario: Ručně zadané místo
- **WHEN** místo má rozhodnutí `{"gps": [49.4063, 16.7777], "popis":
  "zadáno ručně"}`
- **THEN** panel ukáže souřadnice a popis bez odkazu na OSM

#### Scenario: Místo bez souřadnic
- **WHEN** místo má rozhodnutí `null`
- **THEN** panel ukáže „Bez souřadnic.“ bez odkazu na OSM

#### Scenario: Porovnání stejnojmenných kandidátů
- **WHEN** volba souřadnic pro `Vysočany` ukazuje kandidáty z okresů
  Blansko a Znojmo
- **THEN** každý kandidát má vlastní odkaz na svůj objekt OSM
  a kliknutí na odkaz kandidáta nevybere ani nepotvrdí

#### Scenario: Neplatná hodnota
- **WHEN** rozhodnutí místa nebo kandidát z cache má `osm`
  `None/None`
- **THEN** odkaz na OSM chybí a souřadnice i popis se ukážou jako
  obvykle
