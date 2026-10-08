# archive-browsing Specification

## Purpose

Najít v archivu složky akcí, ukázat jejich stav zpracování a umožnit
vybrat akci, se kterou se bude pracovat.

## Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, seřazený podle data sestupně.
Složka s příponou `.ignored` (skrytá nedokončená akce, viz
`event-visibility`) SHALL být v seznamu pod názvem bez přípony.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit. Výjimkou jsou soubory indexu `_INDEX.html` a `_INDEX.md`, které
v produkčním režimu zapisuje aplikace (viz `archive-index`), a složka
`přetřídit`, ze které v produkčním režimu přesouvá soubory import (viz
`unsorted-import`). Seznam SHALL obsahovat odkaz na stránku Přetřídit.

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Stezky…`

#### Scenario: Skrytá akce v seznamu
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky.ignored`
- **THEN** seznam obsahuje akci `2026-04-28 kontrola Stezky`

#### Scenario: Index v kořeni archivu
- **WHEN** kořen archivu obsahuje `_INDEX.html` a `_INDEX.md`
- **THEN** seznam akcí je neuvádí a `_metadata.xlsx` zůstane beze změny

#### Scenario: Jiné složky mimo akce
- **WHEN** uživatel provede import ze složky `přetřídit`
- **THEN** `fotky mimo akce` a `přednášky SKLEP TIC` zůstanou beze
  změny

### Requirement: Stav akce
U každé akce SHALL seznam uvádět počet souborů v kořeni (bez
`Thumbs.db`, `_metadata.json` a sidecarů `.xmp`) a stav:
*nezpracováno* (bez `_metadata.json`), *rozpracováno*
(`_metadata.json` existuje, akce není dokončená) nebo *hotovo*.
U akce *hotovo* s neexportovanými změnami SHALL seznam uvést „změněno
po exportu“.

#### Scenario: Akce bez metadat
- **WHEN** složka akce nemá `_metadata.json`
- **THEN** seznam ji ukáže jako *nezpracováno*

#### Scenario: Akce s metadaty
- **WHEN** k akci existuje `_metadata.json` a akce není označená jako
  dokončená
- **THEN** seznam ji ukáže jako *rozpracováno*

#### Scenario: Exportovaná akce
- **WHEN** kořen akce obsahuje 50 fotek a 50 sidecarů `.xmp`
- **THEN** seznam u akce uvádí 50 souborů

#### Scenario: Dokončená akce upravená po exportu
- **WHEN** dokončená akce má neexportované změny
- **THEN** seznam ji ukáže jako *hotovo* s poznámkou „změněno po
  exportu“

### Requirement: Metadata ve složce akce
V produkčním režimu SHALL aplikace číst i ukládat `_metadata.json`
přímo ve složce akce v archivu. Ve vývojovém režimu (výchozím) SHALL
číst i ukládat v pracovním adresáři mimo archiv, který zrcadlí názvy
složek akcí, a MUST NOT do archivu nic zapisovat, přesouvat ani mazat.
Režim MUST být při spuštění zvolen výslovně a vypsán.

#### Scenario: Uložení v produkčním režimu
- **WHEN** uživatel v produkčním režimu uloží metadata akce
- **THEN** soubor `_metadata.json` vznikne nebo se změní ve složce akce

#### Scenario: Uložení ve vývojovém režimu
- **WHEN** uživatel ve vývojovém režimu uloží metadata akce
- **THEN** soubor vznikne v pracovním adresáři pod názvem složky akce
  a archiv zůstane beze změny

### Requirement: Atomické uložení
Uložení `_metadata.json` MUST být atomické: soubor je vždy buď celý
starý, nebo celý nový, i při výpadku během zápisu.

#### Scenario: Výpadek při zápisu
- **WHEN** server spadne uprostřed ukládání
- **THEN** ve složce akce zůstane předchozí platný `_metadata.json`

### Requirement: Převzetí z pracovního adresáře
Aplikace SHALL nabídnout jednorázové převzetí `_metadata.json`
z pracovního adresáře do archivu. Převzetí MUST přeskočit
akce, které už `_metadata.json` v archivu mají, a vypsat je.

#### Scenario: Akce už má metadata v archivu
- **WHEN** akce má `_metadata.json` v pracovním adresáři i v archivu
- **THEN** převzetí ji přeskočí, archivní soubor nezmění a akci vypíše

### Requirement: Odznak poškozených souborů
Seznam akcí SHALL u akce s nenulovým souhrnem poškozených (viz
`file-integrity`) zobrazit odznak „N poškozených“. Plocha akce SHALL
tentýž souhrn zobrazovat v liště. Odznak MUST být čistě informační —
nezabraňuje prohlížení ani ukládání.

