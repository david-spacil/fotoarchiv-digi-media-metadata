## 1. Výpočet a cache (`fotoarchiv/velikost.py`)

- [ ] 1.1 Rekurzivní součet `st_size` bez sledování symlinků, kolize
  přípony sečte obě složky; ověřit pytestem nad dummy stromem
  v `tmp_path` (podsložky `RAW.ignored`, `_metadata.json`,
  `Thumbs.db`, symlink na složku mimo akci, kolize)
- [ ] 1.2 Třída `Velikosti`: cache `.work/velikosti.json` (akce, koš),
  atomický zápis pod zámkem, načtení při startu; ověřit pytestem
  (zápis, znovunačtení, poškozený soubor = prázdná cache)
- [ ] 1.3 Fronta přepočtů a pracovní vlákno s denním přepočtem celého
  archivu i koše a úklidem zmizelých položek, doplnění chybějících při
  startu; ověřit pytestem s přímým voláním kroku vlákna (bez spánku)
- [ ] 1.4 Přesuny údaje: do koše, z koše, odebrání vysypaných;
  výsledek přepočtu zmizelé akce se zahodí; ověřit pytestem

## 2. Server (`app.py`, `trash.py`)

- [ ] 2.1 `create_app(…, velikost_interval=…)`: instance `Velikosti`,
  vlákno jen s intervalem, `__main__.py` předá denní interval; ověřit,
  že stávající testy projdou bez vlákna
- [ ] 2.2 `GET /api/akce` s polem `bajtu` (`null` bez údaje, akce bez
  údaje se zařadí k přepočtu, archiv se nečte navíc); ověřit pytestem
- [ ] 2.3 `GET /api/velikost` se součtem akcí (jen existující) a koše
  pro každého přihlášeného; ověřit pytestem pro archiváře a admina
- [ ] 2.4 Přepočet po importu (i z `přetřídit`), úklidu a dokončení;
  ověřit pytestem, že akce je po operaci ve frontě a po kroku vlákna
  má nový údaj
- [ ] 2.5 Smazání do koše přenese údaj, obnovení vrátí a zařadí
  přepočet, vysypání odebere; `trash.entries` vrací `bajtu`; ověřit
  pytestem dopad na součet koše
- [ ] 2.6 Ve vývojovém režimu přepočet archiv jen čte a smazání (plán)
  údaj nepřesune; ověřit pytestem

## 3. Klient

- [ ] 3.1 `fronta.js`: přesun `fmtSize`, řazení `velikost` (bez údaje
  na konci, shoda podle data), `celkemText`; ověřit
  `node --test tests/js/fronta.test.mjs` (doplnit testy)
- [ ] 3.2 `app.js`: velikost v `eventMeta`, načtení `/api/velikost`
  a řádek součtu pod filtry, řazení v nabídce a v adrese
  (`#/?razeni=velikost`); ověřit ručně nad
  `~/Dokumenty/fotoarchiv-scratch/test-archiv`
- [ ] 3.3 Stránka Koš: sloupec velikosti; ověřit ručně nad test-archiv
  (smazání a obnovení akce)

## 4. Dokumentace

- [ ] 4.1 `docs/navod/seznam-akci.md` (velikost, řazení, součet),
  `docs/navod/smazani-akce.md` (velikost v koši),
  `docs/navrh/archiv.md` (`.work/velikosti.json`, denní přepočet);
  ověřit čtením diffu a odkazů
- [ ] 4.2 Celé testy: `.venv/bin/python -m pytest -q`
  a `node --test tests/js/*.test.mjs` projdou
