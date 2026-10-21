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
- **WHEN** uživatel na ploše akce `2026-04-28 kontrola Naučné stezky…` spustí
  import
- **THEN** průvodce má jako cíl předvybranou tuto akci

### Requirement: Kroky průvodce importem
Průvodce importem SHALL mít kroky v pořadí: soubory → přehled → cíl →
plán → skupiny a autoři → výsledek. Provedení importu SHALL spouštět
tlačítko kroku skupiny a autoři, ne krok plán. Plán (duplicity,
blokované a poškozené soubory) MUST předcházet popisu, aby se
popisovala jen média, která se přenesou.

#### Scenario: Duplicita se nepopisuje
- **WHEN** plán označí 3 z 50 souborů jako duplicity a uživatel
  pokračuje
- **THEN** krok skupiny a autoři ukáže jen 47 přenášených médií

#### Scenario: Provedení až po popisu
- **WHEN** uživatel v produkčním režimu je v kroku plán
- **THEN** krok nabízí jen pokračování ke skupinám a autorům, import
  se ještě neprovádí

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
  `VZORNY`
- **THEN** průvodce nic nenahrává a přejde na přehled souborů
  `VZORNY`

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
Uživatel SHALL zvolit jako cíl stávající akci, kterou smí upravit (viz
`user-login`), nebo novou akci. Akci, kterou upravit nesmí, MUST
průvodce nenabídnout a server MUST import do ní odmítnout s 403. U nové
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
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky.ignored`
  a uživatel zadá novou akci `2026-04-28 kontrola Naučné stezky`
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Nová akce skrytá
- **WHEN** uživatel v produkčním režimu importuje do nové akce
  `2026-04-28 kontrola Naučné stezky`
- **THEN** soubory leží ve složce `2026-04-28 kontrola Naučné stezky.ignored`

#### Scenario: Cizí akce jako cíl
- **WHEN** uživatel bez role vybírá stávající akci a akce
  `2026-04-28 kontrola Naučné stezky` jeho jméno v `upravili` nemá
- **THEN** průvodce ji mezi cíli nenabídne

### Requirement: Údaje nové akce v cíli
U nové akce SHALL krok cíl kromě data a názvu složky nabídnout údaje
akce: název, datum od–do, popis, místa a účastníky. Název akce SHALL
průvodce předvyplnit názvem ze složky (bez data), datum od–do
nejstarším a nejnovějším dnem médií z přehledu. Pokračovat MUST jít
jen s vyplněným názvem a datem od. U stávající akce krok údaje akce
nenabízí.

#### Scenario: Předvyplnění údajů nové akce
- **WHEN** nahrané fotky mají EXIF data 28. a 29. 4. 2026 a uživatel
  zadá název složky `kontrola Naučné stezky`
- **THEN** údaje akce mají název `kontrola Naučné stezky`, datum od
  `2026-04-28` a datum do `2026-04-29`

#### Scenario: Stávající akce
- **WHEN** cílem je stávající akce
- **THEN** krok cíl údaje akce nenabízí

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
V produkčním režimu SHALL průvodce po potvrzení v kroku skupiny
a autoři plán provést. Server MUST plán sestavit znovu těsně před
provedením a přenést jen neblokované soubory, které nejsou duplicitou.
Přenos MUST NOT přepsat existující soubor. Přenesený soubor MUST mít
stejný obsah a čas změny jako nahraný originál. U nové akce server
SHALL vytvořit složku akce; pokud mezitím vznikla, import MUST
odmítnout. Během provedení SHALL průvodce ukazovat průběh podle objemu
přenesených dat. Ve vývojovém režimu SHALL průvodce plán a krok skupiny
a autoři jen zobrazit a do archivu nic nezapsat.

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu potvrdí import 40 JPG a 40 RW2
  do nové akce `2026-04-28 kontrola Naučné stezky`
- **THEN** složka vznikne, 40 JPG je v jejím kořeni, 40 RW2
  v `RAW.ignored/` a akce je v seznamu jako *rozpracováno*

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
- **WHEN** uživatel ve vývojovém režimu dojde k potvrzení v kroku
  skupiny a autoři
- **THEN** průvodce ukáže, co by se zapsalo, a archiv zůstane beze
  změny

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
prohlížeče. Jméno vlastníka SHALL server brát z přihlášení, ne z
požadavku; jen bez přihlášení (vývojový režim) z požadavku. Seznam akcí
SHALL ukázat rozpracované importy uživatele (kdy vznikly, počet a velikost
souborů, zamýšlený cíl, poslední aktivita) s možností pokračovat nebo
import zahodit. Import jiného uživatele MUST NOT být vidět ani dostupný.
Zvolený cíl SHALL průvodce po návratu předvyplnit. Během provedení importu
MUST server odmítnout nahrávání, zahození i další provedení téhož importu.
Nahrává-li se nebo kopíruje-li se import v jiné záložce, průvodce SHALL na
to upozornit (u nahrávání se jménem souboru a přijatým objemem).

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

#### Scenario: Podvržené jméno
- **WHEN** přihlášený uživatel Modelová, Zuzana pošle požadavek na
  import uživatele Příkladný, Daniel se jménem `Příkladný, Daniel` v požadavku
- **THEN** server vrátí 404 a import zůstane beze změny

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
V kroku skupiny a autoři SHALL průvodce nabídnout výchozí rozdělení
importovaných médií do skupin:
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
RAWy (do `RAW.ignored/`) skupinu nedostanou. Změna výchozího rozdělení
SHALL skupiny sestavit znovu; má-li uživatel ruční úpravy nebo autory
skupin, MUST průvodce před tím požádat o potvrzení. Zvolené rozdělení
SHALL průvodce po návratu k rozpracovanému importu předvyplnit.

#### Scenario: Podsložky od autorů
- **WHEN** uživatel nahraje složku `DOD 2015` s podsložkami
  `DOD 2015_Lenka` a `DOD 2015_Olga`
- **THEN** předvolba je „podle podsložek“ a krok skupiny a autoři
  ukáže skupiny `DOD 2015_Lenka` a `DOD 2015_Olga`, každou se soubory
  své podsložky, i když jsou v jedné podsložce fotky ze dvou přístrojů

#### Scenario: Výběr bez podsložek
- **WHEN** uživatel vybere jednotlivé soubory a cílem je stávající akce
  s `_metadata.json`
- **THEN** volba „podle podsložek“ chybí a předvolba je „jedna nová
  skupina“ s názvem `Import` a dnešním datem

#### Scenario: Zařazení do stávající skupiny
- **WHEN** cílová akce má skupiny `g9` a `mobil` a uživatel zvolí
  „zařadit do skupiny“ `g9`
- **THEN** krok skupiny a autoři ukáže všechna importovaná média ve
  skupině `g9` jako existující

#### Scenario: Změna rozdělení po úpravách
- **WHEN** uživatel zadal autory dvou skupin a přepne rozdělení
  z „automaticky“ na „jedna nová skupina“
- **THEN** průvodce se zeptá, zda úpravy zahodit, a bez potvrzení
  skupiny nezmění

### Requirement: Skupiny ve stávající akci
Má-li cílová akce skupiny (v `_metadata.json`, nebo v návrhu skupin
z dřívějšího importu do akce bez něj), MUST import nově navrženou
skupinu sám nepřipojit k existující, ani při shodě názvu nebo přístroje.
Krok skupiny a autoři SHALL u každé nové skupiny nabídnout volbu „nová
skupina“ nebo „připojit ke skupině …“ (kterákoli existující). Předvolba
MUST být „nová skupina“. Existující skupinu se shodným názvem (bez
ohledu na velikost písmen a diakritiku) nebo se stejným přístrojem
SHALL krok u volby uvést jako možnou shodu. Připojená skupina SHALL
ukázat autory existující skupiny jako zděděné a její údaje MUST zůstat
beze změny. Název nové skupiny MUST být odlišný od názvů existujících
skupin; při shodě dostane pořadové číslo. Změna připojení MUST NOT
vyžadovat nové sestavení plánu. Uvnitř jednoho importu se soubory
slučují podle zvoleného rozdělení bez ptaní (např. automaticky dva
telefony stejného modelu do jedné skupiny).

#### Scenario: Podsložka se jménem existující skupiny
- **WHEN** akce má skupinu `DOD 2015_Lenka` a uživatel do ní importuje
  podsložky `DOD 2015_Lenka` a `DOD 2015_Mira`
- **THEN** krok skupiny a autoři navrhne dvě nové skupiny, u `DOD
  2015_Jana` uvede shodu s existující skupinou a připojí ji, jen když
  to uživatel zvolí

#### Scenario: Stejný přístroj, jiný autor
- **WHEN** akce má skupinu s přístrojem `Samsung SM-A515F` a import
  automaticky obsahuje fotky ze stejného modelu
- **THEN** fotky po importu tvoří novou skupinu, pokud uživatel
  nezvolil připojení

#### Scenario: Zvolené připojení
- **WHEN** uživatel v kroku skupiny a autoři u navržené skupiny `DOD
  2015_Jana` zvolí „připojit ke skupině `DOD 2015_Lenka`“ a import
  provede
- **THEN** přenesené soubory patří do existující skupiny, nová skupina
  nevznikne a autoři existující skupiny se nezmění

### Requirement: Skupiny a autoři v importu
Krok skupiny a autoři SHALL ukázat náhledy přenášených médií (fotky
a videa, ne RAWy) rozdělené do skupin podle výchozího rozdělení (viz
Volba skupin). Uživatel SHALL moci skupinu přejmenovat, sloučit
s jinou, vytvořit novou z vybraných médií a přesunout do ní vybraná
média, a každé skupině zadat autory. Autory celé akce krok MUST NOT
nabízet, ani u nové, ani u stávající akce. Jména autorů SHALL mít
kanonický tvar a návrhy jako jinde v aplikaci.

Má-li některá skupina přenášených médií prázdné autory, SHALL import
na to před provedením upozornit a provést se až po druhém potvrzení
(jako dokončení průvodce akce).

Údaje akce, skupiny, přiřazení a autory SHALL průvodce průběžně ukládat
k importu (ne do archivu) a po návratu k rozpracovanému importu je
předvyplnit. Změní-li se plán, média, která se už nepřenesou, MUST
ze skupin vypadnout a nově přenášená média SHALL dostat skupinu podle
výchozího rozdělení; ruční úpravy ostatních médií MUST zůstat.

#### Scenario: Ruční úprava automatické skupiny
- **WHEN** automatické rozdělení dá do jedné skupiny fotky dvou
  fotografů se stejným modelem telefonu a uživatel vybere fotky
  jednoho z nich a vytvoří z nich novou skupinu
- **THEN** krok ukáže dvě skupiny a každé jde zadat jiné autory

#### Scenario: Autoři celé akce
- **WHEN** uživatel importuje další fotky do akce, jejíž skupiny mají
  autory, a nové skupině zadá autorku `Modelová, Zuzana`
- **THEN** krok se na autory celé akce neptá, import se provede bez
  upozornění a autoři existujících skupin se nezmění

#### Scenario: Skupina bez autorů
- **WHEN** jedna nová skupina nemá autory a uživatel klikne na import
- **THEN** průvodce upozorní na skupinu bez autorů a import provede až
  po druhém kliknutí

#### Scenario: Návrat k rozpracovanému importu
- **WHEN** uživatel zadá autory dvou skupin, zavře stránku a import
  později otevře přes Pokračovat
- **THEN** krok skupiny a autoři ukáže tytéž skupiny s týmiž autory

### Requirement: Náhledy souborů importu
Server SHALL dodat náhled nahraného souboru importu i souboru zdroje
v `přetřídit` ve stejných velikostech jako náhledy souborů akce, jen
majiteli importu. Náhled MUST NOT zapsat nic do archivu ani do zdroje.

#### Scenario: Náhled ze zdroje přetřídit
- **WHEN** krok skupiny a autoři ukazuje média importu ze složky
  `přetřídit/DOD 2016`
- **THEN** dlaždice mají náhledy a složka `DOD 2016` zůstane beze
  změny

#### Scenario: Cizí import
- **WHEN** uživatel požádá o náhled souboru importu jiného uživatele
- **THEN** server odpoví, že import nenašel

### Requirement: Zápis skupin při provedení
Po provedení importu SHALL server zapsat skupiny, přiřazení a autory
skupin z kroku skupiny a autoři pro skutečně přenesená média;
blokované, duplicitní a selhané soubory MUST NOT dostat záznam.
Skupina, které po provedení nezůstal žádný přenesený soubor, MUST NOT
vzniknout. Autory celé akce MUST NOT zapsat (ani ze staršího
rozpracovaného importu).

- **Nová akce:** server SHALL založit `_metadata.json` s údaji akce
  z kroku cíl, skupinami a přenesenými soubory včetně technických
  údajů, jako by je přidalo otevření akce. Akce je pak *rozpracovaná*.
- **Akce s `_metadata.json`:** server SHALL zapsat nové skupiny s autory
  a přiřazení přenesených souborů. Stávající záznamy souborů a údaje
  akce a existujících skupin MUST zůstat beze změny.
- **Existující akce bez `_metadata.json`:** server MUST `_metadata.json`
  nevytvořit; SHALL uložit návrh skupin (skupiny s autory a přiřazení)
  do pracovního adresáře k akci (další import do téže akce návrh
  doplní).

Zápis do `_metadata.json` (nová akce i akce s ním) SHALL do `upravili`
doplnit jméno uživatele, který import provedl (viz `metadata-model`).

Nepodaří-li se popis zapsat, přenesené soubory MUST zůstat v archivu
a výsledek SHALL uvést, že soubory jsou bez skupiny a autorů.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` s autorem `Modelová, Zuzana` do akce ve
  stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a autorkou `Modelová, Zuzana` a navigátor je neuvádí jako soubory
  bez skupiny ani skupinu bez autorů

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu importuje složku `DOD 2015`
  s podsložkami do nové akce a zadá údaje akce a autory skupin
