## ADDED Requirements

### Requirement: Vyloučení z importu
V kroku skupiny a autoři importu SHALL klávesa Del i tlačítko v panelu
přepínat vyloučení vybraných médií: jsou-li všechna vybraná vyloučená,
vrátí je do importu, jinak je všechna vyloučí. Tlačítko SHALL mít podle
výběru popisek „Vrátit do importu“, nebo „Vyloučit z importu“.
Vyloučené médium SHALL zůstat v mřížce ve své skupině, vizuálně
odlišené, a jde ho kdykoli vrátit.

#### Scenario: Vyloučení dvou fotek
- **WHEN** krok ukazuje 47 přenášených médií a uživatel vybere dvě
  fotky a stiskne Del
- **THEN** obě dlaždice zůstanou ve skupině zašedlé s ikonou vyloučení
  a tlačítko ukáže „Importovat (45)“

#### Scenario: Zrušení vyloučení
- **WHEN** uživatel vybere obě vyloučené fotky a znovu stiskne Del
- **THEN** fotky už vyloučené nejsou a tlačítko ukáže „Importovat (47)“

#### Scenario: Popisek tlačítka
- **WHEN** jsou vybrané jen vyloučené fotky
- **THEN** tlačítko v panelu má popisek „Vrátit do importu“; po přidání
  nevyloučené fotky do výběru „Vyloučit z importu“

#### Scenario: Smíšený výběr
- **WHEN** z vybraných tří fotek je vyloučená jen jedna a uživatel
  klikne na „Vyloučit z importu“
- **THEN** vyloučené jsou všechny tři

### Requirement: Počty a uložení vyloučených
Vyloučená média MUST NOT se počítat do počtu v tlačítku Importovat ani
do upozornění na skupiny bez autorů. Seznam vyloučených SHALL průvodce
ukládat k importu (ne do archivu) i ve vývojovém režimu a po návratu
k rozpracovanému importu i po změně výchozího rozdělení je zachovat.

#### Scenario: Skupina jen z vyloučených
- **WHEN** všechna média skupiny bez autorů jsou vyloučená a uživatel
  klikne na Importovat
- **THEN** průvodce na skupinu bez autorů neupozorní

#### Scenario: Vše vyloučeno
- **WHEN** uživatel stiskne Ctrl+A a pak Del
- **THEN** tlačítko Importovat je vypnuté

#### Scenario: Návrat k rozpracovanému importu
- **WHEN** uživatel vyloučí fotku `P1503712.JPG`, zavře stránku
  a import později otevře přes Pokračovat
- **THEN** krok ukáže `P1503712.JPG` jako vyloučenou

#### Scenario: Změna výchozího rozdělení
- **WHEN** uživatel vyloučí fotku a pak změní výchozí rozdělení do
  skupin
- **THEN** fotka zůstane vyloučená v nové skupině

### Requirement: Vyloučení RAWu k fotce
Má-li vylučovaná fotka ve výběru RAW stejného jména bez přípony ve
stejné složce výběru, který by se přenesl, SHALL průvodce před
vyloučením zobrazit dialog s počtem takových RAWů a volbou, zda je
vyloučit také. Zrušení vyloučení fotky SHALL zrušit i vyloučení jejího
RAWu bez dotazu. Panel kroku SHALL uvést počet vyloučených RAWů.

#### Scenario: Vyloučit i RAW
- **WHEN** uživatel vylučuje `P1503712.JPG` a výběr obsahuje
  `P1503712.RW2` a v dialogu zvolí vyloučit i RAWy
- **THEN** obě se nepřenesou a panel uvede jeden vyloučený RAW

#### Scenario: Jen fotku
- **WHEN** uživatel v tomto dialogu zvolí vyloučit jen fotky
- **THEN** `P1503712.RW2` se přenese do `RAW.ignored/`

#### Scenario: Fotka bez RAWu
- **WHEN** vylučovaná fotka nemá ve výběru RAW stejného jména
- **THEN** průvodce se na nic neptá

#### Scenario: Vrácení fotky
- **WHEN** uživatel zruší vyloučení `P1503712.JPG`, které vyloučil
  spolu s RAWem
- **THEN** přenese se fotka i `P1503712.RW2`

### Requirement: Vyloučené soubory při provedení
Server MUST vyloučený soubor nepřenést a MUST ho nechat v pracovním
adresáři importu, nebo ve zdroji v `přetřídit`, dokud uživatel import
nezahodí. Vyloučený soubor MUST NOT dostat záznam v `_metadata.json`
ani návrhu skupin. Plán i výsledek SHALL uvést vyloučené soubory
zvlášť jako „vyloučeno“. Vyloučení MUST NOT měnit, které soubory plán
označí jako duplicitu nebo blokované.

#### Scenario: Import s vyloučenou fotkou
- **WHEN** uživatel v produkčním režimu importuje 40 nahraných JPG,
  z nich dvě vyloučené
- **THEN** v akci je 38 fotek, výsledek uvede 2 vyloučené a ty zůstanou
  v pracovním adresáři importu, který zůstane mezi rozpracovanými

#### Scenario: Vyloučený soubor ze zdroje
- **WHEN** uživatel importuje složku `přetřídit/DOD 2016` a jednu fotku
  vyloučí
- **THEN** fotka zůstane ve složce `DOD 2016`, výsledek ji uvede mezi
  tím, co ve zdroji zůstalo, a stránka Přetřídit složku dál nabízí

#### Scenario: Plán po návratu
- **WHEN** uživatel po vyloučení fotky přejde zpět na plán a nechá ho
  sestavit znovu
- **THEN** plán uvede fotku jako vyloučenou a v kroku skupiny a autoři
  zůstane vyloučená ve své skupině

#### Scenario: Vývojový režim
- **WHEN** uživatel ve vývojovém režimu vyloučí fotku a otevře „Co by
  se zapsalo“
- **THEN** vyloučená fotka v zápisu není a archiv zůstane beze změny
