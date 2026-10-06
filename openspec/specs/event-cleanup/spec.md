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

### Requirement: Ukázky obsahu podsložky
Průvodce SHALL u každé nalezené podsložky ukázat až 8 souborů vybraných
rovnoměrně podle abecedy z jejích fotek a videí, každý s náhledem
a názvem souboru. Neobsahuje-li podsložka fotky ani videa, SHALL se
stejně vybrat z ostatních souborů (bez `Thumbs.db`) a ukázat jen jejich
názvy. Klik na náhled SHALL ukázat zvětšený náhled. Zobrazení ukázek
MUST NOT v archivu nic změnit.

#### Scenario: Podsložka s fotkami
- **WHEN** podsložka `PPA 2026` obsahuje 13 fotek
- **THEN** průvodce u ní ukáže 8 náhledů s názvy souborů od první
  fotky po některou z posledních dvou, ne prvních 8 fotek

#### Scenario: Podsložka bez fotek
- **WHEN** podsložka `Prezentační` obsahuje jen soubory PPTX a PDF
- **THEN** průvodce u ní ukáže jejich názvy bez náhledů

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

### Requirement: Vyřazení označených souborů
Plán úklidu SHALL u každého souboru v kořeni akce, který má
v `_metadata.json` `"vyradit": true`, navrhnout přesun do
`k_odstraneni.ignored/` v kořeni akce; složka vznikne, pokud neexistuje,
jinak se do ní soubory přidají. Platí pravidla kolizí: přesun, jehož cíl
nebo cílový `.xmp` existuje, MUST být blokovaný. Označený soubor, který
v kořeni není, se do plánu nezahrne. Podsložka `k_odstraneni.ignored`
se jako ostatní `.ignored` při úklidu přeskakuje.

#### Scenario: Označený soubor
- **WHEN** `P1503712.JPG` v kořeni má `"vyradit": true`
- **THEN** plán navrhne přesun do `k_odstraneni.ignored/P1503712.JPG`

#### Scenario: Kolize ve vyřazených
- **WHEN** `k_odstraneni.ignored/a.jpg` už existuje a označený je i `a.jpg`
  v kořeni
- **THEN** plán označí přesun `a.jpg` jako blokovaný kolizí

### Requirement: Sidecar vyřazeného souboru
Před odstraněním záznamu vyřazovaného souboru SHALL server zapsat jeho
XMP sidecar s rozepsanými hodnotami do `k_odstraneni.ignored/<soubor>.xmp`
a sidecar v kořeni, pokud existuje, odstranit. Sidecar MUST NOT obsahovat
tag o vyřazení. Selže-li zápis sidecaru, soubor se MUST NOT přesunout.

#### Scenario: Sidecar s údaji
- **WHEN** vyřazený `P1503712.JPG` má v záznamu popis
- **THEN** `k_odstraneni.ignored/P1503712.JPG.xmp` popis obsahuje
  a `P1503712.JPG.xmp` v kořeni není

#### Scenario: Jen zděděné údaje
- **WHEN** vyřazený soubor má v záznamu jen `"vyradit": true` a akce
  má datum
- **THEN** `k_odstraneni.ignored/<soubor>.xmp` vznikne s datem akce

### Requirement: Záznam vyřazeného souboru
Po úspěšném přesunu do `k_odstraneni.ignored` SHALL server odstranit záznam
souboru ze `soubory` v `_metadata.json` (se stejnou kontrolou verze jako
běžné uložení). U blokovaného nebo selhaného přesunu záznam i označení
MUST zůstat. Ve vývojovém režimu se nic nepřesouvá ani neodstraňuje.

#### Scenario: Úspěšné vyřazení
- **WHEN** přesun `P1503712.JPG` do `k_odstraneni.ignored` proběhne
- **THEN** `_metadata.json` záznam `P1503712.JPG` nemá a soubor se na
  pracovní ploše neukazuje

#### Scenario: Blokované vyřazení
- **WHEN** přesun `a.jpg` je blokovaný kolizí
- **THEN** `a.jpg` zůstává v kořeni se záznamem i označením

### Requirement: Úklid z pracovní plochy
Je-li v akci aspoň jeden soubor označený k vyřazení, SHALL pracovní
plocha nabídnout úklid. Ten ukáže plán vyřazení, v produkčním režimu ho
po potvrzení provede a ukáže výsledek podle požadavku Výsledek úklidu;
ve vývojovém režimu plán jen zobrazí. Provedení MUST vyžadovat zámek
akce. Neuložené změny `_metadata.json` SHALL být uloženy před sestavením
plánu.

#### Scenario: Úklid z plochy
- **WHEN** uživatel na ploše se 3 označenými soubory spustí úklid
  a potvrdí plán
- **THEN** 3 soubory jsou ve `k_odstraneni.ignored` a výsledek ukáže
  3 provedené přesuny
