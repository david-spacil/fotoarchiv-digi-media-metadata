## ADDED Requirements

### Requirement: Vyřazení označených souborů
Plán úklidu SHALL u každého souboru v kořeni akce, který má
v `_metadata.json` `"vyradit": true`, navrhnout přesun do
`vyrazene.ignored/` v kořeni akce; složka vznikne, pokud neexistuje,
jinak se do ní soubory přidají. Platí pravidla kolizí: přesun, jehož cíl
existuje, MUST být blokovaný. Označený soubor, který v kořeni není, se
do plánu nezahrne. Podsložka `vyrazene.ignored` se jako ostatní
`.ignored` při úklidu přeskakuje.

#### Scenario: Označený soubor
- **WHEN** `P1503712.JPG` v kořeni má `"vyradit": true`
- **THEN** plán navrhne přesun do `vyrazene.ignored/P1503712.JPG`

#### Scenario: Kolize ve vyřazených
- **WHEN** `vyrazene.ignored/a.jpg` už existuje a označený je i `a.jpg`
  v kořeni
- **THEN** plán označí přesun `a.jpg` jako blokovaný kolizí

### Requirement: Záznam vyřazeného souboru
Po úspěšném přesunu do `vyrazene.ignored` SHALL server odstranit záznam
souboru ze `soubory` v `_metadata.json` (se stejnou kontrolou verze jako
běžné uložení). U blokovaného nebo selhaného přesunu záznam i označení
MUST zůstat. Ve vývojovém režimu se nic nepřesouvá ani neodstraňuje.

#### Scenario: Úspěšné vyřazení
- **WHEN** přesun `P1503712.JPG` do `vyrazene.ignored` proběhne
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
- **THEN** 3 soubory jsou ve `vyrazene.ignored` a výsledek ukáže
  3 provedené přesuny
