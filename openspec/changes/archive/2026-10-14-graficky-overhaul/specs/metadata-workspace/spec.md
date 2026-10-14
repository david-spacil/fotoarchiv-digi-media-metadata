## MODIFIED Requirements

### Requirement: Formulář podle výběru
Formulář vedle mřížky SHALL upravovat akci, když není nic vybráno,
skupinu, když je vybrána hlavička skupiny, a vybrané soubory, když je
vybrán jeden nebo více souborů. Zděděné hodnoty SHALL být viditelně
odlišené od zadaných a MUST jít přepsat i vrátit na zděděné. Vyprázdnění
pole SHALL znamenat vrácení na zděděné (pole se smaže); přepsání na
prázdnou hodnotu aplikace nepodporuje.

Každé pole SHALL ukazovat zdroj své hodnoty štítkem a barevným
proužkem: zděděná („z akce“, „ze skupiny“, „z místa“), rozdílná ve
výběru („rozdílné“) a zadaná na dané úrovni. Pole se zadanou hodnotou
u skupiny nebo souborů SHALL mít tlačítko „vrátit na zděděné“, které
hodnotu z dané úrovně smaže (stejně jako vyprázdnění pole). U akce
tlačítko není (akce nic nedědí). Bez zámku akce (jen ke čtení) MUST
NOT jít tlačítko použít.

#### Scenario: Hromadné přepsání
- **WHEN** uživatel vybere 12 souborů a zadá popis
- **THEN** všech 12 souborů má tento popis zadaný na úrovni souboru

#### Scenario: Rozdílné hodnoty ve výběru
- **WHEN** vybrané soubory mají v poli různé hodnoty
- **THEN** formulář to u pole vyznačí a pole nezmění, dokud do něj
  uživatel nezapíše

#### Scenario: Vyprázdnění pole
- **WHEN** uživatel u souboru smaže celý zadaný popis
- **THEN** pole zmizí ze záznamu souboru a zobrazí se zděděný popis

#### Scenario: Štítek zdroje
- **WHEN** uživatel vybere soubor, jehož skupina má autora a soubor
  autory nepřepisuje
- **THEN** pole autoři ukazuje autora skupiny se štítkem „ze skupiny“

#### Scenario: Vrácení na zděděné
- **WHEN** soubor má zadaný vlastní popis a uživatel u pole klikne na
  „vrátit na zděděné“
- **THEN** popis zmizí ze záznamu souboru, pole ukáže zděděný popis se
  štítkem zdroje a změna se uloží jako ostatní

#### Scenario: Vrácení u výběru
- **WHEN** 5 vybraných souborů má zadané místo a uživatel klikne na
  „vrátit na zděděné“
- **THEN** žádný z 5 souborů nemá místo zadané u sebe

### Requirement: Lišta chybějících údajů
Pracovní plocha SHALL průběžně ukazovat, co chybí: akce bez názvu nebo
data, skupiny bez autorů, soubory bez data, soubory bez skupiny
a soubory bez místa, pokud má akce víc míst. Kliknutí na položku SHALL vybrat dotčené soubory nebo skupiny.
Soubory označené k vyřazení MUST NOT být v lištu započítány; skupina,
jejíž všechny soubory jsou označené, se nepočítá mezi skupiny bez
autorů.

Chybějící údaje, počet souborů k vyřazení a nálezy kontroly SHALL být
ve stejné liště jako název akce, přepínače zobrazení a tlačítka
Importovat a Dokončit akci (jedna lišta akce pod hlavičkou aplikace).
Nevejdou-li se na řádek, SHALL se zalomit na další řádek lišty;
ovládací prvky lišty MUST zůstat vidět.

#### Scenario: Skupina bez autorů
- **WHEN** skupina nemá autory a žádný její soubor je nepřepisuje
- **THEN** lišta ukáže „1 skupina bez autorů“

#### Scenario: Soubory bez místa
- **WHEN** akce má dvě místa a 30 souborů nemá místo zadané u sebe ani
  u skupiny
- **THEN** lišta ukáže „30 souborů bez místa“

#### Scenario: Označený soubor bez data
- **WHEN** soubor bez data je označený k vyřazení
- **THEN** lišta ho mezi soubory bez data nepočítá

#### Scenario: Jedna lišta
- **WHEN** uživatel otevře plochu akce, které chybí autoři dvou skupin
- **THEN** „2 skupiny bez autorů“ je v téže liště jako název akce
  a tlačítko Dokončit akci

#### Scenario: Mnoho položek na úzkém okně
- **WHEN** v okně 1280 px šířky chybí pět druhů údajů
- **THEN** položky se zalomí na další řádek lišty a tlačítko Dokončit
  akci zůstane vidět

## ADDED Requirements

### Requirement: Velikost dlaždic
Pracovní plocha SHALL mít ovladač velikosti náhledů v mřížce
s rozsahem od malých (aspoň 8 dlaždic na řádek v okně 1280 px s panelem)
po velké (náhled aspoň 280 px na šířku). Změna SHALL se projevit hned,
výběr a aktuální soubor MUST zůstat zachované a aktuální soubor vidět.
Volba SHALL platit v tomtéž prohlížeči pro další akce a po obnovení.
Filmový pás lupy velikost nemění.

#### Scenario: Zvětšení náhledů
- **WHEN** uživatel posune ovladač k velkým náhledům
- **THEN** dlaždice v mřížce se zvětší a vybrané soubory zůstanou
  vybrané

#### Scenario: Volba přetrvá
- **WHEN** uživatel nastaví malé náhledy a otevře jinou akci
- **THEN** mřížka nové akce má malé náhledy

### Requirement: Skládací panel formuláře
Panel formuláře na pracovní ploše SHALL jít sbalit a znovu rozbalit
tlačítkem a klávesou `P` (mimo textové pole). Sbalený panel SHALL
uvolnit šířku mřížce nebo lupě a ukazovat jen tlačítko pro rozbalení.
Stav panelu SHALL platit v tomtéž prohlížeči pro další akce a po
obnovení. Sbalení MUST NOT měnit výběr ani zahodit neuložené změny.
V průvodci se panel nesbaluje.

#### Scenario: Sbalení v lupě
- **WHEN** uživatel v lupě stiskne `P`
- **THEN** panel zmizí a velká fotka se roztáhne na uvolněnou šířku

#### Scenario: P v textovém poli
- **WHEN** je kurzor v poli popis a uživatel napíše `P`
- **THEN** píše se text a panel zůstane

#### Scenario: Rozbalení
- **WHEN** je panel sbalený a uživatel klikne na tlačítko rozbalení
- **THEN** panel ukáže formulář pro aktuální výběr
