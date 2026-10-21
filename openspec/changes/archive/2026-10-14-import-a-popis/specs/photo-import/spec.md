## ADDED Requirements

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

### Requirement: Skupiny a autoři v importu
Krok skupiny a autoři SHALL ukázat náhledy přenášených médií (fotky
a videa, ne RAWy) rozdělené do skupin podle výchozího rozdělení (viz
Volba skupin). Uživatel SHALL moci skupinu přejmenovat, sloučit
s jinou, vytvořit novou z vybraných médií a přesunout do ní vybraná
média, a každé skupině zadat autory. Nad skupinami SHALL krok nabídnout
autory celé akce; skupina bez vlastních autorů je zdědí a MUST se
nepočítat mezi skupiny bez autorů. U stávající akce s autory SHALL
nové skupiny bez vlastních autorů ukázat autory akce jako zděděné
a pole autorů celé akce MUST měnit `autori` akce. Jména autorů SHALL
mít kanonický tvar a návrhy jako jinde v aplikaci.

Má-li po zdědění některá skupina přenášených médií prázdné autory,
SHALL import na to před provedením upozornit a provést se až po
druhém potvrzení (jako dokončení průvodce akce).

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
- **WHEN** u nové akce uživatel zadá autory celé akce `Příkladný, Daniel`
  a skupinám nic
- **THEN** import se provede bez upozornění a skupiny autory dědí
  z akce

#### Scenario: Skupina bez autorů
- **WHEN** jedna nová skupina nemá autory ani je nedědí a uživatel
  klikne na import
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

## MODIFIED Requirements

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

### Requirement: Zápis skupin při provedení
Po provedení importu SHALL server zapsat skupiny, přiřazení a autory
z kroku skupiny a autoři pro skutečně přenesená média; blokované,
duplicitní a selhané soubory MUST NOT dostat záznam. Skupina, které
po provedení nezůstal žádný přenesený soubor, MUST NOT vzniknout.

- **Nová akce:** server SHALL založit `_metadata.json` s údaji akce
  z kroku cíl (včetně autorů celé akce), skupinami a přenesenými
  soubory včetně technických údajů, jako by je přidalo otevření akce.
  Akce je pak *rozpracovaná*.
- **Akce s `_metadata.json`:** server SHALL zapsat nové skupiny s autory
  a přiřazení přenesených souborů; autory celé akce, jen když je
  uživatel v kroku změnil. Stávající záznamy souborů a údaje
  existujících skupin MUST zůstat beze změny.
- **Existující akce bez `_metadata.json`:** server MUST `_metadata.json`
  nevytvořit; SHALL uložit návrh skupin (skupiny s autory a přiřazení,
  autory celé akce) do pracovního adresáře k akci (další import do
  téže akce návrh doplní).

Nepodaří-li se popis zapsat, přenesené soubory MUST zůstat v archivu
a výsledek SHALL uvést, že soubory jsou bez skupiny a autorů.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` s autorem `Modelová, Zuzana` do akce ve
  stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a autorkou `Modelová, Zuzana` a lišta je neuvádí jako soubory
  bez skupiny ani skupinu bez autorů

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu importuje složku `DOD 2015`
  s podsložkami do nové akce a zadá údaje akce a autory skupin
- **THEN** akce má `_metadata.json` s těmito údaji, je v seznamu jako
  *rozpracováno* a její otevření vede rovnou na pracovní plochu

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe, každou se
  svými autory

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

## REMOVED Requirements

### Requirement: Skupiny v plánu
**Reason**: Skupiny se volí až v kroku skupiny a autoři po plánu;
plán ukazuje jen přenos (cíl, duplicity, blokované, poškozené).
**Migration**: Cílovou skupinu každého média a odlišení nových
a existujících skupin ukazuje krok skupiny a autoři (viz Skupiny
a autoři v importu, Skupiny ve stávající akci).
