# Proposal

## Why

Osoby na fotkách aplikace jen přebírá z Immiche (`obliceje`), pojmenovat
je ale jde jen v Immichi, kde nepojmenované shluky obličejů z jedné akce
nejsou nijak pohromadě. Archivář proto nemá jak akci projít osoba po osobě
a nevidí, kolik osob v akci ještě chybí (issue #35).

## What Changes

- Nový nástroj **pojmenování osob**: překryv nad plochou akce
  s rozmazaným pozadím, který po jedné provede nepojmenovanými
  neskrytými osobami Immiche s obličejem na fotkách akce. U každé ukáže
  až 3 výřezy obličeje z různých fotek a metadata zdrojové fotky
  z Immiche i z archivu a nabídne:
  - **Pojmenovat:** jméno v kanonickém tvaru `Příjmení, Jméno`
    s návrhy ze seznamu jmen; při shodě s jinou osobou Immiche navrhne
    sloučení.
  - **Nevím:** odloží osobu do dalšího kola (stav ve `.work/`).
  - **Skrýt:** osobu skryje v Immichi, takže se v nástroji ani
    v kompletnosti už neobjeví.
- Nástroj pojmenovává celý shluk v Immichi, tedy i fotky mimo akci;
  do archivu zapisuje dál jen synchronizace.
- Nástroj smí používat archivář a admin. Klíč Immiche zůstává na
  serveru a prohlížeč volá jen endpointy aplikace.
- Odkazy na nástroj: karta akce v seznamu, plocha akce a chybějící
  údaj „nepojmenované osoby“ v navigátoru.
- Synchronizace nově vede v Immichi **album pro každou dokončenou akci**
  (vymezuje fotky akce pro nástroj) a do `.work/` ukládá počty
  pojmenovaných a nepojmenovaných osob akce.
- Osoby se stávají součástí kompletnosti akce: hotovost na kartě
  (`osoby N/M`), štítek „nekompletní“ a chybějící údaje navigátoru.
- **BREAKING (provoz):** dosud stačil klíč Immiche jen pro čtení. Nově
  potřebuje i oprávnění k zápisu (`person.update`, `person.merge`,
  `album.create`, `albumAsset.create`, …). Test připojení chybějící
  oprávnění vypíše. Synchronizace bez nich zakládá alba až po doplnění
  práv a nástroj je do té doby nedostupný.
- **BREAKING (provoz):** aplikace začne v Immichi zakládat alba
  (pojmenovaná podle akcí) a měnit osoby (jména, skrytí, sloučení),
  a to i ve vývojovém režimu.

## Capabilities

### New Capabilities
- `person-naming`: nástroj pro pojmenování nepojmenovaných osob akce
  v Immichi (výběr osob, náhledy, metadata, pojmenování, sloučení,
  odložení, skrytí, oprávnění).

### Modified Capabilities
- `immich-people`: test připojení ověřuje i oprávnění k zápisu;
  synchronizace vede album akce a počty osob akce.
- `metadata-workspace`: nepojmenované osoby jsou mezi chybějícími údaji
  řádku Akce v navigátoru (dosud výslovně vyloučeny).
- `archive-browsing`: hotovost akce uvádí osoby, štítek „nekompletní“
  počítá i nepojmenované osoby, karta nabízí nástroj.

## Impact

- `fotoarchiv/immich.py`: zapisující volání klienta (osoby, sloučení,
  alba, náhledy, oprávnění klíče); alba a počty osob v synchronizaci.
- Nový modul `fotoarchiv/naming.py`: výběr osob akce, kolo a odložené
  osoby ve `.work/`.
- `fotoarchiv/app.py`: endpointy `/api/akce/<nazev>/osoby…` (archivář
  a výš, mimo `ADMIN_PREFIXES`).
- `fotoarchiv/archive.py`, `fotoarchiv/model.py`: osoby v hotovosti
  a ve štítku „nekompletní“.
- Klient: nový modul `fotoarchiv/static/naming.js` (překryv), odkazy
  v `app.js`, styl překryvu v `style.css`.
- Nové soubory ve `.work/`: `immich-alba.json` (akce → id alba),
  `immich-osoby.json` (počty osob akce), `pojmenovani.json`
  (odložené osoby podle uživatele a akce).
- README (Datový model, Aplikace → Immich), AGENTS.md (nový invariant:
  do Immiche zapisuje jen nástroj pojmenování a alba v synchronizaci;
  `.work/` soubory nástroje), testy `tests/test_immich.py`, nové
  `tests/test_naming.py`, `tests/js/naming.test.mjs`.
