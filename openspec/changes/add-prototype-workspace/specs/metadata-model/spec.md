## Purpose

Definovat `_metadata.json` jako zdroj pravdy o metadatech akce, pravidla
dědění hodnot a bezpečné ukládání.

## ADDED Requirements

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

Výjimky, které se nedědí: `nazev` skupiny (čitelný název skupiny, ne
název akce) a u souboru `skupina` a `sha256`. Název akce proto nejde
přepsat na úrovni skupiny, jen u souboru.

#### Scenario: Autor přepsaný u fotky
- **WHEN** skupina má `autori` = [`Spáčil, David`, `Kopáčová, Zuzana`]
  a jeden soubor má `autori` = [`Kopáčová, Zuzana`]
- **THEN** výslední autoři toho souboru jsou jen `Kopáčová, Zuzana`
  a ostatních souborů skupiny oba

#### Scenario: Zrušení přepsání
- **WHEN** uživatel u souboru přepsání pole zruší
- **THEN** pole zmizí ze záznamu souboru a hodnota se znovu dědí

#### Scenario: Název skupiny
- **WHEN** akce má `nazev` = `kontrola Stezky` a skupina `nazev`
  = `Panasonic DC-G9`
- **THEN** výsledný `nazev` souborů skupiny je `kontrola Stezky`

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
