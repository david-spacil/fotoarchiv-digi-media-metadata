## Purpose

Načíst technická metadata a náhledy fotek a videí v kořeni akce
a navrhnout z nich skupiny pro hromadné přiřazení údajů.

## ADDED Requirements

### Requirement: Zpracovávané soubory
Sken SHALL zahrnout fotky a videa v kořeni akce (JPG, JPEG, PNG, MP4,
MOV bez ohledu na velikost písmen). `Thumbs.db`, RAWy, archivy a další
soubory MUST být vynechány; aplikace je SHALL uvést jako nezpracované.

#### Scenario: Zip v kořeni
- **WHEN** kořen akce obsahuje `prezentace.zip`
- **THEN** soubor není v mřížce a je uveden mezi nezpracovanými

### Requirement: Technická metadata
Pro každý soubor SHALL sken zjistit datum pořízení, přístroj (výrobce
a model) a GPS, pokud je soubor obsahuje. Pokud soubor datum nemá a název
odpovídá vzoru WhatsApp `IMG-YYYYMMDD-WA*`, datum SHALL být odvozeno
z názvu (jen den, bez času).

#### Scenario: Fotka z Panasonicu
- **WHEN** sken načte `P1503712.JPG` z Panasonic DC-G9
- **THEN** má datum a čas z EXIF, přístroj `Panasonic DC-G9` a GPS
  prázdné

#### Scenario: Fotka z WhatsAppu
- **WHEN** sken načte `IMG-20260428-WA0003.jpg` bez EXIF
- **THEN** má datum `2026-04-28` odvozené z názvu

### Requirement: Návrh skupin
Sken SHALL navrhnout skupiny tak, že soubory se stejným přístrojem
a stejným vzorem názvu patří do jedné skupiny. Soubor bez přístroje
SHALL patřit ke skupině se stejným vzorem názvu, pokud soubory s tímto
vzorem pocházejí z jediného přístroje; jinak SHALL být seskupen podle
vzoru názvu. Každá skupina SHALL dostat krátký identifikátor a čitelný
název.

#### Scenario: Dva přístroje
- **WHEN** akce obsahuje fotky `P*.JPG` z DC-G9 a `YYYYMMDD_HHMMSS.jpg`
  ze SM-A528B
- **THEN** sken navrhne dvě skupiny

#### Scenario: Video bez přístroje
- **WHEN** akce obsahuje `20260428_150641.jpg` ze SM-A528B
  a `20260428_144812.mp4` bez údaje o přístroji
- **THEN** obě patří do skupiny SM-A528B

#### Scenario: WhatsApp bez přístroje
- **WHEN** akce obsahuje `IMG-20260428-WA0003.jpg` bez EXIF
- **THEN** soubor patří do skupiny WhatsApp

### Requirement: Náhledy
Aplikace SHALL zobrazit náhled každé fotky a videa. Náhledy MUST být
uloženy v lokální cache mimo archiv a při dalším otevření akce znovu
použity, pokud se soubor nezměnil. Video bez možnosti vytvořit náhled
SHALL mít zástupnou ikonu.

#### Scenario: Druhé otevření akce
- **WHEN** uživatel otevře akci podruhé a soubory se nezměnily
- **THEN** náhledy se načtou z cache bez čtení originálů

### Requirement: Opakovaný sken
Při opakovaném otevření akce s existujícím `_metadata.json` SHALL sken
doplnit nové soubory (bez skupiny) a označit soubory, které
v `_metadata.json` jsou, ale v kořeni chybí. Ručně zadané údaje MUST
zůstat zachovány.

#### Scenario: Nový soubor
- **WHEN** do kořene akce přibude soubor, který v `_metadata.json` není
- **THEN** objeví se v mřížce mezi soubory bez skupiny se svými
  technickými údaji
