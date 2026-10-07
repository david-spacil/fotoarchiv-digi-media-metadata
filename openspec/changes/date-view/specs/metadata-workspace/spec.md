## MODIFIED Requirements

### Requirement: Mřížka a výběr
Pracovní plocha SHALL zobrazit náhledy rozdělené podle skupin, nebo
podle dnů (viz Zobrazení podle data). Uživatel SHALL moci vybrat jeden
soubor kliknutím, přidat do výběru s modifikátorem, vybrat rozsah se
Shiftem, vybrat tažením myši a v zobrazení po skupinách vybrat celou
skupinu kliknutím na její hlavičku.

#### Scenario: Výběr rozsahu
- **WHEN** uživatel klikne na první soubor a se Shiftem na pátý
- **THEN** je vybráno pět souborů

#### Scenario: Rozsah v zobrazení podle data
- **WHEN** v zobrazení podle data uživatel klikne na první soubor a se
  Shiftem na pátý a soubory patří do dvou různých skupin
- **THEN** je vybráno pět souborů, které jsou v mřížce mezi nimi

## ADDED Requirements

### Requirement: Přepínač zobrazení
Pracovní plocha SHALL mít přepínač Po skupinách / Podle data, který
platí pro mřížku i filmový pás. Výběr a aktuální soubor MUST zůstat při
přepnutí zachované. Volba SHALL platit v tomtéž prohlížeči i pro další
otevřené akce a po obnovení stránky. Průvodce prvním otevřením SHALL
zobrazovat soubory vždy po skupinách.

#### Scenario: Přepnutí s výběrem
- **WHEN** jsou v zobrazení po skupinách vybrané tři soubory a uživatel
  přepne na Podle data
- **THEN** mřížka ukáže soubory podle data a tytéž tři soubory jsou
  vybrané

#### Scenario: Volba přetrvá
- **WHEN** uživatel zvolí Podle data, vrátí se na seznam akcí
  a otevře jinou akci
- **THEN** plocha nové akce je v zobrazení podle data

#### Scenario: Průvodce
- **WHEN** je zvoleno Podle data a uživatel poprvé otevře akci
- **THEN** krok Načtení a skupiny ukazuje soubory po skupinách

### Requirement: Zobrazení podle data
V zobrazení podle data SHALL plocha ukázat všechny soubory akce v jednom
pořadí podle zděděného data pořízení, při shodě podle názvu souboru,
rozdělené předěly po kalendářních dnech. Hlavička dne SHALL ukázat den
v týdnu, datum a počet souborů. Soubory bez data SHALL být na konci
v oddílu „Bez data“. Klik na hlavičku dne nebo „Bez data“ SHALL vybrat
soubory oddílu.

#### Scenario: Dva přístroje téhož dne
- **WHEN** akce má skupiny `Panasonic DC-G9` a `samsung SM-A528B`
  a obě obsahují fotky z 28. 4. 2026
- **THEN** pod hlavičkou `út 28. 4. 2026` jsou fotky obou skupin
  promíchané podle času pořízení

#### Scenario: Vícedenní akce
- **WHEN** soubory akce mají data 27. a 28. 4. 2026
- **THEN** mřížka má dva oddíly, nejdřív 27. 4., pak 28. 4.

#### Scenario: Soubor bez data
- **WHEN** soubor nemá datum pořízení ani zděděné od skupiny či akce
- **THEN** je v posledním oddílu „Bez data“

#### Scenario: Datum bez času
- **WHEN** soubor `IMG-20260428-WA0003.jpg` má datum `2026-04-28` bez
  času
- **THEN** je v oddílu 28. 4. 2026 před soubory téhož dne s časem

#### Scenario: Výběr dne
- **WHEN** uživatel klikne na hlavičku `út 28. 4. 2026`
- **THEN** jsou vybrané všechny soubory toho dne a formulář upravuje
  soubory

### Requirement: Značka autorů na dlaždici
Na pracovní ploše SHALL dlaždice v mřížce i v pásu nést pruh
podle výsledných autorů souboru. Každá osoba akce MUST mít jednu barvu;
pruh se dělí na stejné úseky v barvách autorů, nejvýš tři, další autoři
SHALL tvořit jeden šedý úsek. Soubor bez autorů SHALL mít šrafovaný
pruh. Popisek dlaždice v mřížce SHALL uvést příjmení autorů. Soubor
k vyřazení a průvodce značku nemají.

#### Scenario: Autor ze skupiny
- **WHEN** skupina `Panasonic DC-G9` má autora `Testová, Jana`
  a soubory skupiny autory nepřepisují
- **THEN** všechny dlaždice skupiny mají jednobarevný pruh téže barvy
  a v popisku `Testová`

#### Scenario: Dva autoři
- **WHEN** soubor má autory `Testová, Jana` a `Zkušební, Petr`
- **THEN** pruh má dva stejně dlouhé úseky v barvách obou osob, tytéž
  barvy mají jejich ostatní soubory

#### Scenario: Víc než tři autoři
- **WHEN** soubor má pět autorů
- **THEN** pruh má tři barevné úseky a jeden šedý, popisek uvede tři
  příjmení a `+2` a titulek dlaždice všech pět jmen

#### Scenario: Soubor bez autorů
- **WHEN** soubor nemá autory ani zděděné od skupiny či akce
- **THEN** jeho pruh je šrafovaný a v popisku je `bez autorů`

#### Scenario: Jiný zápis téže osoby
- **WHEN** jeden soubor má autora `Spáčil, David` a jiný `spacil, david`
- **THEN** oba pruhy mají tutéž barvu

#### Scenario: Změna autorů skupiny
- **WHEN** uživatel u skupiny přidá autora
- **THEN** pruhy souborů skupiny, které autory nepřepisují, se hned
  překreslí

#### Scenario: Soubor k vyřazení
- **WHEN** soubor je označený k vyřazení
- **THEN** jeho dlaždice nemá pruh autorů

#### Scenario: Autoři v zobrazení podle data
- **WHEN** v zobrazení podle data leží pod jedním dnem soubory dvou
  skupin s různými autory
- **THEN** jejich dlaždice mají pruhy v barvách svých autorů a popisek
  neuvádí název skupiny
