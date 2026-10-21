## Purpose

Stažení originálů akce z aplikace: jednoho souboru, výběru souborů
a celé akce jako ZIP spolu s metadaty z archivu (`_metadata.json`
a XMP sidecary), bez zásahu na NAS.

## ADDED Requirements

### Requirement: Stažení jednoho originálu
Aplikace SHALL umožnit stáhnout originál jednoho média z kořene akce
jako přílohu pod jeho názvem na disku, beze změny obsahu. Soubor mimo
kořen akce (podsložka, cesta s `..`) nebo jiný než médium MUST být
odmítnut.

#### Scenario: Stažení fotky
- **WHEN** uživatel stáhne `IMG_0001.jpg` z akce `2026-04-28 kontrola
  Stezky`
- **THEN** prohlížeč uloží soubor `IMG_0001.jpg` shodný bajt po bajtu
  s originálem v archivu

#### Scenario: Soubor z podsložky
- **WHEN** požadavek míří na `RAW.ignored/IMG_0001.CR2` nebo
  `../jina akce/IMG_0002.jpg`
- **THEN** aplikace odpoví „nenalezeno“ a nic nevydá

### Requirement: ZIP celé akce
Aplikace SHALL umožnit stáhnout celou akci jako ZIP. ZIP SHALL obsahovat
média z kořene akce kromě souborů označených k vyřazení; podsložky
(např. `RAW.ignored`, `k_odstraneni.ignored`) a ostatní soubory kořene
MUST v něm nebýt. Média SHALL být v ZIPu beze změny obsahu.

#### Scenario: Akce s vyřazeným souborem
- **WHEN** akce má v kořeni `a.jpg`, `b.jpg` (označený k vyřazení)
  a `c.mp4` a podsložku `RAW.ignored` s `a.CR2`
- **THEN** ZIP akce obsahuje média `a.jpg` a `c.mp4`, ne `b.jpg`
  ani `a.CR2`

### Requirement: ZIP výběru
Aplikace SHALL umožnit stáhnout jako ZIP soubory, které uživatel vybral
na pracovní ploše akce. ZIP SHALL obsahovat přesně vybraná média včetně
označených k vyřazení. Obsahuje-li výběr soubor, který není médiem
v kořeni akce, aplikace MUST požadavek odmítnout celý.

#### Scenario: Výběr s vyřazeným souborem
- **WHEN** uživatel vybere `a.jpg` a `b.jpg` (označený k vyřazení)
  a stáhne výběr
- **THEN** ZIP obsahuje média `a.jpg` a `b.jpg` a žádné jiné médium

#### Scenario: Neplatný název ve výběru
- **WHEN** požadavek na výběr obsahuje `a.jpg` a `../jina akce/x.jpg`
- **THEN** aplikace požadavek odmítne a nevydá žádný ZIP

### Requirement: Metadata v ZIPu
Má-li akce `_metadata.json`, ZIP (celé akce i výběru) SHALL obsahovat
jeho uloženou verzi a ke každému médiu se záznamem XMP sidecar
`<soubor>.xmp`. Sidecar SHALL mít obsah jako při exportu z aktuálního
`_metadata.json` bez oblastí obličejů, i když export neproběhl nebo je
zastaralý. Bez `_metadata.json` SHALL ZIP obsahovat jen média.

#### Scenario: Rozpracovaná akce bez exportu
- **WHEN** akce má `_metadata.json` s popisem `Most přes Svratku`
  u `a.jpg` a sidecary nikdy nebyly exportovány
- **THEN** ZIP obsahuje `_metadata.json` a `a.jpg.xmp` s popisem
  `Most přes Svratku`

#### Scenario: Změna po exportu
- **WHEN** po exportu se popis `a.jpg` změní a uloží
- **THEN** `a.jpg.xmp` v ZIPu nese nový popis, sidecar v archivu
  zůstane beze změny

#### Scenario: Akce bez metadat
- **WHEN** akce *nezpracováno* nemá `_metadata.json`
- **THEN** ZIP obsahuje jen média, žádný JSON ani sidecar

### Requirement: Podoba ZIPu
Soubory SHALL být v kořeni ZIPu pod názvy z disku (média, sidecary
vedle nich, `_metadata.json`). Název ZIPu celé akce SHALL být název
akce s příponou `.zip`, u výběru název akce s počtem souborů; diakritika
v názvech MUST zůstat zachována. Velikost akce MUST NOT stažení omezit.

#### Scenario: Název ZIPu akce
- **WHEN** uživatel stáhne akci `2026-04-28 kontrola Stezky`
- **THEN** prohlížeč uloží `2026-04-28 kontrola Stezky.zip`

#### Scenario: Název ZIPu výběru
- **WHEN** uživatel stáhne výběr 12 souborů téže akce
- **THEN** prohlížeč uloží `2026-04-28 kontrola Stezky (12 souborů).zip`

### Requirement: Stažení jen čte
Stažení SHALL být dostupné každému přihlášenému uživateli bez zámku
akce, i u nedokončené akce (složka s příponou `.ignored`) a akce
držené zámkem jiného uživatele. Stažení MUST NOT nic zapsat do archivu
ani do pracovního adresáře. Soubor, který během stahování ZIPu z kořene
zmizí, SHALL být přeskočen.

#### Scenario: Akce otevřená jiným uživatelem
- **WHEN** akci drží zámek jiného uživatele a uživatel ji stáhne
- **THEN** stažení proběhne a zámek zůstane beze změny

#### Scenario: Nedokončená akce
- **WHEN** akce je ve složce `2026-04-28 kontrola Stezky.ignored`
- **THEN** ZIP akce jde stáhnout a jmenuje se
  `2026-04-28 kontrola Stezky.zip`

#### Scenario: Bez přihlášení
- **WHEN** nepřihlášený požadavek žádá ZIP akce
- **THEN** aplikace ho odmítne jako ostatní požadavky bez přihlášení

### Requirement: Stažení z pracovní plochy
Pracovní plocha akce SHALL při neprázdném výběru nabídnout tlačítko
„Stáhnout (N)“. Jeden vybraný soubor SHALL stáhnout jako originál,
víc vybraných jako ZIP výběru. Tlačítko SHALL být dostupné i jen pro
čtení (bez zámku).

#### Scenario: Jeden soubor
- **WHEN** uživatel vybere `a.jpg` a klikne na „Stáhnout (1)“
- **THEN** prohlížeč uloží `a.jpg`, ne ZIP

#### Scenario: Víc souborů
- **WHEN** uživatel vybere 3 soubory a klikne na „Stáhnout (3)“
- **THEN** prohlížeč uloží ZIP výběru se 3 médii

### Requirement: Stažení z přehledu akcí
Každá karta v přehledu akcí SHALL nabídnout ikonu stažení (mráček se
šipkou dolů) bez textu, s přístupným popiskem a tooltipem „Stáhnout
akci (ZIP)“. Ikona SHALL stáhnout ZIP celé akce bez otevření plochy.

#### Scenario: Stažení z karty
- **WHEN** uživatel klikne na ikonu stažení na kartě akce
  `2026-04-28 kontrola Stezky`
- **THEN** prohlížeč uloží `2026-04-28 kontrola Stezky.zip` a přehled
  zůstane otevřený
