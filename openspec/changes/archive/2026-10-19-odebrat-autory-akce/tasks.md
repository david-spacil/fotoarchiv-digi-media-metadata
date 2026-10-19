# Tasks

## 1. Datový model `/2` a dědění

- [x] 1.1 `archive.SCHEMA` na `fotoarchiv-digi-media-metadata/2`;
  v `model.py` výčet vypuštěných klíčů po úrovních a `upgrade(doc)`
  (převede `/1` na `/2`, vrátí odebrané klíče s počty); `resolve`
  vypuštěné klíče přeskočí, `clean` je odstraní. Test v
  `tests/test_model.py`: `upgrade` na dokumentu se všemi vypuštěnými
  klíči, `clean` po uložení, `resolve` bez `akce.autori`.
- [x] 1.2 `Workspace.load` vrací dokument `/1` převedený přes `upgrade`,
  verze zůstává hashem souboru na disku. Test v `tests/test_archive.py`:
  načtení `/1` nic nezapíše, uložení s vrácenou verzí projde a zapíše
  `/2`.
- [x] 1.3 `static/inherit.js` přeskakuje stejné vypuštěné klíče; fixtura
  `tests/fixtures/inheritance/autori-jen-u-akce.json` přepsaná na
  „autoři u akce se nedědí“ (soubory bez autorů), všechny fixtury na
  `/2`, nová fixtura s `skupina.datum_od`. Ověří
  `node --test tests/js/*.test.mjs` i `pytest tests/test_model.py`
  (obě implementace proti týmž fixturám).
- [x] 1.4 Test v `tests/test_xmp.py`: akce s `akce.autori` a skupinou
  bez autorů → sidecar bez tagu `autor/…`; ostatní testy a fixtury
  na `/2`.
- [x] 1.5 `README.md`, Datový model: `schema` `/2`, autoři jen u skupiny
  a souboru, odstavec o vypuštěných klíčích proti `/1` (bez zmínky
  o `datum_od/do` u skupiny v příkladu). Kontrola: `grep -n
  "metadata/1\|autoři celé akce\|autory celé akce" README.md docs` vrátí jen
  zmínku o převodu.

## 2. Klient: bez autorů akce a dat skupiny

- [x] 2.1 `static/app.js`: `FIELDS.akce` bez `autori`, `FIELDS.skupina`
  bez `datum_od`/`datum_do`; zrušit filtry `k !== "autori"`, pole
  „Celá akce“ v kroku skupiny a autoři průvodce i importu a řádek
  „Autoři celé akce“ v souhrnu importu. Ověření: `grep -n "autori"
  fotoarchiv/static/app.js` nemá výskyt vázaný na `akce`.
- [x] 2.2 `static/importdesc.js` bez `akce_autori`; upravit
  `tests/js/importdesc.test.mjs` (výchozí popis nemá `akce.autori`,
  ani když server pošle starší `akce_autori`).
- [x] 2.3 `docs/navod/pruvodce-akce.md` (krok skupiny a autoři) a
  `docs/navod/import.md`
  (krok skupiny a autoři, souhrn): bez autorů celé akce.

## 3. Server: import bez autorů akce

- [x] 3.1 `app.py` + `importer.py`: detail importu bez `akce_autori`,
  `write_description` a `merge_proposal` bez autorů akce, převzetí
  návrhu při prvním otevření nepřenese `akce.autori` ze staršího
  návrhu. Testy v `tests/test_import.py` (stávající testy autorů akce
  přepsat): nová akce bez `akce.autori` i když popis importu je má,
  akce s `_metadata.json` má `akce` beze změny, návrh skupin bez autorů
  akce, starší návrh s autory akce → `_metadata.json` bez nich
  (`test_app.py`).
- [x] 3.2 `docs/navod/import.md`: zápis popisu bez autorů akce.

## 4. Příkaz `migrovat`

- [x] 4.1 `__main__.py`: podpříkaz `migrovat` podle `skryt` (bez
  `--zapis-do-archivu` jen výpis akcí `/1` a odebraných klíčů s počty;
  s přepínačem uložení `/2` přes `Workspace(zapis=True).save` s verzí;
  přenos záznamu o exportu, když ukazoval na starou verzi a akce
  neměla `akce.autori`; u akcí s `akce.autori` počet souborů, které
  autory ztratí; chyba/konflikt jedné akce nezastaví ostatní, nenulový
  kód). Testy v `tests/test_archive.py` nebo novém
  `tests/test_migrovat.py` podle vzoru testů CLI: výpis nanečisto nic
  nezapíše, převod, přenos záznamu o exportu (`export_version` = nová
  verze), akce s `akce.autori` (záznam beze změny, počet ve výpisu),
  opakované spuštění beze změny.
- [x] 4.2 `docs/provoz/` (příkazy, spuštění, Docker) a `AGENTS.md`
  (Příkazy): `migrovat`
  a postup nasazení (zastavit server, výpis, `--zapis-do-archivu`,
  start).

## 5. Ověření

- [x] 5.1 Celé sady: `.venv/bin/python -m pytest -q` a `node --test
  tests/js/*.test.mjs` (kontrola počtu spuštěných testů).
- [x] 5.2 Prohlížeč nad dummy archivem (vývojový režim, akce `/1`
  s `akce.autori`, `osoby` a `skupina.datum_od`): akce se otevře,
  formulář akce nemá autory, formulář skupiny nemá datum od/do, krok
  skupiny a autoři průvodce i importu nemá „Celá akce“, uložení zapíše
  `/2` do `.work/`. Krok importu prohlížeč neprošel; sdílí panel
  `renderGroupsPanel` s průvodcem a souhrn kryje `importdesc.test.mjs`.
- [x] 5.3 `migrovat` nad kopií dummy archivu: výpis, převod, plocha
  dokončené akce bez „neexportované změny“.
- [x] 5.4 Ruční kontrola uživatelem po nasazení: výpis `migrovat` nad
  produkcí a převod při zastaveném serveru.