- **THEN** akce má `_metadata.json` s těmito údaji, bez `akce.autori`
  a se jménem uživatele v `upravili`, je v seznamu jako *rozpracováno*
  a její otevření vede rovnou na pracovní plochu

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe, každou se
  svými autory

#### Scenario: Rozpracovaný import s autory akce
- **WHEN** rozpracovaný import z doby před změnou má uložené autory
  celé akce a uživatel ho provede do akce s `_metadata.json`
- **THEN** `akce` v `_metadata.json` se nezmění

### Requirement: Fotky s odebranou polohou
Fotka má **odebranou polohu**, když její EXIF obsahuje blok GPS
s `GPSVersionID` rovným `0 0 0 0` a bez číselné zeměpisné šířky
i délky. Import MUST NOT takovou fotku přenést, a to ani u importu
nahráním, ani ze složky `přetřídit`; uživatel ji MUST NOT moci povolit.
Přehled SHALL fotky s odebranou polohou vypsat s důvodem („telefon
odebral polohu“) a vysvětlením, že originál je potřeba předat jinou
cestou. Plán i výsledek SHALL je uvést jako samostatnou skupinu
nepřenesených. Nepřenesené MUST zůstat v pracovním adresáři, nebo ve
zdroji v `přetřídit`, dokud uživatel import nezahodí. Fotka bez bloku
GPS a fotka s číselnými souřadnicemi MUST se importovat jako dosud.

