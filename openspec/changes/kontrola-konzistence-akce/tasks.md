## 1. Kontrola akce

- [x] 1.1 Nový modul `fotoarchiv/consistency.py`: `check(event_dir, doc)`
  vrací seřazené nálezy `{"druh", "nazev"}` (`nepodporovany`,
  `sirotek_xmp`, `raw`, `podslozka`, `chybejici`), porovnání přes
  `_key`; ověří 1.2
- [x] 1.2 Nový `tests/test_consistency.py`: scénáře z
  `event-consistency` (zip + pdf + `Thumbs.db`, osiřelý sidecar,
  `a.JPG.xmp` k `a.jpg`, záznam bez souboru, `Video` vs. `RAW.ignored`,
  akce bez metadat, dočasné soubory a `_metadata.json` se nehlásí);
  `pytest tests/test_consistency.py` zelené

## 2. Seznam akcí

- [x] 2.1 `archive.list_events`: pole `kontrola` (počty podle druhu)
  z `consistency.check` nad už načteným výpisem a `doc`; u kolize
  prázdné
- [x] 2.2 `static/app.js` `showList`: štítek „k vyřešení“ s popiskem
  počtů podle druhu (sklonované), styl v `style.css`
- [x] 2.3 Testy v `tests/test_archive.py`: akce se zipem má
  `kontrola`, čistá akce prázdnou, sidecary exportované akce se
  nehlásí; `pytest tests/test_archive.py` zelené
- [x] 2.4 README (Tok práce, bod 1 Seznam akcí) aktualizovat

## 3. Úklid: `ostatni.ignored` a úklid z plochy

- [x] 3.1 `cleanup.py`: `OSTATNI = "ostatni.ignored"`, `plan(...,
  ostatni=True)` přidá přesuny nepodporovaných souborů a osiřelých
  sidecarů přes `move_into` (existující složka, kolize, soubor
  stejného jména jako složka); `ostatni.ignored` se jako podsložka
  přeskakuje
- [x] 3.2 `app.py` `cleanup_args`: tělo `ostatni` (výchozí `True`);
  `z_plochy` (alias `jen_vyradit`) vezme `volby` z těla s výchozí
  `None` pro každou podsložku, RAWy z kořene a ostatní zapnuté
- [x] 3.3 Testy v `tests/test_cleanup.py`: zip a osiřelý sidecar do
  `ostatni.ignored`, kolize, přesun vypnutý, provedení; v
  `tests/test_app.py`: úklid z plochy přesune pdf i RAW, podsložka bez
  volby zůstane, vývojový režim jen plán
- [x] 3.4 `static/app.js`: průvodce `renderCleanup` zaškrtávátko
  „Přesunout ostatní soubory do ostatni.ignored“; `discardCleanup`
  posílá `z_plochy` a v dialogu ukáže volbu přesunout/ponechat
  u podsložek (sdílet s průvodcem), plán se po změně volby přepočte
- [x] 3.5 README (Podsložky a RAW) aktualizovat

## 4. Plocha a dokončení

- [x] 4.1 `app.py` detail akce: `kontrola` (seznam nálezů) místo
  `nezpracovane`; test v `tests/test_app.py`
- [x] 4.2 `static/app.js`: `missingItems` přidá položky nálezů po
  druzích (klik → dialog s názvy), záznam bez souboru nahradí dnešní
  „N souborů chybí v kořeni“; `renderBar` ukáže Uklidit… i při nálezu
  s nápravou; odebrat `<details class="other">` z `renderGrid`
- [x] 4.3 Dokončení: potvrzení v `runExport` vypíše i nálezy (plyne
  z 4.2), akce se po potvrzení dokončí
- [x] 4.4 README (Tok práce, body 3 a 4) aktualizovat

## 5. Ověření

- [x] 5.1 Celé sady: `.venv/bin/python -m pytest -q` a
  `node --test tests/js/*.test.mjs` zelené
- [x] 5.2 Prohlížeč nad vygenerovaným archivem v scratch adresáři (akce
  se zipem, pdf, osiřelým sidecarem, RAWem, podsložkou a záznamem bez
  souboru; čistá akce): štítek v seznamu, lišta a dialog s názvy, úklid
  z plochy v produkčním režimu, varování při dokončení; snímky
  obrazovky
