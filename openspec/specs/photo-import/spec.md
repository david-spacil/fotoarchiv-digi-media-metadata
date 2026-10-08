# photo-import Specification

## Purpose

Dostat nové fotky a videa z počítače uživatele do archivu přes
prohlížeč: do stávající nebo nové složky akce, bez přepsání a bez
duplicit.

## Requirements

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
i výběrem), nebo jako zdroj složku v `přetřídit` (viz
`unsorted-import`). Soubory z podsložek vybrané složky SHALL zpracovat,
jako by ležely v jedné úrovni. Nahrané soubory MUST server uložit do
pracovního adresáře mimo archiv a do archivu MUST NOT zapisovat dřív,
než uživatel import potvrdí. Průvodce SHALL ukazovat průběh nahrávání.

#### Scenario: Přerušené nahrávání
- **WHEN** uživatel během nahrávání zavře stránku
- **THEN** archiv zůstane beze změny

#### Scenario: Složka s podsložkou
- **WHEN** uživatel vybere složku s `a.jpg` a `Video/b.mp4`
- **THEN** přehled obsahuje `a.jpg` i `b.mp4`

#### Scenario: Zdroj místo nahrání
- **WHEN** uživatel v kroku Soubory zvolí ze složky `přetřídit` složku
  `HLOZEK`
- **THEN** průvodce nic nenahrává a přejde na přehled souborů
  `HLOZEK`

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

### Requirement: Kontrola souborů v přehledu
Po zobrazení přehledu SHALL průvodce spustit kontrolu podporovaných
souborů importu (podle `file-integrity`) a ukazovat její průběh po
souborech. Přehled SHALL uvést počet podezřelých a nečitelných souborů
a u každého důvod. Pokračovat na plán SHALL jít až po dokončení
kontroly.

#### Scenario: Import s poškozenou fotkou
- **WHEN** uživatel nahraje 40 JPG, mezi nimi `20151107_140851.jpg`
  s nulami na začátku
- **THEN** přehled po kontrole uvede jeden nečitelný soubor s důvodem
  a 39 v pořádku

#### Scenario: Návrat k importu
- **WHEN** uživatel se k rozpracovanému importu vrátí beze změny
  souborů
- **THEN** přehled ukáže výsledky kontroly hned bez nového čtení
### Requirement: Volba u podezřelých souborů
Nečitelný soubor MUST NOT import přenést. Podezřelý soubor MUST NOT
import přenést, pokud ho uživatel v přehledu výslovně nepovolí. Volbu
SHALL server uložit k importu a průvodce ji po návratu předvyplní.

#### Scenario: Výchozí stav
- **WHEN** přehled uvede `20151107_135155.jpg` jako podezřelý
  a uživatel nic nezmění
- **THEN** plán soubor nepřenese

#### Scenario: Povolení
- **WHEN** uživatel u `20151107_135155.jpg` zvolí „přesto importovat“
- **THEN** plán soubor přenese jako ostatní média
### Requirement: Smazání poškozeného souboru importu
U podezřelého i nečitelného souboru SHALL průvodce nabídnout smazání,
které MUST uživatel potvrdit v dialogu se jménem souboru a důvodem.
Nahraný soubor MUST server smazat z pracovního adresáře importu. Smazat
MUST jít jen soubor, který kontrola označila jako poškozený, a jen
dokud se od kontroly nezměnil. Smazání během provedení importu MUST
server odmítnout.

#### Scenario: Smazání nahraného souboru
- **WHEN** uživatel u nečitelného nahraného `20151107_140851.jpg`
  potvrdí smazání
- **THEN** soubor zmizí z pracovního adresáře i z přehledu a archiv se
  nezmění

#### Scenario: Zdravý soubor nejde smazat
- **WHEN** klient pošle požadavek na smazání souboru, který kontrola
  označila jako v pořádku
