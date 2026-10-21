## MODIFIED Requirements

### Requirement: Struktura souboru
`_metadata.json` SHALL obsahovat klíč `schema` s hodnotou
`fotoarchiv-digi-media-metadata/2` a oddíly `akce`, `skupiny`
a `soubory` podle README. Soubory SHALL být klíčovány názvem souboru
v kořeni akce.

Proti verzi `/1` jsou **vypuštěné klíče**: `autori` a `osoby` u akce,
`datum_od`, `datum_do` a `osoby` u skupiny a `osoby` u souboru.
Vypuštěný klíč MUST NOT ovlivnit výsledné hodnoty, sidecary ani index
a při uložení MUST být odstraněn, stejně jako `obliceje` u akce nebo
skupiny.

#### Scenario: Nová akce
- **WHEN** uživatel poprvé uloží akci
- **THEN** vznikne `_metadata.json` se `schema`
  `fotoarchiv-digi-media-metadata/2`, `akce`, `skupiny` a `soubory`

#### Scenario: Autoři u akce se nedědí
- **WHEN** `_metadata.json` má `akce.autori` = [`Příkladný, Daniel`]
  a skupina `g9` ani její soubory autory nemají
- **THEN** soubory skupiny `g9` nemají žádné autory a sidecary
  neobsahují tag `autor/Příkladný, Daniel`

#### Scenario: Datum skupiny
- **WHEN** skupina `g9` má `datum_od` = `2026-04-28` a uživatel akci
  uloží
- **THEN** skupina `g9` v `_metadata.json` `datum_od` nemá

### Requirement: Dědění hodnot
Výsledná hodnota pole pro soubor SHALL být hodnota zadaná u souboru,
jinak u jeho skupiny, jinak u akce. Každé pole akce i skupiny MUST jít
přepsat na nižší úrovni. Autoři (`autori`) SHALL být jen u skupiny
a souboru, autoři skupiny MUST jít přepsat u souboru. Do
`_metadata.json` se SHALL ukládat jen hodnoty zadané na dané úrovni,
ne zděděné.

Výjimky, které se nedědí: `ucastnici` akce (výčet lidí na akci, ne
osoby na každé fotce), `mista` akce (výčet míst akce; skupina a soubor
mají jedno `misto`), `nazev` skupiny (čitelný název skupiny, ne
název akce) a u souboru `skupina`, `sha256` a `obliceje`. Název akce
proto nejde přepsat na úrovni skupiny, jen u souboru.

`obliceje` SHALL existovat jen u souboru a zapisuje je jen
synchronizace z Immiche. Osoby na fotce jsou jména z `obliceje`.

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
- **WHEN** akce má `nazev` = `kontrola Naučné stezky` a skupina `nazev`
  = `Panasonic DC-G9`
- **THEN** výsledný `nazev` souborů skupiny je `kontrola Naučné stezky`

## ADDED Requirements

### Requirement: Převod starších dokumentů
Server SHALL `_metadata.json` se `schema` `fotoarchiv-digi-media-metadata/1`
při načtení převést na `/2`: odebrat vypuštěné klíče a nastavit
`schema`. Převod MUST NOT sám nic zapsat. Další uložení akce
(plocha, dokončení, synchronizace Immiche, import) SHALL uložit
dokument `/2`. Ochrana proti souběžné změně SHALL dál porovnávat
verzi souboru na disku.

#### Scenario: Otevření starší akce
- **WHEN** uživatel otevře akci, jejíž `_metadata.json` má `schema`
  `/1` a `osoby` u souboru
- **THEN** akce se otevře, soubor se na disku nezmění a klient dostane
  dokument `/2` bez `osoby`

#### Scenario: Uložení starší akce
- **WHEN** uživatel v té akci změní popis a změna se uloží
- **THEN** `_metadata.json` má `schema` `/2`, nový popis a žádný
  vypuštěný klíč

### Requirement: Příkaz migrovat
Příkaz `python -m fotoarchiv migrovat` SHALL bez `--zapis-do-archivu`
jen vypsat akce s dokumentem `/1` a jejich vypuštěné klíče s počty
a MUST NOT nic zapsat. S `--zapis-do-archivu` SHALL každou takovou
akci uložit převedenou na `/2`. Dokument `/2` MUST zůstat beze změny.
Selhání nebo souběžná změna jedné akce MUST NOT zastavit ostatní;
příkaz ji SHALL vypsat a skončit nenulovým kódem.

#### Scenario: Výpis nanečisto
- **WHEN** správce spustí `migrovat` bez `--zapis-do-archivu` a jedna
  akce má `/1` s `osoby` u 3 souborů
- **THEN** výpis uvede tu akci a 3× `soubor.osoby` a `_metadata.json`
  zůstane beze změny

#### Scenario: Opakované spuštění
- **WHEN** správce spustí `migrovat --zapis-do-archivu` podruhé
- **THEN** žádný `_metadata.json` se nezmění

### Requirement: Záznam o exportu při migraci
Ukazoval-li záznam o exportu akce na verzi `_metadata.json` před
převodem a akce neměla `akce.autori`, SHALL příkaz `migrovat` záznam
přenést na novou verzi (sidecary se převodem nemění). U akce
s `akce.autori` SHALL vypsat počet souborů, které autory jen dědily
z akce, a záznam o exportu MUST NOT měnit.

#### Scenario: Dokončená akce zůstane exportovaná
- **WHEN** dokončená akce s aktuálním exportem má `/1` bez `akce.autori`
  a správce spustí `migrovat --zapis-do-archivu`
- **THEN** `_metadata.json` má `/2` a plocha akce neukáže
  „neexportované změny“

#### Scenario: Akce s autory akce
- **WHEN** akce má `akce.autori` a 12 souborů bez autorů ve skupině
  i u sebe
- **THEN** příkaz vypíše, že 12 souborů ztratí autory, a plocha akce
  ukáže „neexportované změny“
