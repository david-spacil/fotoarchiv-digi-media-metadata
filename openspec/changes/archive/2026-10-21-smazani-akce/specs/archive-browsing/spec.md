## MODIFIED Requirements

### Requirement: Seznam akcí
Aplikace SHALL zobrazit seznam složek první úrovně archivu, jejichž
název odpovídá vzoru `YYYY-MM-DD název`, jako karty (ne tabulku);
pořadí určuje Řazení seznamu. Karta SHALL uvádět datum, název akce
jako odkaz na pracovní plochu, počet souborů, stav a štítky (viz Stav
akce), hotovost, náhledy a držitele zámku.
Složka s příponou `.ignored` (skrytá nedokončená akce, viz
`event-visibility`) SHALL být v seznamu pod názvem bez přípony.
Ostatní složky a soubory první úrovně MUST být ignorovány a nesmí se
měnit. Výjimkou jsou soubory indexu `_INDEX.html` a `_INDEX.md`, které
v produkčním režimu zapisuje aplikace (viz `archive-index`), a složka
`přetřídit`, ze které v produkčním režimu přesouvá soubory import (viz
`unsorted-import`), a složka koše `_kos.ignored`, do které přesouvá
smazané akce (viz `event-trash`). Seznam SHALL obsahovat odkaz na
stránku Přetřídit a adminovi odkaz na stránku Koš.
Seznam SHALL nabídnout přepínač podoby karet: dlaždice (výchozí)
a řádky; volbu si pamatuje prohlížeč.

#### Scenario: Složky mimo vzor
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky…`, `přetřídit`
  a `_metadata.xlsx`
- **THEN** seznam obsahuje jen `2026-04-28 kontrola Naučné stezky…`

#### Scenario: Skrytá akce v seznamu
- **WHEN** archiv obsahuje `2026-04-28 kontrola Naučné stezky.ignored`
- **THEN** seznam obsahuje akci `2026-04-28 kontrola Naučné stezky`

#### Scenario: Index v kořeni archivu
- **WHEN** kořen archivu obsahuje `_INDEX.html` a `_INDEX.md`
- **THEN** seznam akcí je neuvádí a `_metadata.xlsx` zůstane beze změny

#### Scenario: Jiné složky mimo akce
- **WHEN** uživatel provede import ze složky `přetřídit`
- **THEN** `fotky mimo akce` a `přednášky SKLEP TIC` zůstanou beze
  změny

#### Scenario: Koš v kořeni archivu
- **WHEN** kořen archivu obsahuje `_kos.ignored` se smazanou akcí
  `2026-04-28 kontrola Naučné stezky`
- **THEN** seznam akcí ji neuvádí a admin vidí odkaz na Koš

#### Scenario: Karta akce
- **WHEN** seznam ukazuje akci `2026-04-28 kontrola Naučné stezky` s 50 soubory
- **THEN** karta uvádí `2026-04-28`, název `kontrola Naučné stezky` jako odkaz
  na plochu akce a 50 souborů

#### Scenario: Podoba karet
- **WHEN** uživatel otevře seznam poprvé, přepne na řádky a znovu
  načte stránku
- **THEN** seznam je napoprvé v dlaždicích a po načtení v řádcích
