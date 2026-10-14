## MODIFIED Requirements

### Requirement: Okamžiky generování
Aplikace SHALL index přegenerovat po provedení importu, po exportu XMP
z aplikace (dokončení akce) a jednou na konci
příkazu `exportovat`. Uložení `_metadata.json` a kontrola exportu
nanečisto MUST NOT index generovat. Soubor indexu SHALL být zapsán
atomicky a jen tehdy, když chybí nebo se jeho obsah liší; obsah MUST
NOT obsahovat čas generování. Selhání zápisu indexu MUST NOT způsobit
selhání exportu ani importu; aplikace ho SHALL ohlásit jako varování.

#### Scenario: Import do nové akce
- **WHEN** import vytvoří akci `2026-10-06 nová akce` a zkopíruje do ní
  fotky
- **THEN** oba indexy obsahují akci `nová akce` jako *rozpracováno*
  s údaji akce a autory z importu a s počtem fotek z importu

#### Scenario: Bez změny se nezapisuje
- **WHEN** se export spustí znovu bez změny metadat a souborů
- **THEN** soubory indexu zůstanou nezměněné včetně času změny

#### Scenario: Uložení akce
- **WHEN** uživatel uloží rozpracovanou akci bez exportu
- **THEN** index se nezmění

#### Scenario: Index nejde zapsat
- **WHEN** zápis `_INDEX.html` selže a sidecary se zapsaly
- **THEN** export skončí úspěšně s varováním o indexu
