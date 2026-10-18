# metadata-model Specification

## Purpose

Definovat `_metadata.json` jako zdroj pravdy o metadatech akce, pravidla
dědění hodnot a bezpečné ukládání.

## Requirements

### Requirement: Struktura souboru
`_metadata.json` SHALL obsahovat klíč `schema` s hodnotou
`fotoarchiv-digi-media-metadata/1` a oddíly `akce`, `skupiny`
a `soubory` podle README. Soubory SHALL být klíčovány názvem souboru
v kořeni akce.

#### Scenario: Nová akce
- **WHEN** uživatel poprvé uloží akci
- **THEN** vznikne `_metadata.json` se `schema`, `akce`, `skupiny`
  a `soubory`

### Requirement: Dědění hodnot
Výsledná hodnota pole pro soubor SHALL být hodnota zadaná u souboru,
jinak u jeho skupiny, jinak u akce. Každé pole akce i skupiny MUST jít
přepsat na nižší úrovni, včetně `autori`. Do `_metadata.json` se SHALL
ukládat jen hodnoty zadané na dané úrovni, ne zděděné.

Výjimky, které se nedědí: `ucastnici` akce (výčet lidí na akci, ne
osoby na každé fotce), `mista` akce (výčet míst akce; skupina a soubor
mají jedno `misto`), `nazev` skupiny (čitelný název skupiny, ne
název akce) a u souboru `skupina`, `sha256` a `obliceje`. Název akce
proto nejde přepsat na úrovni skupiny, jen u souboru.

`obliceje` SHALL existovat jen u souboru a zapisuje je jen
synchronizace z Immiche. Osoby na fotce jsou jména z `obliceje`. Pole
`osoby` na kterékoli úrovni MUST být ignorováno a při uložení
odstraněno, stejně jako `obliceje` u akce nebo skupiny.

#### Scenario: Autor přepsaný u fotky
- **WHEN** skupina má `autori` = [`Příkladný, Daniel`, `Modelová, Zuzana`]
  a jeden soubor má `autori` = [`Modelová, Zuzana`]
- **THEN** výslední autoři toho souboru jsou jen `Modelová, Zuzana`
  a ostatních souborů skupiny oba

#### Scenario: Zrušení přepsání
- **WHEN** uživatel u souboru přepsání pole zruší
- **THEN** pole zmizí ze záznamu souboru a hodnota se znovu dědí

#### Scenario: Účastníci akce
- **WHEN** akce má `ucastnici` = [`Příkladný, Daniel`, `Modelová, Zuzana`]
  a soubor nemá `obliceje`
- **THEN** soubor nemá žádné osoby

#### Scenario: Starší pole osoby
- **WHEN** starší `_metadata.json` má `osoby` u skupiny i u souboru
  a uživatel akci uloží
- **THEN** soubory osoby z `osoby` nemají a pole `osoby` po uložení
  v `_metadata.json` není

#### Scenario: Název skupiny
- **WHEN** akce má `nazev` = `kontrola Stezky` a skupina `nazev`
  = `Panasonic DC-G9`
- **THEN** výsledný `nazev` souborů skupiny je `kontrola Stezky`

### Requirement: Místo
Skupina a soubor SHALL mít nejvýš jedno `misto`. Pokud ho nemají a akce
má v `mista` právě jedno místo, výsledné `misto` SHALL být toto místo
akce. Pokud má akce víc míst, místo se MUST NOT z akce dědit.

#### Scenario: Jedno místo akce
- **WHEN** akce má `mista` = [`Holštejn`] a soubor ani skupina místo
  nemají
- **THEN** výsledné místo souboru je `Holštejn`

#### Scenario: Víc míst akce
- **WHEN** akce má `mista` = [`Molenburk`, `Housko`] a soubor ani
  skupina místo nemají
- **THEN** soubor nemá žádné místo

### Requirement: Technické a ruční údaje
Technické údaje ze skenu (datum, přístroj, GPS) SHALL být uloženy
u souboru a uživatel je MUST mít možnost opravit. Opravu MUST opakovaný
sken nepřepsat. Údaj, který soubor nemá, se u souboru MUST NOT ukládat,
aby se hodnota dědila ze skupiny.

#### Scenario: Oprava data
- **WHEN** uživatel opraví datum souboru a akci znovu otevře
- **THEN** zůstane opravené datum

#### Scenario: Video bez přístroje
- **WHEN** sken načte mp4 bez údaje o přístroji ve skupině
  s přístrojem `samsung SM-A528B`
- **THEN** záznam souboru pole `pristroj` neobsahuje a soubor přístroj
  dědí ze skupiny

### Requirement: Ochrana proti souběžné změně
Před uložením SHALL aplikace ověřit, že se `_metadata.json` od načtení
nezměnil. Pokud se změnil, uložení MUST být odmítnuto a uživateli
nabídnuto znovunačtení; nic se nepřepíše.

