## Purpose

Najít v kořeni akce soubory a záznamy, které tam nepatří nebo si
odporují, ukázat je v seznamu akcí a na pracovní ploše a nabídnout
jejich nápravu úklidem.

## ADDED Requirements

### Requirement: Nálezy kontroly akce
Kontrola akce SHALL projít kořen složky akce a `_metadata.json`
a vrátit nálezy těchto druhů:

- *nepodporovaný soubor* — soubor, který není fotka ani video aplikace
  (viz `media-scan`), RAW, `Thumbs.db`, `_metadata.json`, sidecar `.xmp`
  ani dočasný soubor aplikace;
- *osiřelý sidecar* — `<soubor>.xmp`, k němuž `<soubor>` v kořeni není;
- *RAW v kořeni*;
- *podsložka* bez přípony `.ignored`;
- *záznam bez souboru* — soubor uvedený v `_metadata.json`, který
  v kořeni není.

Názvy se MUST porovnávat bez ohledu na velikost písmen a normalizaci
Unicode. Kontrola MUST číst jen výpis kořene a `_metadata.json`, ne
obsah souborů, a nesmí nic měnit. Obsah podsložek se nekontroluje.

#### Scenario: Nepodporované soubory
- **WHEN** kořen akce obsahuje `P1503712.JPG`, `prezentace.zip`,
  `zprava.pdf` a `Thumbs.db`
- **THEN** kontrola vrátí jako nepodporované `prezentace.zip`
  a `zprava.pdf`

#### Scenario: Osiřelý sidecar
- **WHEN** kořen obsahuje `P1503712.JPG`, `P1503712.JPG.xmp`
  a `P1503713.JPG.xmp`, ale ne `P1503713.JPG`
- **THEN** kontrola vrátí jako osiřelý jen `P1503713.JPG.xmp`

#### Scenario: Sidecar s jinou velikostí písmen
- **WHEN** kořen obsahuje `a.jpg` a `a.JPG.xmp`
- **THEN** kontrola sidecar nehlásí

#### Scenario: Záznam bez souboru
- **WHEN** `_metadata.json` uvádí `P1503714.JPG` a v kořeni není
- **THEN** kontrola vrátí `P1503714.JPG` jako záznam bez souboru

#### Scenario: Podsložky
- **WHEN** kořen obsahuje složky `Video` a `RAW.ignored`
- **THEN** kontrola vrátí jen podsložku `Video`

#### Scenario: Akce bez metadat
- **WHEN** akce nemá `_metadata.json` a kořen obsahuje `P1503712.RW2`
- **THEN** kontrola vrátí RAW v kořeni a žádný záznam bez souboru

### Requirement: Nálezy v seznamu akcí
Seznam akcí SHALL u akce s aspoň jedním nálezem kontroly ukázat štítek
„k vyřešení“ s počty nálezů podle druhu v popisku. Platí pro akce
v každém stavu kromě kolize přípony `.ignored`.

#### Scenario: Akce se zipem
- **WHEN** kořen akce `2026-04-28 kontrola Stezky` obsahuje
  `prezentace.zip`
- **THEN** seznam u akce ukáže „k vyřešení“ a popisek uvede
  „1 nepodporovaný soubor“

#### Scenario: Čistá akce
- **WHEN** kontrola akce nevrátí žádný nález
- **THEN** seznam u akce štítek „k vyřešení“ neukazuje

### Requirement: Nálezy na pracovní ploše
Lišta pracovní plochy SHALL ukázat nálezy kontroly po druzích s počtem
(„2 nepodporované soubory v kořeni“, „1 osiřelý sidecar“). Kliknutí na
položku SHALL ukázat názvy dotčených souborů a složek. Je-li mezi nálezy
nepodporovaný soubor, osiřelý sidecar, RAW v kořeni nebo podsložka,
SHALL lišta nabídnout úklid (viz `event-cleanup`). Záznam bez souboru
se jen hlásí; aplikace ho MUST NOT smazat.

#### Scenario: Nepodporovaný soubor na ploše
- **WHEN** uživatel otevře akci, jejíž kořen obsahuje `zprava.pdf`
- **THEN** lišta ukáže „1 nepodporovaný soubor v kořeni“ a tlačítko
  Uklidit…

#### Scenario: Jen záznam bez souboru
- **WHEN** jediným nálezem akce je záznam bez souboru
- **THEN** lišta ho ukáže a tlačítko Uklidit… kvůli němu nenabízí
