## MODIFIED Requirements

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

Nepodaří-li se popis zapsat, přenesené soubory MUST zůstat v archivu
a výsledek SHALL uvést, že soubory jsou bez skupiny a autorů.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` s autorem `Modelová, Zuzana` do akce ve
  stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a autorkou `Modelová, Zuzana` a navigátor je neuvádí jako soubory
  bez skupiny ani skupinu bez autorů

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu importuje složku `DOD 2015`
  s podsložkami do nové akce a zadá údaje akce a autory skupin
- **THEN** akce má `_metadata.json` s těmito údaji, je v seznamu jako
  *rozpracováno* a její otevření vede rovnou na pracovní plochu

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe, každou se
  svými autory