- **THEN** server požadavek odmítne a soubor zůstane
### Requirement: Volba cíle
Uživatel SHALL zvolit jako cíl stávající akci, nebo novou akci. U nové
akce SHALL průvodce předvyplnit datum nejstarším dnem z nahraných
souborů a vyžádat název. Název složky nové akce MUST odpovídat vzoru
`YYYY-MM-DD název`, MUST NOT obsahovat `/` ani `\`, MUST NOT končit na
`.ignored` a složka stejného názvu MUST NOT existovat s příponou
`.ignored` ani bez ní. V produkčním režimu SHALL import složku nové
akce založit s příponou `.ignored` (viz `event-visibility`). U dokončené
akce SHALL průvodce upozornit, že akce dostane nové soubory bez metadat
a Immich je uvidí hned.

#### Scenario: Návrh data nové akce
- **WHEN** nahrané fotky mají EXIF datum 28. a 29. 4. 2026
- **THEN** průvodce předvyplní datum `2026-04-28`

#### Scenario: Existující název
- **WHEN** uživatel zadá novou akci s názvem složky, která už v archivu
  je
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Existující skrytá akce
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky.ignored`
  a uživatel zadá novou akci `2026-04-28 kontrola Stezky`
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Nová akce skrytá
- **WHEN** uživatel v produkčním režimu importuje do nové akce
  `2026-04-28 kontrola Stezky`
- **THEN** soubory leží ve složce `2026-04-28 kontrola Stezky.ignored`

### Requirement: Plán importu
Pro zvolený cíl SHALL průvodce ukázat plán: média do kořene akce, RAWy
do `RAW.ignored/` (vznikne, pokud chybí). Soubor, jehož cílová cesta už
existuje nebo který má stejné jméno jako jiný soubor ve výběru
(bez ohledu na velikost písmen), MUST být označen jako blokovaný.
Soubor se stejným obsahem (sha256) jako soubor v kořeni cílové akce
nebo jako jiný soubor výběru MUST být označen jako duplicita
a přeskočen. Během výpočtu plánu SHALL průvodce ukazovat průběh
porovnání s cílovou akcí a MUST NOT dovolit spustit výpočet znovu.

#### Scenario: Plán do velké akce na síťovém disku
- **WHEN** uživatel nechá ukázat plán do akce, kde je 900 MB souborů
  stejné velikosti jako nahrané
- **THEN** průvodce ukazuje průběh porovnání, tlačítko je do konce
  výpočtu zablokované a server počítá plán jen jednou

#### Scenario: Kolize jména
- **WHEN** cílová akce obsahuje `P1503712.JPG` s jiným obsahem
  a výběr také `P1503712.JPG`
- **THEN** plán soubor označí jako blokovaný kolizí

#### Scenario: Duplicita s jiným jménem
- **WHEN** výběr obsahuje `kopie.jpg` se stejným obsahem jako
  `P1503712.JPG` v kořeni cílové akce
- **THEN** plán soubor označí jako duplicitu a nepřenese ho

### Requirement: Poškozené soubory v plánu a výsledku
Plán SHALL server sestavit s výsledky kontroly; soubor, který se od
kontroly změnil, MUST zkontrolovat znovu. Plán i výsledek SHALL uvést
nepřenesené poškozené soubory jako samostatnou skupinu s důvodem.
Nepřenesené poškozené soubory MUST zůstat v pracovním adresáři, dokud
uživatel import nezahodí nebo je nesmaže.

#### Scenario: Výsledek s poškozeným souborem
- **WHEN** import 40 JPG s jedním nečitelným skončí
- **THEN** výsledek uvede 39 přenesených a jeden poškozený nepřenesený
  soubor s důvodem
### Requirement: Provedení importu
V produkčním režimu SHALL průvodce po potvrzení plán provést. Server
MUST plán sestavit znovu těsně před provedením a přenést jen
neblokované soubory, které nejsou duplicitou. Přenos MUST NOT přepsat
existující soubor. Přenesený soubor MUST mít stejný obsah a čas změny
jako nahraný originál. U nové akce server SHALL vytvořit složku akce;
pokud mezitím vznikla, import MUST odmítnout. Během provedení SHALL
průvodce ukazovat průběh podle objemu přenesených dat. Ve vývojovém
režimu SHALL průvodce plán jen zobrazit a do archivu nic nezapsat.

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu potvrdí import 40 JPG a 40 RW2
  do nové akce `2026-04-28 kontrola Stezky`
