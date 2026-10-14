## MODIFIED Requirements

### Requirement: Dokončení akce
Pracovní plocha SHALL nabídnout tlačítko Dokončit akci; to uloží
neuložené změny a otevře kontrolní stránku dokončení (viz Kontrolní
stránka dokončení). Tlačítko Dokončit na kontrolní stránce je jediné
místo aplikace mimo příkaz `exportovat`, které zapisuje sidecary.
Dokončení SHALL zkontrolovat úplnost podle chybějících údajů (viz
Chybějící údaje v navigátoru) a nálezy kontroly akce (viz
`event-consistency`); chybí-li něco nebo je-li nález, MUST to kontrolní
stránka ukázat a dokončit jen po výslovném potvrzení.
Pak SHALL akci exportovat, v produkčním režimu odebrat ze
složky akce příponu `.ignored` (viz `event-visibility`) a nastavit
`dokonceno` na datum dokončení. Má-li akce `dokonceno` už nastavené,
dokončení ho MUST NOT změnit: `dokonceno` je datum prvního dokončení.
Selže-li u akce bez `dokonceno` zápis některého sidecaru nebo
přejmenování složky, akce MUST NOT být označena jako dokončená.
Selže-li u akce s `dokonceno`, akce MUST zůstat dokončená se stejným
datem a kontrolní stránka SHALL chybu ukázat.
Dokončení vyžaduje zámek akce.

U dokončené akce SHALL být tlačítko na ploše i na kontrolní stránce
neaktivní, dokud není co dokončovat: žádné neuložené ani
neexportované změny, žádné neaktuální sidecary a poslední export
neselhal. Jakmile něco z toho nastane, tlačítko SHALL být znovu
aktivní. Text tlačítka na ploše se nemění.

#### Scenario: Úplná akce
- **WHEN** akci nic nechybí a uživatel na kontrolní stránce klikne na
  Dokončit
- **THEN** sidecary jsou zapsané, `dokonceno` je nastavené a seznam
  akcí ji ukazuje jako *hotovo*

#### Scenario: Neúplná akce
- **WHEN** 14 souborů nemá datum a uživatel klikne na ploše na
  Dokončit akci
- **THEN** kontrolní stránka ukáže „14 souborů bez data“ a dokončí až
  po výslovném potvrzení

#### Scenario: Akce s nepodporovaným souborem
- **WHEN** kořen akce obsahuje `zprava.pdf` a uživatel otevře
  kontrolní stránku
- **THEN** stránka ukáže „1 nepodporovaný soubor v kořeni“ a po
  potvrzení akci dokončí; `zprava.pdf` zůstane v kořeni

#### Scenario: Selhání přejmenování
- **WHEN** sidecary se zapíšou, ale složku akce nejde přejmenovat
- **THEN** akce nemá `dokonceno` a kontrolní stránka ukáže, že akci
  nešlo zveřejnit

#### Scenario: Dokončená akce beze změn
- **WHEN** uživatel otevře dokončenou akci se všemi sidecary aktuálními
- **THEN** tlačítko Dokončit akci je neaktivní a u něj je „Dokončeno …“

#### Scenario: Úprava dokončené akce
- **WHEN** uživatel u dokončené akce změní popis souboru
- **THEN** tlačítko Dokončit akci je aktivní až do dalšího dokončení

#### Scenario: Opakované dokončení zachová datum
- **WHEN** akce dokončená 2026-10-01 se 8. 10. 2026 upraví a znovu
  dokončí
- **THEN** sidecary jsou aktuální a `dokonceno` je dál `2026-10-01`

#### Scenario: Selhání exportu u dokončené akce
- **WHEN** u akce dokončené 2026-10-01 při opakovaném dokončení selže
  zápis sidecaru `foto.jpg.xmp`
- **THEN** `dokonceno` je dál `2026-10-01`, seznam akcí ji ukazuje
  jako *hotovo*, kontrolní stránka ukáže chybu u `foto.jpg`
  a tlačítko Dokončit zůstane aktivní

#### Scenario: Rozpracovaná akce
- **WHEN** akce ještě nemá `dokonceno`
- **THEN** tlačítko Dokončit akci je aktivní (má-li uživatel zámek)

## ADDED Requirements

### Requirement: Kontrolní stránka dokončení
Aplikace SHALL mít pro každou akci kontrolní stránku dokončení na
vlastní adrese (`#/akce/<název>/dokonceni`), dostupnou z plochy
tlačítkem Dokončit akci i přímým odkazem. Stránka SHALL ukázat seznam
kontrol, každou se stavem v pořádku / k vyřešení a počtem:

- **Údaje akce:** chybějící název nebo data akce.
- **Chybějící údaje souborů:** skupiny bez autorů, soubory bez
  autorů, bez data, bez místa (bez místa jen pokud má akce víc míst),
  místa bez souřadnic; počty stejné jako v navigátoru.
- **Nálezy kontroly akce** po druzích (viz `event-consistency`).
- **Poškozené soubory** bez rozhodnutí (viz `file-integrity`).
- **Soubory k vyřazení**, které ještě nejsou přesunuté.
- **Stav exportu:** výsledek kontroly nanečisto (počet neaktuálních
  sidecarů, „neexportované změny“, nebo vše aktuální) a ve vývojovém
  režimu poznámka, že sidecary jdou do pracovního adresáře.

Každá kontrola k vyřešení SHALL mít odkaz na nápravu, který otevře
plochu akce a vybere dotčené soubory nebo skupinu, případně skočí na
oddíl nebo otevře dialog Uklidit…. Návrat z plochy SHALL být možný
tlačítkem Dokončit akci. Tlačítko Dokončit SHALL při kontrolách
k vyřešení nést text „Přesto dokončit“; bez nich „Dokončit“. Po
dokončení SHALL stránka ukázat počty zapsaných, nezměněných
a selhaných sidecarů, chyby u jednotlivých souborů a odkaz zpět na
seznam akcí.

Stránka SHALL používat zámek akce stejně jako plocha: přechod mezi
plochou a stránkou zámek MUST NOT uvolnit; bez zámku je stránka jen
pro čtení s uvedeným držitelem a tlačítko Dokončit je neaktivní.
Akci bez `_metadata.json` stránka SHALL přesměrovat na plochu
(průvodce).

#### Scenario: Přechod z plochy
- **WHEN** uživatel na ploše s neuloženou změnou klikne na Dokončit
  akci
- **THEN** změna se uloží, otevře se kontrolní stránka a zámek akce
  zůstane uživateli

#### Scenario: Náprava chybějícího data
- **WHEN** kontrolní stránka ukazuje „14 souborů bez data“
  a uživatel klikne na odkaz nápravy
- **THEN** otevře se plocha akce se 14 vybranými soubory

#### Scenario: Vše v pořádku
- **WHEN** akci nic nechybí, nemá nálezy ani poškozené soubory
- **THEN** všechny kontroly jsou v pořádku a tlačítko nese text
  „Dokončit“

#### Scenario: Přímý odkaz bez zámku
- **WHEN** uživatel otevře `#/akce/<název>/dokonceni` akce, kterou
  drží Kopáčová, Zuzana
- **THEN** stránka ukáže kontroly, uvede „upravuje Kopáčová, Zuzana“
  a tlačítko Dokončit je neaktivní

#### Scenario: Nezpracovaná akce
- **WHEN** uživatel otevře kontrolní stránku akce bez `_metadata.json`
- **THEN** aplikace otevře plochu akce s průvodcem
