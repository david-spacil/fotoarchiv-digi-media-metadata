# Proposal

## Why

Autoři jdou zadat u akce (formulář akce na ploše) a dědí se na skupiny
a soubory, ale průvodce prvním otevřením je u akce schválně vynechává
a chce je u každé skupiny zvlášť. Když celou akci fotila jedna parta,
musí uživatel stejná jména opakovat u každé skupiny, a pole „Autoři“
na ploše pak působí jako omyl, protože v průvodci nebylo.

## What Changes

- Krok průvodce „Autoři skupin“ dostane nad skupinami pole **Autoři
  celé akce** (`akce.autori`), předvyplněné, pokud už je akce má.
- Skupiny bez vlastních autorů ukazují autory akce jako zděděné („zděděno
  z akce“) a průběžně se překreslí při jejich změně; skupina je dál může
  přepsat vlastními.
- Skupina se zděděnými autory akce se nepočítá mezi skupiny bez autorů,
  takže dokončení průvodce neupozorňuje (pravidlo dědění už to tak
  počítá, mění se jen to, že jde autory akce zadat v průvodci).
- Krok „Údaje akce“ autory dál neukazuje (jedno místo pro autory
  v průvodci).
- README a fixtures dědění doplněné o autory zadané jen u akce.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `metadata-workspace`: nový požadavek na autory celé akce v kroku
  autoři skupin průvodce.

## Impact

- `fotoarchiv/static/app.js` (`renderAuthorsStep`), jen klient.
- `README.md` (Aplikace, Tok práce, bod 2).
- `tests/fixtures/inheritance/` — nový případ, testuje ho Python
  (`model.py`) i JS (`inherit.js`).
- Datový model, API, export ani dědění se nemění.