- **THEN** složka vznikne, 40 JPG je v jejím kořeni, 40 RW2
  v `RAW.ignored/` a akce je v seznamu jako *nezpracováno*

#### Scenario: Průběh u velkého videa
- **WHEN** uživatel importuje video o velikosti 10 GB
- **THEN** ukazatel průběhu se posouvá i během kopírování tohoto souboru
  a ukazuje data skutečně zapsaná do archivu, ne do cache

#### Scenario: Zavření stránky během provedení
- **WHEN** uživatel během kopírování do archivu zavře stránku
- **THEN** přenesené soubory jsou v archivu celé, rozkopírovaný soubor
  v archivu nezůstane a nepřenesené zůstanou v pracovním adresáři

#### Scenario: Dočasný soubor po výpadku síťového disku
- **WHEN** v akci zůstal po výpadku spojení dočasný soubor importu
  starší než hodina a uživatel do akce znovu importuje
- **THEN** server dočasný soubor před kopírováním smaže a výsledek to
  uvede

#### Scenario: Kolize vzniklá po zobrazení plánu
- **WHEN** mezi zobrazením plánu a potvrzením vznikne v cílové akci
  soubor stejného jména
- **THEN** ten soubor se nepřenese a výsledek ho uvede jako blokovaný

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu dojde k potvrzení
- **THEN** průvodce ukáže plán a archiv zůstane beze změny

### Requirement: Ověření velikosti po přenosu
Po přenosu každého souboru SHALL server porovnat velikost souboru
v cíli s velikostí originálu. Nesoulad MUST výsledek uvést u souboru
jako chybu přenosu; soubor v archivu MUST NOT server smazat.

#### Scenario: Nesouhlasná velikost
- **WHEN** soubor má po přenosu v cíli jinou velikost než originál
- **THEN** výsledek ho uvede s chybou „velikost v cíli nesouhlasí“
  a soubor zůstane v archivu
### Requirement: Výsledek importu
Po provedení SHALL průvodce ukázat přenesené, blokované, duplicitní
a selhané soubory (s chybou). Selhání jednoho souboru MUST NOT zastavit
ostatní. Úspěšně přenesené soubory MUST server z pracovního adresáře
odstranit; nepřenesené SHALL zůstat, dokud uživatel import nezahodí.
U importu ze zdroje v `přetřídit` SHALL výsledek uvést, co ve zdroji
zůstalo a zda zdrojová složka zanikla; import, ve kterém nezůstal žádný
přenositelný soubor, SHALL server zrušit. Průvodce SHALL nabídnout
otevřít cílovou akci.

#### Scenario: Otevření akce po importu
- **WHEN** import do stávající akce s `_metadata.json` skončí
- **THEN** po otevření akce jsou přenesené soubory mezi novými soubory
  akce

#### Scenario: Zbytky zdroje ve výsledku
- **WHEN** import ze složky `DOD 2016` přesune všechna média a zbyde
  jeden `.docx`
- **THEN** výsledek uvede, že ve zdroji zůstal jeden soubor a složka
  `DOD 2016` zůstala

### Requirement: Rozpracované importy
Import SHALL patřit uživateli (jménu), pod kterým vznikl, ne záložce
prohlížeče. Seznam akcí SHALL ukázat rozpracované importy uživatele
(kdy vznikly, počet a velikost souborů, zamýšlený cíl, poslední
aktivita) s možností pokračovat nebo import zahodit. Import jiného
uživatele MUST NOT být vidět ani dostupný. Zvolený cíl SHALL průvodce
po návratu předvyplnit. Během provedení importu MUST server odmítnout
nahrávání, zahození i další provedení téhož importu. Nahrává-li se
nebo kopíruje-li se import v jiné záložce, průvodce SHALL na to
upozornit (u nahrávání se jménem souboru a přijatým objemem).

