## ADDED Requirements

### Requirement: Velikost akce
Velikost akce SHALL být součet velikostí (`st_size`) všech souborů
celé složky akce včetně podsložek (`RAW.ignored` a další `*.ignored`),
souborů označených k vyřazení, `_metadata.json`, sidecarů a
`Thumbs.db`. Symbolické odkazy MUST NOT být sledovány ani započteny.
U akce v kolizi přípony (složka s `.ignored` i bez ní) SHALL velikost
být součtem obou složek.

Velikost SHALL být údaj „k datu“ uložený v pracovním adresáři, ne
v archivu. Výpis seznamu akcí MUST NOT kvůli velikosti číst archiv;
uvádí uložený údaj, nebo žádný. Údaj akce SHALL být přepočítán:
- po změně akce aplikací: import (i z `přetřídit`), úklid,
  dokončení, obnovení z koše;
- u akce bez údaje (nová akce, první spuštění) na pozadí;
- jednou denně pro všechny akce, aby zachytil změny provedené mimo
  aplikaci.

Údaj tak může být až den starý. Přepočet MUST archiv jen číst,
i v produkčním režimu.

#### Scenario: Podsložky a vyřazené soubory
- **WHEN** akce má v kořeni 2 fotky po 1 MB, `_metadata.json`
  o 1 kB a `RAW.ignored` se 2 soubory po 20 MB
- **THEN** velikost akce je 42 001 000 B

#### Scenario: Symbolický odkaz
- **WHEN** složka akce obsahuje symbolický odkaz na složku mimo akci
- **THEN** velikost akce soubory za odkazem nezapočítá

#### Scenario: Kolize přípony
- **WHEN** archiv obsahuje složku akce s 1 GB a stejnojmennou složku
  s příponou `.ignored` s 2 GB
- **THEN** velikost akce je 3 GB

#### Scenario: Přepočet po importu
- **WHEN** import přidá do akce s údajem 1 GB soubory o 500 MB
- **THEN** po doběhnutí přepočtu seznam uvádí u akce 1,5 GB

#### Scenario: Změna mimo aplikaci
- **WHEN** správce přes SMB přidá do podsložky akce soubory
- **THEN** seznam uvádí starý údaj až do denního přepočtu, pak nový

#### Scenario: Akce bez údaje
- **WHEN** v archivu přibude složka nové akce a uživatel otevře seznam
- **THEN** výpis odpoví bez čekání na průchod složkou, karta velikost
  neuvádí a po přepočtu na pozadí ji při dalším načtení uvede

### Requirement: Velikost na kartě a celkový součet
Karta akce SHALL uvádět velikost akce v jednotkách B, kB, MB, GB, TB
(desítkové, s desetinnou čárkou), např.
`2024-05-01 · 132 souborů · 4,2 GB`. Akce bez údaje velikost neuvádí.
Seznam SHALL ukazovat celkový součet velikostí všech akcí archivu
nezávisle na filtru a hledání a zvlášť součet koše, např.
`Celkem 25 GB (+5 GB v koši)`; prázdný koš závorku vynechá. Součet
koše SHALL vidět každý přihlášený uživatel; neobsahuje nic jiného než
číslo. Akce a položky koše bez údaje se do součtu nezapočítají.

#### Scenario: Karta s velikostí
- **WHEN** akce `2024-05-01 exkurze` má 132 souborů a 4 200 000 000 B
- **THEN** karta uvádí `2024-05-01 · 132 souborů · 4,2 GB`

#### Scenario: Součet nezávislý na filtru
- **WHEN** archiv má akce o 20 GB a 5 GB, koš 5 GB a uživatel zvolí
  filtr, který ukazuje jen první akci
- **THEN** seznam uvádí `Celkem 25 GB (+5 GB v koši)`

#### Scenario: Prázdný koš
- **WHEN** koš je prázdný a akce mají celkem 25 GB
- **THEN** seznam uvádí `Celkem 25 GB` bez závorky

#### Scenario: Archivář vidí součet koše
- **WHEN** seznam otevře archivář bez role admin a koš má 5 GB
- **THEN** seznam uvádí `(+5 GB v koši)`, ale odkaz na Koš nemá

## MODIFIED Requirements

### Requirement: Řazení seznamu
Seznam SHALL nabídnout řazení:
- **podle data akce** sestupně (výchozí),
- **podle hotovosti** vzestupně (nejméně hotové nahoře; hotovost =
  součet vyplněných polí všech souborů ze všech možných); akce
  *nezpracováno* na konci, shoda podle data sestupně,
- **podle poslední úpravy** sestupně (nejnovější čas v `upravili`);
  akce bez záznamu na konci podle data sestupně,
- **podle velikosti** sestupně (viz Velikost akce); akce bez údaje
  na konci, shoda podle data sestupně.

#### Scenario: Poslední úprava
- **WHEN** akce A byla naposledy uložena 2026-10-12 a akce B
  2026-10-14, akce C nemá `upravili`
- **THEN** řazení podle poslední úpravy dá pořadí B, A, C

#### Scenario: Výchozí řazení
- **WHEN** uživatel otevře seznam poprvé
- **THEN** akce jsou seřazené podle data sestupně

#### Scenario: Podle velikosti
- **WHEN** akce A má 2 GB, akce B 7 GB a akce C ještě nemá údaj
- **THEN** řazení podle velikosti dá pořadí B, A, C a adresa seznamu
  obsahuje `razeni=velikost`
