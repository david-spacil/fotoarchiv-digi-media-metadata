# Tasks

## 1. Kontrola při generování náhledu

- [x] 1.1 `app.py` `thumb_response`: před vytvořením náhledu zjistit
      platný výsledek v cache kontroly akce (`integrity.cached`);
      při miss náhledu i kontroly spustit `integrity.check` a zapsat
      do cache `<work>/cache/kontrola/<nazev>.json`
      (helper `integrity.ensure_cached(path, nazev, work)` v
      `integrity.py`)
- [x] 1.2 Vyjmout odvození názvu akce a cesty cache z kódu příkazu
      `zkontrolovat`, aby náhled i CLI psaly do stejného souboru
- [x] 1.3 Testy: miss náhledu píše cache; druhý náhled (i jiná
      velikost) nečte; hit kontroly bez náhledové cache nespustí
      kontrolu; náhled z podsložky při úklidu nekontroluje

## 2. Souhrn poškozených (server)

- [x] 2.1 `integrity.summary(cache_path, records)` — počet a mapa
      `název → {stav, duvody}` s vyloučením `overeno`/`vyradit`
      a bez I/O nad cache JSONem; testy na tvary cache
- [x] 2.2 `archive.list_events`: klíč `poskozene` (počet) z cache
      + `_metadata.json`; detail akce v `app.py` o `poskozene` mapu
- [x] 2.3 Testy `test_app.py` / `test_archive`: list s cache bez
      cache, s `overeno`, s `vyradit`; detail vrací důvody

## 3. Příznak `overeno`

- [x] 3.1 `model.py`: `overeno` do `LOCAL_KEYS["soubor"]`,
      `clean()` nechat projít (ruční pole); ověřit, že `xmp.py`
      i `index.py` nečerpají neznámá klíče (stejně jako `vyradit`)
- [x] 3.2 `static/inherit.js` + fixture testy: `overeno` se nedědí
- [x] 3.3 Test uložení: `overeno` přežije round-trip PUT→GET,
      export sidecaru ho neobsahuje

## 4. Klient: odznak, dlaždice, přepínač

- [x] 4.1 Seznam akcí: `badge poskozene` „N poškozených“ podle
      vzoru `badge vyresit`; barva v `style.css`
- [x] 4.2 Plocha: lišta `info poskozene` (vzor „k vyřazení“);
      dlaždice třída `damaged` + `title` s důvodem
      (`STAV_KONTROLY` z `static/integrity.js`)
- [x] 4.3 Akce dlaždice: „Považovat za v pořádku“ / zrušení
      (přepínač `overeno`, `flushSave`), „Označit k vyřazení“
      pro poškozené stejné jako dosud (`vyradit`)
- [x] 4.4 `node --test tests/js`+: přepínač `overeno`, počítání
      odznaku mimo vyřazené/potvrzené

## 5. Dokončení

- [x] 5.1 `README.md`: odznak, `overeno` v datovém modelu, náprava
      poškozených přes vyřazení (žádná nová složka)
- [x] 5.2 Celý běh `.venv/bin/python -m pytest -q` +
      `node --test tests/js/*.test.mjs`
- [x] 5.3 Ověření v prohlížeči (dev i prod režim): odznak po
      vyprázdnění cache náhledů, přepínač, vyřazení poškozeného
      včetně sidecaru a mizení z odznaku