#### Scenario: Pokračování ze zavřené záložky
- **WHEN** uživatel nahraje soubory, zavře záložku a v nové záložce
  otevře seznam akcí
- **THEN** seznam ukáže jeho rozpracovaný import a po kliknutí na
  Pokračovat průvodce naskočí na přehled se stejnými soubory

#### Scenario: Cizí import
- **WHEN** jiný uživatel otevře seznam akcí nebo adresu cizího importu
- **THEN** import nevidí a průvodce ohlásí, že import nenalezl

#### Scenario: Nahrávání v jiné záložce
- **WHEN** uživatel nahrává velké video a otevře týž import v druhé
  záložce
- **THEN** druhá záložka upozorní, že se v jiné záložce nahrává video,
  a poradí počkat nebo původní záložku zavřít

#### Scenario: Provedení ve dvou záložkách
- **WHEN** uživatel spustí provedení importu a v jiné záložce ho zkusí
  provést nebo zahodit znovu
- **THEN** druhá záložka dostane odmítnutí a archiv obsahuje každý
  soubor nejvýš jednou

### Requirement: Zahození importu
Uživatel SHALL moci rozpracovaný import zahodit; server MUST pak
smazat jeho soubory z pracovního adresáře. U importu ze zdroje
v `přetřídit` MUST zahození zdroj ponechat beze změny. Importy
neaktivní déle než 7 dní SHALL server smazat při startu.

#### Scenario: Zahození před potvrzením
- **WHEN** uživatel po nahrání import zahodí
- **THEN** pracovní adresář importu je smazaný a archiv beze změny

#### Scenario: Zahození importu ze zdroje
- **WHEN** uživatel zahodí import ze složky `FotoKoule`
- **THEN** složka `přetřídit/FotoKoule` zůstane beze změny

### Requirement: Volba skupin
V kroku volby cíle SHALL průvodce nabídnout rozdělení importovaných
médií do skupin:
- **podle podsložek** — jen má-li výběr podsložky. Kořen výběru je
  nejdelší společná složka všech nahraných souborů. Skupinu tvoří každá
  podsložka první úrovně pod kořenem (soubory z hlubších podsložek
  patří k ní), skupina dostane její název. Soubory přímo v kořeni
  dostanou skupinu pojmenovanou po kořeni, nebo zůstanou bez skupiny,
  je-li kořen prázdný.
- **jedna nová skupina** — název SHALL průvodce předvyplnit názvem
  kořene výběru, jinak `Import YYYY-MM-DD` (den importu); prázdný název
  MUST odmítnout.
- **automaticky** — podle přístroje a vzoru názvu jako návrh skupin
  u nové akce.
- **bez skupiny**.
- **zařadit do skupiny …** — jen u akce, jejíž `_metadata.json` má
  skupiny; uživatel zvolí jednu z nich.

Předvolba SHALL být „podle podsložek“, má-li výběr podsložky; jinak
„automaticky“ u nové akce a akce bez `_metadata.json`, „jedna nová
skupina“ u akce s `_metadata.json`. Volba se týká jen fotek a videí,
RAWy (do `RAW.ignored/`) skupinu nedostanou. Zvolené rozdělení SHALL
průvodce po návratu k rozpracovanému importu předvyplnit.

#### Scenario: Podsložky od autorů
- **WHEN** uživatel nahraje složku `DOD 2015` s podsložkami
  `DOD 2015_Jana` a `DOD 2015_Pavla`
- **THEN** předvolba je „podle podsložek“ a plán uvede skupiny
  `DOD 2015_Jana` a `DOD 2015_Pavla`, každou se soubory své podsložky,
  i když jsou v jedné podsložce fotky ze dvou přístrojů

#### Scenario: Výběr bez podsložek
- **WHEN** uživatel vybere jednotlivé soubory a cílem je stávající akce
  s `_metadata.json`
