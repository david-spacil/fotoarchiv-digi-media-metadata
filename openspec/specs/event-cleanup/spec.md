# event-cleanup Specification

## Purpose

Rozpoznat podsložky a RAW soubory v kořeni akce a připravit plán úklidu,
aby kořen obsahoval jen fotky a videa určené pro Immich.

## Requirements

### Requirement: Nalezení podsložek
Aplikace SHALL v kořeni akce najít všechny podsložky bez přípony
`.ignored` a u každé uvést počet souborů (bez `Thumbs.db`) a počet
RAWů. Podsložky s příponou `.ignored` MUST být přeskočeny.

#### Scenario: Akce s podsložkami
- **WHEN** akce obsahuje podsložky `RAW` a `Video`
- **THEN** průvodce u obou nabídne volbu *přesunout do kořene* nebo
  *ponechat stranou*

#### Scenario: Ignorovaná podsložka
- **WHEN** akce obsahuje podsložku `RAW.ignored`
- **THEN** průvodce se na ni neptá a její soubory nezpracovává

### Requirement: Cílový název ponechané podsložky
Ponechaná podsložka SHALL dostat název `původní.ignored`. Pokud RAWy
tvoří víc než polovinu jejích souborů, cílový název MUST být
`RAW.ignored` bez ohledu na původní název. RAWem se rozumí soubor
s příponou `rw2`, `cr2`, `cr3`, `nef`, `arw`, `dng`, `orf` nebo `raf`
bez ohledu na velikost písmen.

#### Scenario: Podsložka s většinou RAWů
- **WHEN** uživatel ponechá podsložku `RAWy` se 176 soubory RW2
- **THEN** plán ji přejmenuje na `RAW.ignored`

#### Scenario: Ostatní podsložka
- **WHEN** uživatel ponechá podsložku `Prezentační` bez RAWů
- **THEN** plán ji přejmenuje na `Prezentační.ignored`

### Requirement: RAWy v kořeni
RAWy v kořeni akce SHALL průvodce nabídnout k přesunu do `RAW.ignored`.

#### Scenario: RAW v kořeni
- **WHEN** kořen akce obsahuje `P1503712.RW2`
- **THEN** plán navrhne přesun do `RAW.ignored/P1503712.RW2`

### Requirement: Kolize názvů
Plán MUST odhalit každý přesun, jehož cíl už existuje, a takový přesun
označit jako blokovaný; nic se nesmí přepsat. Pokud `RAW.ignored` už
existuje, soubory se do ní přidávají.

#### Scenario: Soubor stejného jména v kořeni
- **WHEN** podsložka `Video` obsahuje `a.mp4` a kořen také `a.mp4`
- **THEN** plán označí přesun `Video/a.mp4` jako blokovaný kolizí

### Requirement: Úklid nasucho
V prototypu SHALL průvodce plán úklidu jen zobrazit (co se přesune,
přejmenuje, smaže a co je blokované) a MUST NOT ho provést. Další krok
průvodce SHALL pracovat se soubory, které jsou v kořeni skutečně.

#### Scenario: Potvrzení plánu
- **WHEN** uživatel v průvodci potvrdí plán úklidu
- **THEN** archiv zůstane beze změny a průvodce pokračuje načtením
  souborů z kořene
