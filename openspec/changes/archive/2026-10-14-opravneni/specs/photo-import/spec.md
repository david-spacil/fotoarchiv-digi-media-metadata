## MODIFIED Requirements

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
- **WHEN** přihlášený uživatel Kopáčová, Zuzana pošle požadavek na
  import uživatele Spáčil, David se jménem `Spáčil, David` v požadavku
- **THEN** server vrátí 404 a import zůstane beze změny

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
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky.ignored`
  a uživatel zadá novou akci `2026-04-28 kontrola Stezky`
- **THEN** průvodce název odmítne a nabídne zvolit tu akci jako
  stávající

#### Scenario: Nová akce skrytá
- **WHEN** uživatel v produkčním režimu importuje do nové akce
  `2026-04-28 kontrola Stezky`
- **THEN** soubory leží ve složce `2026-04-28 kontrola Stezky.ignored`

#### Scenario: Cizí akce jako cíl
- **WHEN** uživatel bez role vybírá stávající akci a akce
  `2026-04-28 kontrola Stezky` jeho jméno v `upravili` nemá
- **THEN** průvodce ji mezi cíli nenabídne

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

Zápis do `_metadata.json` (nová akce i akce s ním) SHALL do `upravili`
doplnit jméno uživatele, který import provedl (viz `metadata-model`).

Nepodaří-li se popis zapsat, přenesené soubory MUST zůstat v archivu
a výsledek SHALL uvést, že soubory jsou bez skupiny a autorů.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` s autorem `Kopáčová, Zuzana` do akce ve
  stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a autorkou `Kopáčová, Zuzana` a navigátor je neuvádí jako soubory
  bez skupiny ani skupinu bez autorů

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu importuje složku `DOD 2015`
  s podsložkami do nové akce a zadá údaje akce a autory skupin
- **THEN** akce má `_metadata.json` s těmito údaji a jménem uživatele
  v `upravili`, je v seznamu jako *rozpracováno* a její otevření vede
  rovnou na pracovní plochu

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe, každou se
  svými autory