- **THEN** volba „podle podsložek“ chybí a předvolba je „jedna nová
  skupina“ s názvem `Import` a dnešním datem

#### Scenario: Zařazení do stávající skupiny
- **WHEN** cílová akce má skupiny `g9` a `mobil` a uživatel zvolí
  „zařadit do skupiny“ `g9`
- **THEN** plán uvede u všech importovaných médií skupinu `g9`

### Requirement: Skupiny ve stávající akci
Má-li cílová akce skupiny (v `_metadata.json`, nebo v návrhu skupin
z dřívějšího importu do akce bez něj), MUST import nově navrženou
skupinu sám nepřipojit k existující, ani při shodě názvu nebo přístroje.
Plán SHALL u každé nově navržené skupiny nabídnout volbu „nová skupina“
nebo „připojit ke skupině …“ (kterákoli existující). Předvolba MUST být
„nová skupina“. Existující skupinu se shodným názvem (bez ohledu na
velikost písmen a diakritiku) nebo se stejným přístrojem SHALL plán
u volby uvést jako možnou shodu. Název nové skupiny MUST být odlišný od
názvů existujících skupin; při shodě dostane pořadové číslo. Změna
připojení MUST NOT vyžadovat nové sestavení plánu. Uvnitř jednoho
importu se soubory slučují podle zvoleného režimu bez ptaní (např.
automaticky dva telefony stejného modelu do jedné skupiny).

#### Scenario: Podsložka se jménem existující skupiny
- **WHEN** akce má skupinu `DOD 2015_Jana` a uživatel do ní importuje
  podsložky `DOD 2015_Jana` a `DOD 2015_Verca`
- **THEN** plán navrhne dvě nové skupiny, u `DOD 2015_Jana` uvede
  shodu s existující skupinou a připojí ji, jen když to uživatel zvolí

#### Scenario: Stejný přístroj, jiný autor
- **WHEN** akce má skupinu s přístrojem `Samsung SM-A515F` a import
  automaticky obsahuje fotky ze stejného modelu
- **THEN** fotky po importu tvoří novou skupinu, pokud uživatel
  v plánu nezvolil připojení

#### Scenario: Zvolené připojení
- **WHEN** uživatel v plánu u navržené skupiny `DOD 2015_Jana` zvolí
  „připojit ke skupině `DOD 2015_Jana`“ a import provede
- **THEN** přenesené soubory patří do existující skupiny a nová
  skupina nevznikne

### Requirement: Skupiny v plánu
Plán importu SHALL u každého přenášeného média ukázat cílovou skupinu
a odlišit nové skupiny od existujících. Plán SHALL vycházet z aktuální
volby skupin; změna režimu MUST plán sestavit znovu.

#### Scenario: Existující skupina v plánu
- **WHEN** uživatel zvolí „zařadit do skupiny“ `g9` v akci, která ji má
- **THEN** plán uvede `g9` jako existující skupinu, ne novou

### Requirement: Zápis skupin při provedení
Po provedení importu SHALL server zapsat zvolené skupiny pro skutečně
přenesená média; blokované, duplicitní a selhané soubory MUST NOT
dostat záznam. U akce s `_metadata.json` SHALL server nové skupiny
a přiřazení zapsat do `_metadata.json` (přenesené soubory včetně
technických údajů, jako by je přidalo otevření akce). Stávající
záznamy souborů a údaje skupin MUST zůstat beze změny. U akce bez
`_metadata.json` MUST server `_metadata.json` nevytvořit; místo toho
SHALL uložit návrh skupin do pracovního adresáře k akci (další import
do téže akce návrh doplní). Nepodaří-li se skupiny zapsat, přenesené
soubory MUST zůstat v archivu a výsledek SHALL uvést, že soubory jsou
bez skupiny.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` do akce ve stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a lišta je neuvádí jako soubory bez skupiny

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel importuje složku `DOD 2015` s podsložkami do nové
  akce
- **THEN** `_metadata.json` nevznikne a akce je v seznamu jako
  *nezpracováno*

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a v plánu nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe
