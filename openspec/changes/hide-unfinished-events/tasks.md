## 1. Název akce a složka na disku

- [ ] 1.1 `archive.py`: `IGNORED` z `cleanup.py`, `event_names()` vrací
  názvy bez přípony (jednou i při kolizi), `event_dir(name)` najde
  `name` nebo `name.ignored`, odmítne název končící na `.ignored`
  a při obou složkách vyhodí novou výjimku `Collision`
- [ ] 1.2 `archive.py`: přímé `self.archiv / name` (počty souborů
  v `list_events`, cesta k `_metadata.json` a XMP v produkci) přes
  `event_dir`; `list_events` u kolize vrátí `kolize: true`
- [ ] 1.3 `Workspace.publish(name)`: odebere příponu (cíl nesmí
  existovat, jinak `Collision`), bez přípony nic nedělá, ve vývojovém
  režimu nic nedělá
- [ ] 1.4 `app.py`: `Collision` → 409 `kolize_pripony` ve společném
  `event_dir`
- [ ] 1.5 `scan.scan` a `Imports.sha_cache` klíčované názvem akce, ne
  `event_dir.name` (volání v `app.py` a `importer.py`)
- [ ] 1.6 Testy v `tests/test_archive.py`: seznam se skrytou akcí,
  otevření, název s příponou odmítnut, kolize, `publish`; cache skenu
  přežije `publish` (`tests/test_scan.py`)

## 2. Import

- [ ] 2.1 `importer.check_new_name`: odmítne název končící na
  `.ignored` a název, k němuž existuje složka s příponou
- [ ] 2.2 `importer.create_event`: v produkci zakládá `název.ignored`;
  `import_execute` zjistí cestu až po zámku
- [ ] 2.3 `static/app.js`: upozornění u dokončené akce v průvodci
  importu doplnit „Immich je uvidí hned“
- [ ] 2.4 Testy v `tests/test_import.py`: nová akce skrytá, kolize
  názvu se skrytou akcí, import do stávající skryté akce
- [ ] 2.5 README (Archiv, Import) aktualizovat

## 3. Dokončení akce

- [ ] 3.1 `app.py` `akce_finish`: po úspěšném exportu `ws.publish`;
  při `OSError`/`Collision` vrátit `dokonceno` na `None` a odpovědět
  `chyba: "zverejneni"` s textem chyby
- [ ] 3.2 `static/app.js`: hláška při `zverejneni` („Akci nešlo
  zveřejnit pro Immich: …“) a při `kolize_pripony` na ploše i v seznamu
- [ ] 3.3 Testy v `tests/test_app.py`: dokončení skryté akce odebere
  příponu a sidecary jsou v nové složce; selhání přejmenování (podvržený
  `os.rename`) nechá akci nedokončenou a složku s příponou; opakované
  dokončení příponu nevrátí; vývojový režim nepřejmenovává
- [ ] 3.4 README (Tok práce, Dokončení akce; Výstupy, Immich)
  aktualizovat

## 4. Index

- [ ] 4.1 `index.py`: soubory a náhled přes `event_dir`; `link` dostane
  skutečný název složky, karta ukazuje název akce bez přípony
- [ ] 4.2 Test v `tests/test_index.py`: odkaz na skrytou akci vede na
  `./… .ignored/`, název bez přípony

## 5. Příkaz `skryt`

- [ ] 5.1 `__main__.py`: `python -m fotoarchiv skryt --archiv …
  --work … [--zapis-do-archivu]`; vypíše nedokončené akce bez přípony,
  s přepínačem je přejmenuje, kolize přeskočí a vypíše
- [ ] 5.2 Testy v `tests/test_archive.py` (vedle převzetí; CLI volat
  přes `fotoarchiv.__main__.main` jako u `prevzit` v `test_app.py`):
  výpis bez zápisu, označení nezpracované i rozpracované, dokončená beze
  změny, kolize přeskočena
- [ ] 5.3 README (příkazy, Immich: po ručním nakopírování akce spustit
  znovu) a AGENTS.md (Příkazy, invariant o `.ignored` u složek akcí)

## 6. Ověření

- [ ] 6.1 `.venv/bin/python -m pytest -q` a `node --test
  tests/js/*.test.mjs` zelené (počet testů z výstupu)
- [ ] 6.2 Ruční průchod v prohlížeči na vygenerovaném archivu ve scratch
  adresáři v produkčním režimu: `skryt`, import nové akce, otevření,
  dokončení, seznam a `_INDEX.html`
