## Purpose

Přiřadit názvům míst souřadnice, aby fotky bez GPS v EXIF dostaly
v Immichi místo, a přitom se na stejný název neptat služby opakovaně.

## ADDED Requirements

### Requirement: Dotaz na geokódovací službu
Server SHALL hledat název místa ve veřejném Nominatimu (OpenStreetMap)
a vrátit kandidáty s názvem, popisem (hierarchie správních celků)
a souřadnicemi. Dotaz MUST nést User-Agent s názvem aplikace
a kontaktem z konfigurace serveru; bez kontaktu je geokódování vypnuté.
Server MUST posílat nejvýš jeden dotaz za sekundu a MUST NOT se ptát
během psaní, jen na potvrzený název.

#### Scenario: Nejednoznačný název
- **WHEN** se hledá `Vysočany`
- **THEN** výsledek obsahuje kandidáty z okresů Blansko, Znojmo
  i Prahy 9

#### Scenario: Služba nedostupná
- **WHEN** Nominatim neodpoví
- **THEN** aplikace ukáže chybu s možností zkusit znovu a práce
  s ostatními poli pokračuje

### Requirement: Cache odpovědí
Odpovědi služby SHALL být uložené v cache na serveru mimo archiv,
sdílené všemi akcemi a uživateli. Stejný dotaz (porovnání bez ohledu na
velikost písmen, normalizaci Unicode a nadbytečné mezery) MUST být
zodpovězen z cache bez dotazu na službu.

#### Scenario: Opakovaný dotaz
- **WHEN** se `Vysočany` hledají podruhé, v jiné akci
- **THEN** kandidáti přijdou z cache a na Nominatim neodejde žádný
  dotaz

### Requirement: Volba souřadnic místa
Pro každý název místa použitý jako výsledné `misto` některého souboru
bez vlastního GPS SHALL uživatel rozhodnout o souřadnicích: vybrat
kandidáta, zadat souřadnice ručně, nebo zvolit „bez souřadnic“.
Rozhodnutí SHALL být uložené v `_metadata.json` akce v klíči
`souradnice_mist` (název → `{gps, popis}`, nebo `null` pro „bez
souřadnic“) a platí pro všechny soubory akce s tímto místem. Má-li
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

### Requirement: Atribuce
Kde aplikace zobrazuje výsledky z Nominatimu, SHALL uvést
„© OpenStreetMap contributors“.

#### Scenario: Výběr kandidáta
- **WHEN** formulář ukazuje kandidáty pro místo
- **THEN** u nich je uvedena atribuce OSM