#### Scenario: Fotka z telefonu přes prohlížeč
- **WHEN** uživatel nahraje `PXL_20260917_132338497.MP.jpg`
  s `GPSVersionID` `0 0 0 0` a prázdnými souřadnicemi
- **THEN** přehled ji uvede jako fotku s odebranou polohou, plán ji
  nepřenese a výsledek ji uvede mezi nepřenesenými s důvodem

#### Scenario: WhatsApp bez polohy
- **WHEN** uživatel nahraje `IMG-20260428-WA0003.jpg` bez bloku GPS
- **THEN** přehled ji jako odebranou polohu neuvede a import ji přenese

#### Scenario: Fotka s polohou
- **WHEN** uživatel nahraje fotku s `GPSVersionID` `2 2 0 0`
  a souřadnicemi 49.13579 N, 16.24680 E
- **THEN** import ji přenese

#### Scenario: Smíšený import
- **WHEN** import obsahuje 30 fotek s polohou a 2 s odebranou polohou
- **THEN** plán přenese 30 fotek a 2 uvede jako nepřenesené s důvodem
  a tlačítko provedení je dostupné

### Requirement: Vyloučení z importu
V kroku skupiny a autoři importu SHALL klávesa Del i tlačítko v panelu
přepínat vyloučení vybraných médií: jsou-li všechna vybraná vyloučená,
vrátí je do importu, jinak je všechna vyloučí. Tlačítko SHALL mít podle
výběru popisek „Vrátit do importu“, nebo „Vyloučit z importu“.
Vyloučené médium SHALL zůstat v mřížce ve své skupině, vizuálně
odlišené, a jde ho kdykoli vrátit.

