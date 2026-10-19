## 1. Server: seznam vyloučených a plán

- [x] 1.1 `Imports.set_excluded` + `POST /api/import/<id>/vyloucene`
  (klíč `vyloucene` v `import.json`, jen cesty z výběru, `probiha` 409,
  neplatný tvar 400, vlastník z relace); `overview` vrací `vyloucene`.
  Ověřit testy v `tests/test_import.py` (uložení, filtr cizích cest,
  odmítnutí během provádění) a `tests/test_app.py` (cizí import
  nenalezen, jméno z relace).
- [x] 1.2 `iter_plan` se stavem `vylouceny` po určení duplicit a kolizí;
  `plan_ok` ze stavů `ok` i `vylouceny`; `defaults` vrací i RAWy plánu
  pro párování. Ověřit testy: vyloučený zůstane v `defaults.soubory`,
  vyloučená kopie dál dělá z druhé kopie duplicitu, vyloučení nemění
  kolize jmen.
- [x] 1.3 Provedení: vyloučený soubor se nepřenese, zůstane ve stagingu
  (import není `zahozeno`) nebo ve zdroji (`zdroj_zbyva`, import se
  nezruší), nemá záznam v `_metadata.json` ani návrhu skupin. Ověřit
  testy pro nahrání i zdroj `přetřídit` (rozšířit `test_execute_*`
  a `test_source_execute_moves`) a že každý nový test na kódu z
  `origin/main` selže.

## 2. Klient: vyloučení v kroku skupiny a autoři

- [ ] 2.1 Nový modul `static/vylouceni.js` (přepnutí nad výběrem, páry
  fotka–RAW podle cesty bez přípony bez ohledu na velikost písmen,
  počet pro Importovat) s testem `tests/js/vylouceni.test.mjs`;
  ověřit `node --test tests/js/*.test.mjs` (číst řádek `# tests`).
- [ ] 2.2 `app.js`: Del v kroku importu jako přepínač vyloučit / vrátit,
  tlačítko v nástrojích skupin se stejným přepínáním a popiskem podle
  výběru („Vyloučit z importu“ / „Vrátit do importu“), dialog k RAWům, ukládání
  na server (debounce), třída `excluded` a ikona na dlaždici, řádek
  „Vyloučeno: N médií, M RAWů“, počet v Importovat, vypnuté tlačítko
  při vyloučení všeho, skupiny jen z vyloučených bez upozornění na
  autory, vyloučené v „Co by se zapsalo“ chybí. Průvodce akce: Delete
  dál nic. Ověřit `importdesc.test.mjs` (upozornění na autory
  s vyloučenými) a prohlížečem (úkol 3.1).
- [ ] 2.3 Plán a výsledek vypíší vyloučené zvlášť („vyloučeno“), u zdroje
  mezi tím, co zůstalo. Ověřit prohlížečem (úkol 3.1).
- [ ] 2.4 README (Import → Skupiny a autoři, Výsledek; průvodce akce —
  Delete tam dál nic) ve stejném kroku; ověřit grepem, že žádné místo
  netvrdí, že Delete v kroku importu nic nedělá.

## 3. Ověření

- [ ] 3.1 Prohlížeč nad vygenerovanými dummy daty ve scratch (nahraný
  import JPG+RW2 páry, zdroj `přetřídit`), vývojový i produkční režim
  na kopii: Del a tlačítko, dialog RAW (obě volby), počty, návrat přes
  Pokračovat, změna výchozího rozdělení, zpět na plán, provedení
  a výsledek, soubory na disku. Reálná data se nepoužívají.
- [ ] 3.2 Celé sady `.venv/bin/python -m pytest -q` a `node --test
  tests/js/*.test.mjs` zelené; `openspec validate vyloucit-z-importu
  --strict`.
- [ ] 3.3 Ruční zkouška uživatelem na mobilu/desktopu (vzhled
  vyloučené dlaždice, dialog RAW).
