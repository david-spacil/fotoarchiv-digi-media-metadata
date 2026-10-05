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

### Requirement: Provedení úklidu
V produkčním režimu SHALL průvodce po potvrzení plán úklidu provést.
Server MUST plán sestavit znovu z voleb uživatele těsně před provedením
a provést jen neblokované operace; blokované přeskočí. Přesun ani
přejmenování MUST NOT přepsat existující soubor nebo složku. Smazat se
smí jen podsložka, ve které po přesunech zbyl nejvýš `Thumbs.db`.
Ve vývojovém režimu SHALL průvodce plán jen zobrazit.

#### Scenario: Přesun podsložky do kořene
- **WHEN** uživatel zvolí přesunout podsložku `Video` s 22 soubory bez
  kolizí a plán potvrdí
- **THEN** 22 souborů je v kořeni akce a složka `Video` je smazaná

#### Scenario: Ponechání podsložky
- **WHEN** uživatel ponechá podsložku `RAWy` a plán potvrdí
- **THEN** složka se jmenuje `RAW.ignored`

#### Scenario: Kolize při provedení
- **WHEN** mezi zobrazením a potvrzením plánu vznikne v kořeni soubor
  stejného jména jako přesouvaný
- **THEN** přesun se neprovede, soubor zůstane v podsložce a podsložka
  se nesmaže

### Requirement: Výsledek úklidu
Po provedení SHALL průvodce ukázat, které operace proběhly, které byly
blokované a které selhaly (s chybou). Selhání jedné operace MUST NOT
zastavit ostatní nezávislé operace. Další krok průvodce SHALL pracovat
se soubory, které jsou v kořeni po úklidu.

#### Scenario: Chyba oprávnění
- **WHEN** přesun jednoho souboru selže na oprávnění
- **THEN** výsledek ho ukáže jako selhaný s chybou, ostatní přesuny
  proběhnou a podsložka se nesmaže
