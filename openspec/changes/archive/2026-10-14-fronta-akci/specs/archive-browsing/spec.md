## MODIFIED Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, jako karty (ne tabulku);
pořadí určuje Řazení seznamu. Karta SHALL uvádět datum, název akce
jako odkaz na pracovní plochu, počet souborů, stav a štítky (viz Stav
akce), hotovost, náhledy a držitele zámku.
Složka s příponou `.ignored` (skrytá nedokončená akce, viz
`event-visibility`) SHALL být v seznamu pod názvem bez přípony.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit. Výjimkou jsou soubory indexu `_INDEX.html` a `_INDEX.md`, které
v produkčním režimu zapisuje aplikace (viz `archive-index`), a složka
`přetřídit`, ze které v produkčním režimu přesouvá soubory import (viz
`unsorted-import`). Seznam SHALL obsahovat odkaz na stránku Přetřídit.
Seznam SHALL nabídnout přepínač podoby karet: dlaždice (výchozí)
a řádky; volbu si pamatuje prohlížeč.

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Naučné stezky…`

#### Scenario: Skrytá akce v seznamu
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky.ignored`
- **THEN** seznam obsahuje akci `2026-04-28 kontrola Naučné stezky`

#### Scenario: Index v kořeni archivu
- **WHEN** kořen archivu obsahuje `_INDEX.html` a `_INDEX.md`
- **THEN** seznam akcí je neuvádí a `_metadata.xlsx` zůstane beze změny

#### Scenario: Jiné složky mimo akce
- **WHEN** uživatel provede import ze složky `přetřídit`
- **THEN** `fotky mimo akce` a `přednášky SKLEP TIC` zůstanou beze
  změny

#### Scenario: Karta akce
- **WHEN** seznam ukazuje akci `2026-04-28 kontrola Naučné stezky` s 50 soubory
- **THEN** karta uvádí `2026-04-28`, název `kontrola Naučné stezky` jako odkaz
  na plochu akce a 50 souborů

#### Scenario: Podoba karet
- **WHEN** uživatel otevře seznam poprvé, přepne na řádky a znovu
  načte stránku
- **THEN** seznam je napoprvé v dlaždicích a po načtení v řádcích

### Requirement: Stav akce
U každé akce SHALL seznam uvádět počet souborů v kořeni (bez
`Thumbs.db`, `_metadata.json` a sidecarů `.xmp`) a stav:
*nezpracováno* (bez `_metadata.json`), *rozpracováno*
(`_metadata.json` existuje, akce není dokončená) nebo *hotovo*.
U akce *hotovo* s neexportovanými změnami SHALL seznam uvést „změněno
po exportu“. U akce *hotovo*, jejímž souborům v kořeni (kromě
označených k vyřazení) po zdědění chybí autoři, datum nebo místo,
SHALL seznam uvést štítek „nekompletní“.

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

#### Scenario: Dokončená nekompletní akce
- **WHEN** dokončené akci 3 soubory nemají místo
- **THEN** seznam ji ukáže jako *hotovo* se štítkem „nekompletní“

### Requirement: Odznak poškozených souborů
Seznam akcí SHALL u akce s nenulovým souhrnem poškozených (viz
`file-integrity`) zobrazit na kartě odznak „N poškozených“. Plocha
akce SHALL tentýž souhrn zobrazovat v liště. Odznak MUST být čistě
informační — nezabraňuje prohlížení ani ukládání.

#### Scenario: Odznak v seznamu
- **WHEN** akce má 2 poškozené soubory v souhrnu
- **THEN** karta akce v seznamu má odznak „2 poškozené“

#### Scenario: Žádný výsledek
- **WHEN** akce nemá žádnou cache kontroly nebo je souhrn nulový
- **THEN** seznam ani plocha akce odznak nezobrazují

## ADDED Requirements

### Requirement: Hotovost akce
Seznam SHALL u akce s `_metadata.json` uvádět hotovost po polích
autoři, datum a místo: počet souborů v kořeni (bez označených
k vyřazení), které mají pole po zdědění vyplněné, z jejich celkového
počtu. Pravidla dědění MUST být stejná jako u chybějících údajů na
ploše. U akce *hotovo* SHALL hotovost uvádět i stav exportu (aktuální,
nebo „změněno po exportu“). Akce *nezpracováno* hotovost nemá; karta
SHALL místo ní nabídnout zahájení zpracování (odkaz na plochu, která
spustí průvodce). Výpočet MUST NOT číst soubory archivu kromě
`_metadata.json` a výpisu složky.

#### Scenario: Rozpracovaná akce s mezerami
- **WHEN** akce má 40 souborů, 2 označené k vyřazení, všem autory
  dědí ze skupin, 30 má datum a 10 místo
