## Why

Seznam akcí neukazuje, kolik místa akce zabírá, a není vidět ani
velikost celého archivu a koše (issue #56). Správce archivu tak nepozná,
které akce jsou velké (RAWy, videa), ani kolik místa uvolní vysypání
koše. Měření na serveru (komentář v #56) ukázalo, že rekurzivní průchod
celého archivu včetně koše trvá kolem 1 s (8 113 souborů, 40 GiB),
takže denní přepočet celého archivu je levný.

## What Changes

- Server vede velikost každé akce a každé položky koše v cache
  `.work/velikosti.json`: součet `st_size` všech souborů celé složky
  akce rekurzivně (podsložky `*.ignored`, `_metadata.json`, sidecary,
  `Thumbs.db`), symlinky nesleduje, akci v kolizi přípony sečte z obou
  složek.
- Údaj je „k datu“: výpis akcí čte jen cache, archiv navíc nečte.
  Přepočet jedné akce po změně aplikací (import, úklid, dokončení,
  obnovení z koše), akce bez údaje se dopočítá na pozadí a denně se
  přepočítá celý archiv i koš (zachytí změny zvenku přes SMB).
- Smazání akce do koše přenese její údaj ke koši bez přepočtu,
  obnovení ho vrátí akci (a přepočítá), vysypání položku odebere.
- `GET /api/akce` vrací u akce nové pole `bajtu` (`null` bez údaje).
  Nový endpoint `GET /api/velikost` vrací součet akcí a součet koše
  pro každého přihlášeného (jen čísla, ne obsah koše).
- Karta akce uvádí velikost (`2024-05-01 · 132 souborů · 4,2 GB`),
  seznam nabízí řazení „podle velikosti“ (`#/?razeni=velikost`)
  a ukazuje celkový součet archivu s košem zvlášť
  (`25 GB (+5 GB v koši)`).
- Stránka Koš uvádí velikost u každé smazané akce.

## Capabilities

### New Capabilities

- (žádné)

### Modified Capabilities

- `archive-browsing`: velikost na kartě akce, řazení podle velikosti,
  celkový součet archivu a koše, pravidla výpočtu a cache velikostí.
- `event-trash`: přenos velikosti při smazání, obnovení a vysypání,
  velikost položek na stránce Koš.

## Impact

- Kód: nový modul `fotoarchiv/velikost.py` (výpočet, cache, vlákno
  přepočtu), `app.py` (pole `bajtu`, `/api/velikost`, volání po změnách,
  hooky smazání/obnovení/vysypání), `trash.py` (`entries` s velikostí),
  `static/fronta.js` (řazení, formát součtu, `fmtSize`), `static/app.js`
  (karta, součet), stránka Koš.
- Pracovní adresář: nový soubor `.work/velikosti.json`; archiv se nemění.
- Zátěž SMB: jeden denní průchod celým archivem (řádově sekundy)
  a průchod jednou akcí po změně.
- Dokumentace: `docs/navod/seznam-akci.md`, `docs/navod/smazani-akce.md`,
  `docs/navrh/archiv.md` (cache ve `.work/`).
