# event-visibility Specification

## Purpose

Skrýt nedokončené akce před Immichem, který čte archiv jako externí
knihovnu: složka akce nese do dokončení příponu `.ignored`, takže ji
Immich načte až se sidecary a pod konečnou cestou. Název akce
v aplikaci na příponě nezávisí.

## Requirements

### Requirement: Přípona nedokončené akce
V produkčním režimu SHALL složka každé nedokončené akce na disku nést
příponu `.ignored` (`2026-04-28 kontrola Stezky.ignored`), aby ji Immich
vyloučil vzorem `**/*.ignored/**`. Název akce v aplikaci (seznam, URL,
zámek, pracovní adresář) MUST být bez přípony; přípona je jen vlastnost
složky na disku. Název akce MUST NOT končit na `.ignored`.

#### Scenario: Složka s příponou
- **WHEN** archiv obsahuje složku `2026-04-28 kontrola Stezky.ignored`
- **THEN** aplikace ji ukazuje a otevírá jako akci
  `2026-04-28 kontrola Stezky`

#### Scenario: Název akce s příponou
- **WHEN** požadavek míří na akci `2026-04-28 kontrola Stezky.ignored`
- **THEN** aplikace takovou akci nezná

#### Scenario: Pracovní adresář beze změny
- **WHEN** akce `2026-04-28 kontrola Stezky` při dokončení ztratí
  příponu
- **THEN** její cache, záznam o exportu a ve vývojovém režimu
  `_metadata.json` v pracovním adresáři zůstanou pod týmž názvem

### Requirement: Kolize přípony
Existují-li složka akce s příponou i bez ní, aplikace MUST NOT akci
otevřít, dokončit ani do ní importovat a MUST NOT žádnou ze složek
přesouvat. Seznam akcí SHALL akci ukázat jednou s upozorněním na
kolizi.

#### Scenario: Obě složky
- **WHEN** archiv obsahuje `2026-04-28 kontrola Stezky`
  i `2026-04-28 kontrola Stezky.ignored`
- **THEN** seznam ukáže akci jednou s upozorněním na kolizi, otevření
  akce odmítne a obě složky zůstanou beze změny

### Requirement: Zveřejnění dokončením
Dokončení akce SHALL po úspěšném zápisu sidecarů odebrat příponu
`.ignored` ze složky akce. Selže-li přejmenování, akce MUST NOT být
označena jako dokončená a plocha SHALL chybu ukázat. Složka dokončené
akce MUST NOT příponu znovu dostat, ani po dalších úpravách a exportech.
Ve vývojovém režimu se archiv nepřejmenovává.

#### Scenario: Dokončení skryté akce
- **WHEN** uživatel v produkčním režimu dokončí akci se složkou
  `2026-04-28 kontrola Stezky.ignored`
- **THEN** složka se jmenuje `2026-04-28 kontrola Stezky`, obsahuje
  sidecary a akce je *hotovo*

#### Scenario: Přejmenování selže
- **WHEN** při dokončení nejde složku přejmenovat (soubor drží jiný
  počítač)
- **THEN** akce zůstane nedokončená, složka má dál příponu a plocha
  ukáže chybu

#### Scenario: Úprava dokončené akce
- **WHEN** uživatel u dokončené akce změní popis a znovu ji dokončí
- **THEN** složka zůstane bez přípony

### Requirement: Označení stávajících akcí
Příkaz `python -m fotoarchiv skryt` SHALL najít všechny nedokončené
akce (*nezpracováno* i *rozpracováno*) se složkou bez přípony a vypsat
je. S přepínačem `--zapis-do-archivu` je SHALL přejmenovat na složky
s příponou; bez něj MUST archiv nechat beze změny. Akce v kolizi MUST
přeskočit a vypsat. Příkaz se spouští, když server neběží.

#### Scenario: Výpis bez zápisu
- **WHEN** archiv má nedokončenou akci `2026-04-28 kontrola Stezky`
  a příkaz běží bez `--zapis-do-archivu`
- **THEN** příkaz akci vypíše a složka zůstane beze změny

#### Scenario: Označení
- **WHEN** archiv má nezpracovanou akci `2026-04-28 kontrola Stezky`,
  dokončenou akci `2026-03-14 výzkum Hradisko` a příkaz běží
  s `--zapis-do-archivu`
- **THEN** vznikne `2026-04-28 kontrola Stezky.ignored`
  a `2026-03-14 výzkum Hradisko` zůstane beze změny