#### Scenario: Soubor změněn jinde
- **WHEN** `_metadata.json` po načtení změní jiný proces a uživatel
  uloží
- **THEN** aplikace uložení odmítne a nabídne znovunačtení

### Requirement: Průběžné ukládání
Změny SHALL být ukládány průběžně bez samostatného tlačítka, nejpozději
několik sekund po poslední úpravě. Zápis MUST být atomický (nikdy
nevznikne napůl zapsaný soubor).

#### Scenario: Úprava popisu
- **WHEN** uživatel změní popis akce a chvíli nic nedělá
- **THEN** změna je uložena v `_metadata.json`

### Requirement: GPS ze souřadnic místa
Výsledné `gps` souboru SHALL být jeho vlastní nebo zděděné `gps`; pokud
žádné není a výsledné `misto` má v `souradnice_mist` souřadnice,
výsledné `gps` SHALL být tyto souřadnice s úrovní `misto`. Souřadnice
místa MUST NOT přepsat GPS z EXIF ani ručně zadané GPS na kterékoli
úrovni a MUST NOT se ukládat k souboru.

#### Scenario: Fotka bez GPS
- **WHEN** soubor nemá `gps`, jeho místo je `Holštejn`
  a `souradnice_mist` má pro `Holštejn` [49.4063, 16.7777]
- **THEN** výsledné `gps` souboru je [49.4063, 16.7777] z úrovně
  `misto`

#### Scenario: Fotka s GPS z EXIF
- **WHEN** soubor má `gps` z EXIF a místo se souřadnicemi
- **THEN** výsledné `gps` je to z EXIF

#### Scenario: Místo bez souřadnic
- **WHEN** `souradnice_mist` má pro místo `null`
- **THEN** soubor bez vlastního GPS nemá výsledné `gps`

### Requirement: Ruční potvrzení integrity
Záznam souboru v `_metadata.json` MAY obsahovat `"overeno": true` —
ruční potvrzení uživatele, že soubor je i přes výsledek kontroly
integrity v pořádku. Příznak je pouze úrovňě souboru, nedědí se
a nezapisuje se do sidecaru ani indexu. Pole bez hodnoty se u záznamu
MUST NOT ukládat (ruční zrušení příznak odstraní).

#### Scenario: Uložení potvrzení
- **WHEN** uživatel potvrdí „v pořádku“ u *podezřelého* souboru
  a uloži
- **THEN** `soubory.<název>.overeno` je `true`

#### Scenario: Žádný vliv na export
- **WHEN** se akce s potvrzeným souborem exportuje
- **THEN** sidecar souboru o potvrzení neobsahuje žádné pole

### Requirement: Záznam o úpravách
`_metadata.json` SHALL obsahovat na nejvyšší úrovni pole `upravili`:
objekt jméno uživatele → datum a čas jeho posledního uložení akce
(ISO 8601, místní čas serveru, na sekundy). Pole SHALL zapisovat jen
server při každém úspěšném uložení metadat, při dokončení akce a při
zápisu popisu po provedení importu do akce (nová akce i akce
s `_metadata.json`), a to jménem z přihlášené relace (stejné jako
u zámku), nikdy z požadavku. Hodnotu, kterou pošle klient, server MUST
ignorovat a vzít `upravili` z uložené verze. Dokument bez `upravili`
(starší akce) MUST zůstat platný; pole vznikne prvním uložením.
`upravili` se MUST NOT exportovat do sidecarů ani indexu a nedědí se.
Podle `upravili` se řídí oprávnění k úpravě akce (viz `user-login`).

#### Scenario: První uložení
- **WHEN** uživatel Příkladný, Daniel 2026-10-14 v 10:15:02 poprvé uloží
  akci bez `upravili`
- **THEN** `_metadata.json` obsahuje
  `"upravili": {"Příkladný, Daniel": "2026-10-14T10:15:02"}`

#### Scenario: Druhý uživatel
- **WHEN** akci pak uloží uživatel Modelová, Zuzana
- **THEN** `upravili` obsahuje obě jména, každé s časem svého
  posledního uložení

#### Scenario: Podvržená hodnota
- **WHEN** klient pošle v metadatech `upravili` s jiným jménem
- **THEN** server ji zahodí a uloží jen záznam přihlášeného uživatele
  k uložené verzi

#### Scenario: Import do nové akce
- **WHEN** uživatel Modelová, Zuzana provede import do nové akce
- **THEN** založený `_metadata.json` má v `upravili` jen
  `Modelová, Zuzana` s časem zápisu

#### Scenario: Sidecar
- **WHEN** se akce s `upravili` exportuje
- **THEN** žádný sidecar ani index jména z `upravili` neobsahuje