#### Scenario: Vyloučení dvou fotek
- **WHEN** krok ukazuje 47 přenášených médií a uživatel vybere dvě
  fotky a stiskne Del
- **THEN** obě dlaždice zůstanou ve skupině zašedlé s ikonou vyloučení
  a tlačítko ukáže „Importovat (45)“

#### Scenario: Zrušení vyloučení
- **WHEN** uživatel vybere obě vyloučené fotky a znovu stiskne Del
- **THEN** fotky už vyloučené nejsou a tlačítko ukáže „Importovat (47)“

#### Scenario: Popisek tlačítka
- **WHEN** jsou vybrané jen vyloučené fotky
- **THEN** tlačítko v panelu má popisek „Vrátit do importu“; po přidání
  nevyloučené fotky do výběru „Vyloučit z importu“

#### Scenario: Smíšený výběr
- **WHEN** z vybraných tří fotek je vyloučená jen jedna a uživatel
  klikne na „Vyloučit z importu“
- **THEN** vyloučené jsou všechny tři

### Requirement: Počty a uložení vyloučených
Vyloučená média MUST NOT se počítat do počtu v tlačítku Importovat ani
do upozornění na skupiny bez autorů. Seznam vyloučených SHALL průvodce
ukládat k importu (ne do archivu) i ve vývojovém režimu a po návratu
k rozpracovanému importu i po změně výchozího rozdělení je zachovat.