- **THEN** karta uvádí autoři 38/38, datum 30/38, místo 10/38

#### Scenario: Místo zděděné z akce
- **WHEN** akce má jediné místo akce a 20 souborů bez vlastního místa
- **THEN** karta uvádí místo 20/20

#### Scenario: Nezpracovaná akce
- **WHEN** akce nemá `_metadata.json`
- **THEN** karta hotovost neuvádí a nabízí zahájení zpracování

### Requirement: Náhledy na kartě
Karta akce SHALL ukázat pruh až 4 náhledů souborů z kořene akce
(bez označených k vyřazení), vybraných rovnoměrně podle pořadí názvů.
Náhledy MUST se načítat až ve chvíli, kdy je karta viditelná nebo
blízko viditelné oblasti; seznam MUST být použitelný dřív, než se
náhledy načtou. Soubor bez náhledu (např. video bez `ffmpeg`) SHALL
mít zástupnou ikonu. Akce bez souborů pruh nemá.

#### Scenario: Velká akce
- **WHEN** akce má 200 souborů
- **THEN** karta ukáže 4 náhledy rozložené přes celou akci, ne první
  4 soubory

#### Scenario: Malá akce
- **WHEN** akce má 2 soubory
- **THEN** karta ukáže 2 náhledy

#### Scenario: Karta mimo obrazovku
- **WHEN** seznam má 300 akcí a uživatel je neposouvá
- **THEN** náhledy se načtou jen u karet ve viditelné oblasti
  a v její blízkosti

### Requirement: Držitel zámku na kartě
Seznam SHALL u akce, kterou právě drží platný zámek (viz `event-lock`),
uvést jméno držitele. Zámek vlastní relace uživatele SHALL být
odlišený („otevřeno u vás“). Seznam MUST neuvádět identifikátor relace.

#### Scenario: Akce u kolegy
- **WHEN** akci drží zámek uživatele Modelová, Zuzana
- **THEN** karta uvádí „upravuje Modelová, Zuzana“

#### Scenario: Volná akce
- **WHEN** akce nemá platný zámek
- **THEN** karta držitele neuvádí

### Requirement: Filtry a hledání
Seznam SHALL nabídnout výlučné filtry s počty akcí:
- **Vše** (výchozí),
- **Moje rozpracované**: akce *rozpracováno* nebo *hotovo* se
  změnami po exportu, v jejímž `upravili` je jméno přihlášeného
  uživatele nebo kterou drží jeho zámek,
- **K dokončení**: akce *rozpracováno*, jejímž souborům nic nechybí
  (hotovost všech polí úplná), a akce *hotovo* se změnami po exportu,
- **Nezpracované**: akce *nezpracováno*.

Seznam SHALL nabídnout hledání v názvu akce, které ignoruje
diakritiku a velikost písmen a kombinuje se s filtrem. Zvolený filtr,
hledání a řazení SHALL zůstat zachované po návratu z plochy akce.

#### Scenario: Moje rozpracované
- **WHEN** uživatel Příkladný, Daniel uložil akce A a B, A je
  *rozpracováno* a B *hotovo* bez změn po exportu
- **THEN** filtr Moje rozpracované ukáže jen A

#### Scenario: K dokončení
- **WHEN** rozpracovaná akce má hotovost autoři 38/38, datum 38/38,
  místo 38/38
- **THEN** filtr K dokončení ji ukáže

#### Scenario: Hledání bez diakritiky
- **WHEN** uživatel do hledání napíše `stezky naucna`
- **THEN** seznam ukáže akci `2026-04-28 kontrola Naučné stezky Vzorov`

#### Scenario: Návrat z plochy
- **WHEN** uživatel zvolí filtr Nezpracované, otevře akci a vrátí se
  na seznam
- **THEN** seznam má dál zvolený filtr Nezpracované

### Requirement: Řazení seznamu
Seznam SHALL nabídnout řazení:
- **podle data akce** sestupně (výchozí),
- **podle hotovosti** vzestupně (nejméně hotové nahoře; hotovost =
  součet vyplněných polí všech souborů ze všech možných); akce
  *nezpracováno* na konci, shoda podle data sestupně,
- **podle poslední úpravy** sestupně (nejnovější čas v `upravili`);
  akce bez záznamu na konci podle data sestupně.

#### Scenario: Poslední úprava
- **WHEN** akce A byla naposledy uložena 2026-10-12 a akce B
  2026-10-14, akce C nemá `upravili`
- **THEN** řazení podle poslední úpravy dá pořadí B, A, C

#### Scenario: Výchozí řazení
- **WHEN** uživatel otevře seznam poprvé
- **THEN** akce jsou seřazené podle data sestupně
