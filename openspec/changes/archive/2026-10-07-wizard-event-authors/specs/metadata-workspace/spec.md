# Spec Delta

## ADDED Requirements

### Requirement: Autoři akce v průvodci
Krok autoři skupin průvodce SHALL nad skupinami nabídnout pole autoři
celé akce, které upravuje `autori` akce a ukazuje jejich uloženou
hodnotu. Skupina bez vlastních autorů SHALL v tomto kroku ukázat autory
akce jako zděděné a MUST se nepočítat mezi skupiny bez autorů. Autoři
akce se MUST NOT kopírovat do skupin; skupina je SHALL moci přepsat
vlastními. Krok údaje akce pole autorů neukazuje.

#### Scenario: Autoři celé akce
- **WHEN** uživatel v kroku autoři skupin zadá autory celé akce
  `Spáčil, David` a `Kopáčová, Zuzana`
- **THEN** akce má `autori` = [`Spáčil, David`, `Kopáčová, Zuzana`]
  a skupina `g9` bez vlastních autorů je ukazuje jako zděděné z akce

#### Scenario: Dokončení bez upozornění
- **WHEN** akce má autory a žádná skupina vlastní autory nemá
- **THEN** dokončení průvodce neupozorní na skupiny bez autorů
  a skupiny se uloží bez pole `autori`

#### Scenario: Skupina s vlastními autory
- **WHEN** akce má autory `Spáčil, David` a skupina `g9` má vlastní
  autory `Kopáčová, Zuzana`
- **THEN** skupina `g9` si ponechá `Kopáčová, Zuzana` jako zadané
  u skupiny

#### Scenario: Předvyplnění
- **WHEN** akce už má autory (zadané dřív na ploše) a uživatel se
  v průvodci vrátí ke kroku autoři skupin
- **THEN** pole autoři celé akce je ukazuje
