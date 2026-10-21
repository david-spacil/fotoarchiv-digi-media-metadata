## ADDED Requirements

### Requirement: Rámečky obličejů
Lupa SHALL u aktuální fotky ukázat rámeček kolem každého obličeje
z jejích `obliceje`, a to jen tehdy, když je kurzor nad fotkou nebo nad
jménem osoby ve formuláři; jinak MUST NOT být rámečky vidět. Rámeček
SHALL ohraničit `oblast` vztaženou k fotce zobrazené se správnou
orientací a MUST sedět na fotce při jakékoli velikosti okna. Video
a soubor bez `obliceje` rámečky nemají.

#### Scenario: Kurzor nad fotkou
- **WHEN** aktuální fotka má obličeje `Vzorný, Tomáš`
  a `Ukázková, Věra` a uživatel najede kurzorem na fotku
- **THEN** lupa ukáže dva rámečky a po odjetí kurzoru z fotky zmizí

#### Scenario: Poloha rámečku
- **WHEN** fotka 2000 × 1000 má obličej s `oblast`
  `[0.5, 0.4, 0.1, 0.2]` a kurzor je nad ní
- **THEN** rámeček má střed na 1000, 400 a velikost 200 × 200 pixelů
  fotky

#### Scenario: Otočená fotka
- **WHEN** fotka má EXIF orientaci 6 (uložená na šířku, zobrazená na
  výšku) a obličej s `oblast` vztaženou k fotce na výšku
- **THEN** rámeček je na obličeji ve fotce zobrazené na výšku

#### Scenario: Změna velikosti okna
- **WHEN** jsou rámečky vidět a uživatel zúží okno tak, že se fotka
  zmenší
- **THEN** rámečky se zmenší s fotkou a zůstanou na obličejích

#### Scenario: Video
- **WHEN** aktuální soubor je video a kurzor je nad přehrávačem
- **THEN** lupa žádné rámečky neukáže

### Requirement: Rámeček a jméno ve formuláři
Při kurzoru nad rámečkem SHALL lupa u rámečku ukázat štítek se jménem
osoby a formulář SHALL to jméno zvýraznit; ostatní rámečky nemají
štítek. Při kurzoru nad jménem ve formuláři SHALL lupa ukázat
zvýrazněné jen rámečky té osoby na aktuální fotce, i je-li na ní víc
než jednou.

#### Scenario: Najetí na rámeček
- **WHEN** kurzor je nad rámečkem obličeje `Vzorný, Tomáš`
- **THEN** u rámečku je štítek `Vzorný, Tomáš`, u ostatních rámečků
  štítek není a formulář zvýrazní jméno `Vzorný, Tomáš`

#### Scenario: Najetí na jméno
- **WHEN** aktuální fotka má obličeje `Vzorný, Tomáš` a `Ukázková,
  Věra` a uživatel najede ve formuláři na jméno `Ukázková, Věra`
- **THEN** lupa ukáže zvýrazněný jen rámeček `Ukázková, Věra`

#### Scenario: Osoba na fotce dvakrát
- **WHEN** aktuální fotka má dva obličeje se jménem `Vzorný, Tomáš`
  a uživatel najede ve formuláři na to jméno
- **THEN** lupa ukáže oba rámečky `Vzorný, Tomáš`

### Requirement: Jména mimo aktuální fotku
Ve výběru více souborů SHALL formulář v lupě ztlumit jména osob, která
nejsou mezi obličeji aktuální fotky. Najetí na ztlumené jméno MUST NOT
ukázat žádný rámeček. Ve výběru jednoho souboru a v mřížce SHALL
formulář ukázat jména beze změny.

#### Scenario: Výběr dvou fotek
- **WHEN** v lupě jsou vybrané dvě fotky, aktuální má obličej
  `Vzorný, Tomáš` a druhá `Ukázková, Věra`
- **THEN** formulář ukáže obě jména, `Ukázková, Věra` ztlumené

#### Scenario: Najetí na ztlumené jméno
- **WHEN** uživatel ve výběru dvou fotek najede ve formuláři na
  ztlumené jméno `Ukázková, Věra`
- **THEN** lupa žádný rámeček neukáže

#### Scenario: Mřížka
- **WHEN** v mřížce jsou vybrané tytéž dvě fotky
- **THEN** formulář ukáže obě jména a žádné není ztlumené
