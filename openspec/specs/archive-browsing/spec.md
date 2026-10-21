# archive-browsing Specification

## Purpose

Najít v archivu složky akcí, ukázat jejich stav zpracování a umožnit
vybrat akci, se kterou se bude pracovat.

## Requirements

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
`unsorted-import`), a složka koše `_kos.ignored`, do které přesouvá
smazané akce (viz `event-trash`). Seznam SHALL obsahovat odkaz na
stránku Přetřídit a adminovi odkaz na stránku Koš.
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

#### Scenario: Koš v kořeni archivu
- **WHEN** kořen archivu obsahuje `_kos.ignored` se smazanou akcí
  `2026-04-28 kontrola Naučné stezky`
- **THEN** seznam akcí ji neuvádí a admin vidí odkaz na Koš

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
označených k vyřazení) po zdědění chybí autoři, datum nebo místo, nebo
která má podle posledního zjištění osob akce nepojmenované osoby, SHALL
seznam uvést štítek „nekompletní“.

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

#### Scenario: Dokončená akce s nepojmenovanými osobami
- **WHEN** dokončená akce má všechna pole vyplněná, ale 2 nepojmenované
  osoby
- **THEN** seznam ji ukáže jako *hotovo* se štítkem „nekompletní“

#### Scenario: Skryté osoby
- **WHEN** dokončená akce má všechna pole vyplněná a jediná
  nepojmenovaná osoba je v Immichi skrytá
- **THEN** seznam štítek „nekompletní“ neukáže

### Requirement: Hotovost akce
Seznam SHALL u akce s `_metadata.json` uvádět hotovost po polích
autoři, datum a místo: počet souborů v kořeni (bez označených
k vyřazení), které mají pole po zdědění vyplněné, z jejich celkového
počtu. Pravidla dědění MUST být stejná jako u chybějících údajů na
ploše. Má-li akce zjištěné osoby a stav *obličeje rozpoznány* (viz
`immich-people`), SHALL hotovost uvádět i osoby: pojmenované ze všech
neskrytých. Dokončená akce SHALL na kartě uvádět stav v Immichi
(viz `immich-people`) pro každého přihlášeného uživatele. Při nepojmenovaných
osobách SHALL karta archiváři a adminovi nabídnout nástroj pojmenování
osob. U akce *hotovo* SHALL hotovost uvádět i stav exportu (aktuální,
nebo „změněno po exportu“). Akce *nezpracováno* hotovost nemá; karta
SHALL místo ní nabídnout zahájení zpracování (odkaz na plochu, která
spustí průvodce). Výpočet MUST NOT číst soubory archivu kromě
`_metadata.json` a výpisu složky ani se ptát Immiche.

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

#### Scenario: Osoby akce
- **WHEN** u akce je uloženo 4 pojmenované z 6 osob a kartu vidí
  archivář
- **THEN** karta uvádí osoby 4/6 a odkaz na nástroj pojmenování osob

#### Scenario: Rozpoznávání probíhá
- **WHEN** dokončená akce je ve stavu „Rozpoznávání obličejů probíhá“
- **THEN** karta ukáže tento stav a osoby do hotovosti nepočítá

#### Scenario: Akce bez zjištěných osob
- **WHEN** akce nemá album v Immichi
- **THEN** karta osoby neuvádí a do hotovosti je nepočítá

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
`file-integrity`) zobrazit na kartě odznak „N poškozených“. Plocha
akce SHALL tentýž souhrn zobrazovat v liště. Odznak MUST být čistě
informační — nezabraňuje prohlížení ani ukládání.

#### Scenario: Odznak v seznamu
- **WHEN** akce má 2 poškozené soubory v souhrnu
- **THEN** karta akce v seznamu má odznak „2 poškozené“

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
