## ADDED Requirements

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
  `DOD 2015_Lenka` a `DOD 2015_Olga`
- **THEN** předvolba je „podle podsložek“ a plán uvede skupiny
  `DOD 2015_Lenka` a `DOD 2015_Olga`, každou se soubory své podsložky,
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
- **WHEN** akce má skupinu `DOD 2015_Lenka` a uživatel do ní importuje
  podsložky `DOD 2015_Lenka` a `DOD 2015_Mira`
- **THEN** plán navrhne dvě nové skupiny, u `DOD 2015_Lenka` uvede
  shodu s existující skupinou a připojí ji, jen když to uživatel zvolí

#### Scenario: Stejný přístroj, jiný autor
- **WHEN** akce má skupinu s přístrojem `Samsung SM-A515F` a import
  automaticky obsahuje fotky ze stejného modelu
- **THEN** fotky po importu tvoří novou skupinu, pokud uživatel
  v plánu nezvolil připojení

#### Scenario: Zvolené připojení
- **WHEN** uživatel v plánu u navržené skupiny `DOD 2015_Lenka` zvolí
  „připojit ke skupině `DOD 2015_Lenka`“ a import provede
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
