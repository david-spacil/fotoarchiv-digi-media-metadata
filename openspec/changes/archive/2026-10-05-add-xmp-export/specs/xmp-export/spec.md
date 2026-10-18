## Purpose

Generovat z `_metadata.json` XMP sidecary, ze kterých Immich načte popis,
datum, polohu a tagy fotek a videí akce.

## ADDED Requirements

### Requirement: Obsah sidecaru
Sidecar souboru SHALL obsahovat výsledné (zděděné) hodnoty takto:
`popis` → `dc:description`, `datum` → `xmp:CreateDate`, výsledné `gps`
(vlastní, zděděné nebo souřadnice místa) → `exif:GPSLatitude`
a `exif:GPSLongitude`, `autori` → tagy `autor/<jméno>`, `osoby` → tagy
`osoba/<jméno>` a název složky akce → tag `akce/<název složky>`, vše
v `digiKam:TagsList`. Lomítko v názvu tagu MUST být nahrazeno pomlčkou.
Prázdná pole se do sidecaru nezapisují. Název místa, přístroj,
účastníci akce ani skupina se do sidecaru MUST NOT zapsat.

#### Scenario: Zděděné hodnoty
- **WHEN** skupina `g9` má autory `Příkladný, Daniel` a `Modelová, Zuzana`
  a soubor `P1503712.JPG` patří do `g9`
- **THEN** sidecar `P1503712.JPG.xmp` obsahuje tagy `autor/Příkladný,
  Daniel` a `autor/Modelová, Zuzana`

#### Scenario: GPS z místa
- **WHEN** soubor nemá GPS a jeho místo `Holštejn` má souřadnice
- **THEN** sidecar obsahuje souřadnice Holštejna a žádný tag místa

#### Scenario: Tag akce
- **WHEN** akce je ve složce `2026-04-28 kontrola Stezky`
- **THEN** sidecar každého jejího souboru obsahuje tag
  `akce/2026-04-28 kontrola Stezky`

### Requirement: Časová zóna data
Datum s časem bez zóny SHALL být zapsáno se zónou Europe/Prague platnou
v daný okamžik (+01:00 v zimním, +02:00 v letním čase). Datum bez času
SHALL být zapsáno bez času a bez zóny.

#### Scenario: Letní čas
- **WHEN** `datum` je `2026-04-28T09:44:36`
- **THEN** `xmp:CreateDate` je `2026-04-28T09:44:36+02:00`

#### Scenario: Zimní čas
- **WHEN** `datum` je `2026-01-10T14:00:00`
- **THEN** `xmp:CreateDate` je `2026-01-10T14:00:00+01:00`

#### Scenario: Jen datum
- **WHEN** `datum` je `2026-04-28` (WhatsApp)
- **THEN** `xmp:CreateDate` je `2026-04-28`

### Requirement: Deterministický obsah
Obsah sidecaru SHALL záviset jen na `_metadata.json` a názvu složky
akce: bez časových razítek a verze nástroje, se stálým pořadím prvků
a tagů. Stejná metadata MUST dát bajtově stejný sidecar.

#### Scenario: Opakovaný export
- **WHEN** se akce exportuje dvakrát bez změny metadat
- **THEN** sidecary jsou bajtově stejné

### Requirement: Zápis jen změněných
Export SHALL zapsat sidecar jen tehdy, když chybí nebo se jeho obsah
liší od nově vygenerovaného. Zápis MUST být atomický. Export SHALL
vytvořit sidecar jen pro soubory se záznamem v `soubory`, které jsou
v kořeni akce a nejsou označené k vyřazení. Jiné soubory `.xmp` export
nemaže. Výsledkem SHALL být počty zapsaných, nezměněných a selhaných
sidecarů.

#### Scenario: Změna popisu
- **WHEN** v akci se 100 exportovanými soubory se změní popis jednoho
  souboru a akce se znovu exportuje
- **THEN** zapíše se 1 sidecar a 99 zůstane nezměněno

### Requirement: Umístění podle režimu
V produkčním režimu SHALL být sidecar zapsán vedle souboru jako
`<název souboru>.xmp`. Ve vývojovém režimu SHALL být zapsán do
pracovního adresáře `xmp/<složka akce>/<název souboru>.xmp` a do archivu
MUST NOT být zapsáno nic.

#### Scenario: Vývojový režim
- **WHEN** se akce exportuje bez `--zapis-do-archivu`
- **THEN** sidecary jsou v `.work/xmp/<akce>/` a složka akce se nezmění

### Requirement: Dávkový export z příkazové řádky
Příkaz `python -m fotoarchiv exportovat` SHALL exportovat zadanou akci,
nebo bez ní všechny akce s `_metadata.json`, se stejnými pravidly
a stejným přepínačem režimu jako server. Pro každou akci SHALL vypsat
počty zapsaných, nezměněných a selhaných sidecarů.

#### Scenario: Export celého archivu
- **WHEN** uživatel spustí `exportovat` bez akce
- **THEN** exportují se všechny akce s `_metadata.json` a akce bez něj
  se přeskočí

### Requirement: Záznam o exportu
Po exportu bez chyb SHALL aplikace v pracovním adresáři zaznamenat verzi
`_metadata.json` akce, ze které export vznikl. Akce SHALL mít
*neexportované změny*, když se aktuální verze od zaznamenané liší;
bez záznamu je stav exportu *neznámý*. Do archivu se záznam MUST NOT
zapisovat.

#### Scenario: Úprava po exportu
- **WHEN** akce se exportuje bez chyb a pak se změní popis souboru
- **THEN** akce má neexportované změny

#### Scenario: Export s chybou
- **WHEN** zápis jednoho sidecaru selže
- **THEN** záznam o exportu se nezmění

### Requirement: Kontrola nanečisto
Aplikace SHALL umět akci zkontrolovat nanečisto: vygenerovat sidecary,
porovnat je s diskem a vrátit počet chybějících nebo neaktuálních, aniž
cokoli zapíše.

#### Scenario: Ruční úprava sidecaru
- **WHEN** někdo ručně změní jeden sidecar exportované akce
- **THEN** kontrola nanečisto hlásí 1 neaktuální sidecar a nic nezapíše