#### Scenario: Odznak v seznamu
- **WHEN** akce má 2 poškozené soubory v souhrnu
- **THEN** řádek akce v seznamu má odznak „2 poškozené“

#### Scenario: Žádný výsledek
- **WHEN** akce nemá žádnou cache kontroly nebo je souhrn nulový
- **THEN** seznam ani plocha akce odznak nezobrazují

### Requirement: Označení dlaždice poškozeného souboru
Pracovní plocha akce SHALL dlaždici souboru, jehož výsledek kontroly
je *podezřelý* nebo *nečitelný* a který nemá `overeno` ani `vyradit`,
vizuálně odlišit a v tooltipu uvést stav a důvod kontroly. Dlaždice
potvrzeného (`overeno`) nebo vyřazeného (`vyradit`) souboru se odlišovat
MUST NOT, s výjimkou stávajícího označení vyřazení.

#### Scenario: Nula na dlaždici
- **WHEN** plocha zobrazuje nečitelnou fotku
- **THEN** dlaždice je odlišená a tooltip uvádí *nečitelný* s důvodem

#### Scenario: Po přehodnocení
- **WHEN** uživatel u fotky potvrdí „v pořádku“ a uloží
- **THEN** dlaždice je běžná a souhrn akce fotku nepočítá

### Requirement: Potvrzení „v pořádku“
Plocha akce SHALL u dlaždice s poškozeným souborem nabídnout akci
„Považovat za v pořádku“. Potvrzení se uloží do záznamu souboru
jako `overeno` (viz `metadata-model`) a projeví se v odznaku,
souhrnu i dlaždici po uložení. Zrušení potvrzení MUST být možné
stejnou akcí.

#### Scenario: Falešná pozitivita
- **WHEN** *podezřelá* fotka je podle uživatele v pořádku a uživatel
  potvrdí „Považovat za v pořádku“
- **THEN** odznak akce fotku nadále nepočítá a po opětovném kliknutí
  ji počítá znovu

### Requirement: Rozhodnutí o poškozených v dialogu úklidu
Dialog „Uklidit…“ SHALL zobrazit sekci „Poškozené soubory“ jako
tabulku poškozených souborů kořene (malý náhled nebo zástupná ikona,
název, stav, důvod) se dvěma výlučnými sloupci „Vyřadit“ a „V pořádku“,
i když akce nemá žádné jiné nálezy; tlačítko „Uklidit…“ se SHALL
objevit i tehdy, má-li akce poškozený soubor bez rozhodnutí. Každý
sloupec SHALL mít v hlavičce hromadné zaškrtnutí všech řádků. Výchozí
stav řádku SHALL odpovídat uloženým metadatům (potvrzený = V pořádku,
jinak nic); soubor bez volby MUST zůstat beze změny. Volby se SHALL
zapsat až potvrzením dialogu, zrušení dialogu MUST nic nezměnit:
Vyřadit nastaví `vyradit` (zruší `overeno`) a soubor se přesune spolu
s ostatními operacemi plánu, V pořádku nastaví `overeno`, odškrtnutí
potvrzeného `overeno` zruší. Bez přesunů SHALL tlačítko jen uložit.
Soubor už označený k vyřazení SHALL být v tabulce šedě bez přepínačů,
s poznámkou, že označení se ruší na dlaždici. Ve vývojovém režimu
SHALL být sloupec Vyřadit vypnutý.

#### Scenario: Jedno okno pro konzistenci i poškozené
- **WHEN** akce má osiřelý sidecar i poškozenou fotku a uživatel
  otevře „Uklidit…“
- **THEN** dialog obsahuje plán přesunů i tabulku Poškozené soubory
  a fotka nemá žádnou volbu

#### Scenario: Výlučné volby
- **WHEN** uživatel u souboru zaškrtne Vyřadit a pak V pořádku
- **THEN** zůstane zaškrtnuté jen V pořádku

#### Scenario: Hromadné potvrzení
- **WHEN** uživatel zaškrtne V pořádku v hlavičce a potvrdí „Uložit“
- **THEN** všechny poškozené soubory bez označení k vyřazení mají
  `overeno`, nic se nepřesune a odznak akce je 0

#### Scenario: Vyřazení a zrušení potvrzení najednou
- **WHEN** soubor A je bez volby, soubor B potvrzený; uživatel u A
  zaškrtne Vyřadit, u B odškrtne V pořádku a spustí úklid
- **THEN** A se přesune do `k_odstraneni.ignored` i se sidecarem a B
  zůstane v kořeni bez `overeno`

#### Scenario: Zrušení dialogu
- **WHEN** uživatel zaškrtne volby a dialog zruší
- **THEN** metadata se nezmění
