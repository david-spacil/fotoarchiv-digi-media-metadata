## Purpose

Dostat nové fotky a videa z počítače uživatele do archivu přes
prohlížeč: do stávající nebo nové složky akce, bez přepsání a bez
duplicit.

## ADDED Requirements

### Requirement: Spuštění průvodce
Aplikace SHALL nabídnout průvodce importem ze seznamu akcí (bez
předvybraného cíle) a z pracovní plochy akce (s touto akcí jako
předvybraným cílem).

#### Scenario: Import z pracovní plochy
- **WHEN** uživatel na ploše akce `2026-04-28 kontrola Stezky…` spustí
  import
- **THEN** průvodce má jako cíl předvybranou tuto akci

### Requirement: Výběr a nahrání souborů
Průvodce SHALL přijmout jednotlivé soubory i celou složku (přetažením
i výběrem). Soubory z podsložek vybrané složky SHALL zpracovat, jako
by ležely v jedné úrovni. Nahrané soubory MUST server uložit do
pracovního adresáře mimo archiv a do archivu MUST NOT zapisovat dřív,
než uživatel import potvrdí. Průvodce SHALL ukazovat průběh nahrávání.

#### Scenario: Přerušené nahrávání
- **WHEN** uživatel během nahrávání zavře stránku
- **THEN** archiv zůstane beze změny

#### Scenario: Složka s podsložkou
- **WHEN** uživatel vybere složku s `a.jpg` a `Video/b.mp4`
- **THEN** přehled obsahuje `a.jpg` i `b.mp4`

### Requirement: Podporované soubory
Import SHALL přijmout média, která aplikace zpracovává (jpg, jpeg,
png, mp4, mov), a RAWy (podle `event-cleanup`), vše bez ohledu na
velikost písmen přípony. `Thumbs.db` MUST přeskočit bez hlášení. Ostatní
soubory MUST průvodce v přehledu vypsat jako nepodporované a do
archivu je nepřenést.

#### Scenario: Nepodporovaný soubor
- **WHEN** výběr obsahuje `prezentace.pptx`
- **THEN** přehled ho uvede jako nepodporovaný a import ho nepřenese

### Requirement: Přehled před importem
Před volbou cíle SHALL průvodce ukázat počet souborů podle typu
(fotky, videa, RAWy), rozsah dat z EXIF (u WhatsApp fotek z názvu
souboru), zjištěné přístroje a nepodporované soubory.

#### Scenario: Smíšený výběr
- **WHEN** uživatel nahraje 40 JPG z G9 z 28. 4. 2026, 40 RW2
  a 2 mp4
- **THEN** přehled uvede 40 fotek, 2 videa, 40 RAWů, datum 28. 4. 2026
  a přístroj Panasonic DC-G9

### Requirement: Volba cíle
Uživatel SHALL zvolit jako cíl stávající akci, nebo novou akci. U nové
akce SHALL průvodce předvyplnit datum nejstarším dnem z nahraných
souborů a vyžádat název. Název složky nové akce MUST odpovídat vzoru
`YYYY-MM-DD název`, MUST NOT obsahovat `/` ani `\` a složka stejného
názvu MUST NOT existovat. U dokončené akce SHALL průvodce upozornit, že
akce dostane nové soubory bez metadat.

#### Scenario: Návrh data nové akce
- **WHEN** nahrané fotky mají EXIF datum 28. a 29. 4. 2026
- **THEN** průvodce předvyplní datum `2026-04-28`

#### Scenario: Existující název
- **WHEN** uživatel zadá novou akci s názvem složky, která už v archivu
  je
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

### Requirement: Plán importu
Pro zvolený cíl SHALL průvodce ukázat plán: média do kořene akce, RAWy
do `RAW.ignored/` (vznikne, pokud chybí). Soubor, jehož cílová cesta už
existuje nebo který má stejné jméno jako jiný soubor ve výběru
(bez ohledu na velikost písmen), MUST být označen jako blokovaný.
Soubor se stejným obsahem (sha256) jako soubor v kořeni cílové akce
nebo jako jiný soubor výběru MUST být označen jako duplicita
a přeskočen.

#### Scenario: Kolize jména
- **WHEN** cílová akce obsahuje `P1503712.JPG` s jiným obsahem
  a výběr také `P1503712.JPG`
- **THEN** plán soubor označí jako blokovaný kolizí

#### Scenario: Duplicita s jiným jménem
- **WHEN** výběr obsahuje `kopie.jpg` se stejným obsahem jako
  `P1503712.JPG` v kořeni cílové akce
- **THEN** plán soubor označí jako duplicitu a nepřenese ho

### Requirement: Provedení importu
V produkčním režimu SHALL průvodce po potvrzení plán provést. Server
MUST plán sestavit znovu těsně před provedením a přenést jen
neblokované soubory, které nejsou duplicitou. Přenos MUST NOT přepsat
existující soubor. Přenesený soubor MUST mít stejný obsah a čas změny
jako nahraný originál. U nové akce server SHALL vytvořit složku akce;
pokud mezitím vznikla, import MUST odmítnout. Ve vývojovém režimu SHALL
průvodce plán jen zobrazit a do archivu nic nezapsat.

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu potvrdí import 40 JPG a 40 RW2
  do nové akce `2026-04-28 kontrola Stezky`
- **THEN** složka vznikne, 40 JPG je v jejím kořeni, 40 RW2
  v `RAW.ignored/` a akce je v seznamu jako *nezpracováno*

#### Scenario: Kolize vzniklá po zobrazení plánu
- **WHEN** mezi zobrazením plánu a potvrzením vznikne v cílové akci
  soubor stejného jména
- **THEN** ten soubor se nepřenese a výsledek ho uvede jako blokovaný

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu dojde k potvrzení
- **THEN** průvodce ukáže plán a archiv zůstane beze změny

### Requirement: Výsledek importu
Po provedení SHALL průvodce ukázat přenesené, blokované, duplicitní
a selhané soubory (s chybou). Selhání jednoho souboru MUST NOT zastavit
ostatní. Úspěšně přenesené soubory MUST server z pracovního adresáře
odstranit; nepřenesené SHALL zůstat, dokud uživatel import nezahodí.
Průvodce SHALL nabídnout otevřít cílovou akci.

#### Scenario: Otevření akce po importu
- **WHEN** import do stávající akce s `_metadata.json` skončí
- **THEN** po otevření akce jsou přenesené soubory mezi novými soubory
  akce

### Requirement: Zahození importu
Uživatel SHALL moci rozpracovaný import zahodit; server MUST pak
smazat jeho soubory z pracovního adresáře. Importy neaktivní déle než
7 dní SHALL server smazat při startu.

#### Scenario: Zahození před potvrzením
- **WHEN** uživatel po nahrání import zahodí
- **THEN** pracovní adresář importu je smazaný a archiv beze změny
