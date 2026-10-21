## MODIFIED Requirements

### Requirement: Obsah sidecaru
Sidecar souboru SHALL obsahovat výsledné (zděděné) hodnoty takto:
`popis` → `dc:description`, `datum` → `xmp:CreateDate`, výsledné `gps`
(vlastní, zděděné nebo souřadnice místa) → `exif:GPSLatitude`
a `exif:GPSLongitude`, `autori` → tagy `autor/<jméno>` a název složky
akce → tag `akce/<název složky>`, vše v `digiKam:TagsList`. Lomítko
v názvu tagu MUST být nahrazeno pomlčkou. Prázdná pole se do sidecaru
nezapisují. Název místa, přístroj, účastníci akce, osoby ani skupina se
do sidecaru MUST NOT zapsat; obličeje jen podle požadavku Obličeje pro
obnovu.

#### Scenario: Zděděné hodnoty
- **WHEN** skupina `g9` má autory `Příkladný, Daniel` a `Modelová, Zuzana`
  a soubor `P1503712.JPG` patří do `g9`
- **THEN** sidecar `P1503712.JPG.xmp` obsahuje tagy `autor/Příkladný,
  Daniel` a `autor/Modelová, Zuzana`

#### Scenario: GPS z místa
- **WHEN** soubor nemá GPS a jeho místo `Vzorkov` má souřadnice
- **THEN** sidecar obsahuje souřadnice Vzorkova a žádný tag místa

#### Scenario: Tag akce
- **WHEN** akce je ve složce `2026-04-28 kontrola Naučné stezky`
- **THEN** sidecar každého jejího souboru obsahuje tag
  `akce/2026-04-28 kontrola Naučné stezky`

#### Scenario: Osoby se běžně neexportují
- **WHEN** soubor má obličej `Vzorný, Tomáš` a exportuje se bez volby
  pro obnovu
- **THEN** jeho sidecar neobsahuje tag `osoba/…` ani oblasti obličejů

### Requirement: Záznam o exportu
Po exportu bez chyb SHALL aplikace v pracovním adresáři zaznamenat verzi
`_metadata.json` akce, ze které export vznikl. Akce SHALL mít
*neexportované změny*, když se aktuální verze od zaznamenané liší;
bez záznamu je stav exportu *neznámý*. Do archivu se záznam MUST NOT
zapisovat. Zápis synchronizace obličejů do akce, jejíž záznam odpovídal
verzi před zápisem, SHALL záznam posunout na novou verzi, protože
obličeje obsah běžných sidecarů nemění. Export pro obnovu (s obličeji)
MUST NOT záznam změnit.

#### Scenario: Úprava po exportu
- **WHEN** akce se exportuje bez chyb a pak se změní popis souboru
- **THEN** akce má neexportované změny

#### Scenario: Export s chybou
- **WHEN** zápis jednoho sidecaru selže
- **THEN** záznam o exportu se nezmění

#### Scenario: Synchronizace obličejů po exportu
- **WHEN** akce je exportovaná a synchronizace jí změní obličeje
- **THEN** akce nemá neexportované změny

## ADDED Requirements

### Requirement: Obličeje pro obnovu
Příkaz `exportovat` SHALL mít volbu `--obliceje`, se kterou sidecary
navíc obsahují oblasti pojmenovaných obličejů ve formátu MWG
(`mwg-rs:Regions`): `mwg-rs:AppliedToDimensions` s rozměry originálu
v pixelech a pro každý obličej `mwg-rs:Area` s `oblast` (jednotka
`normalized`), `mwg-rs:Type` `Face` a `mwg-rs:Name` se jménem. Takový
sidecar SHALL Immich se zapnutým importem obličejů z metadat načíst
jako obličej přiřazený osobě daného jména. Soubory bez obličejů SHALL
dostat běžný sidecar.

#### Scenario: Export pro obnovu
- **WHEN** soubor 2736 × 3648 má obličej `Vzorný, Tomáš` s oblastí
  `[0.5, 0.4, 0.08, 0.06]` a spustí se `exportovat --obliceje`
- **THEN** sidecar obsahuje `mwg-rs:Regions` s rozměry 2736 × 3648
  a oblastí `Face` jménem `Vzorný, Tomáš` se středem 0.5, 0.4 a velikostí
  0.08 × 0.06

#### Scenario: Kontrola po exportu pro obnovu
- **WHEN** po `exportovat --obliceje` proběhne kontrola nanečisto
- **THEN** sidecary s obličeji jsou hlášené jako neaktuální
