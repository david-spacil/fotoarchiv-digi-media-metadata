## ADDED Requirements

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