#### Scenario: Skupina jen z vyloučených
- **WHEN** všechna média skupiny bez autorů jsou vyloučená a uživatel
  klikne na Importovat
- **THEN** průvodce na skupinu bez autorů neupozorní

#### Scenario: Vše vyloučeno
- **WHEN** uživatel stiskne Ctrl+A a pak Del
- **THEN** tlačítko Importovat je vypnuté

#### Scenario: Návrat k rozpracovanému importu
- **WHEN** uživatel vyloučí fotku `P1503712.JPG`, zavře stránku
  a import později otevře přes Pokračovat
- **THEN** krok ukáže `P1503712.JPG` jako vyloučenou

#### Scenario: Změna výchozího rozdělení
- **WHEN** uživatel vyloučí fotku a pak změní výchozí rozdělení do
  skupin
- **THEN** fotka zůstane vyloučená v nové skupině

### Requirement: Vyloučení RAWu k fotce
Má-li vylučovaná fotka ve výběru RAW stejného jména bez přípony ve
stejné složce výběru, který by se přenesl, SHALL průvodce před
vyloučením zobrazit dialog s počtem takových RAWů a volbou, zda je
vyloučit také. Zrušení vyloučení fotky SHALL zrušit i vyloučení jejího
RAWu bez dotazu. Panel kroku SHALL uvést počet vyloučených RAWů.

#### Scenario: Vyloučit i RAW
- **WHEN** uživatel vylučuje `P1503712.JPG` a výběr obsahuje
  `P1503712.RW2` a v dialogu zvolí vyloučit i RAWy
- **THEN** obě se nepřenesou a panel uvede jeden vyloučený RAW

#### Scenario: Jen fotku
- **WHEN** uživatel v tomto dialogu zvolí vyloučit jen fotky
- **THEN** `P1503712.RW2` se přenese do `RAW.ignored/`

#### Scenario: Fotka bez RAWu
- **WHEN** vylučovaná fotka nemá ve výběru RAW stejného jména
- **THEN** průvodce se na nic neptá

#### Scenario: Vrácení fotky
- **WHEN** uživatel zruší vyloučení `P1503712.JPG`, které vyloučil
  spolu s RAWem
- **THEN** přenese se fotka i `P1503712.RW2`

### Requirement: Vyloučené soubory při provedení
Server MUST vyloučený soubor nepřenést a MUST ho nechat v pracovním
adresáři importu, nebo ve zdroji v `přetřídit`, dokud uživatel import
nezahodí. Vyloučený soubor MUST NOT dostat záznam v `_metadata.json`
ani návrhu skupin. Plán i výsledek SHALL uvést vyloučené soubory
zvlášť jako „vyloučeno“. Vyloučení MUST NOT měnit, které soubory plán
označí jako duplicitu nebo blokované.

#### Scenario: Import s vyloučenou fotkou
- **WHEN** uživatel v produkčním režimu importuje 40 nahraných JPG,
  z nich dvě vyloučené
- **THEN** v akci je 38 fotek, výsledek uvede 2 vyloučené a ty zůstanou
  v pracovním adresáři importu, který zůstane mezi rozpracovanými

#### Scenario: Vyloučený soubor ze zdroje
- **WHEN** uživatel importuje složku `přetřídit/DOD 2016` a jednu fotku
  vyloučí
- **THEN** fotka zůstane ve složce `DOD 2016`, výsledek ji uvede mezi
  tím, co ve zdroji zůstalo, a stránka Přetřídit složku dál nabízí

#### Scenario: Plán po návratu
- **WHEN** uživatel po vyloučení fotky přejde zpět na plán a nechá ho
  sestavit znovu
- **THEN** plán uvede fotku jako vyloučenou a v kroku skupiny a autoři
  zůstane vyloučená ve své skupině

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu vyloučí fotku a otevře „Co by
  se zapsalo“
- **THEN** vyloučená fotka v zápisu není a archiv zůstane beze změny
