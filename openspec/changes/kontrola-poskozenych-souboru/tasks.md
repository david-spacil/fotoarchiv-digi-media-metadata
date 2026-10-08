# Tasks

## 1. Testovací vzorky

- [ ] 1.1 Přidat do `tests/fixtures/integrity/` malé generované vzorky
  (zdravý JPEG s šumem, nuly na začátku, nuly na konci, nuly uprostřed
  64 KiB, useknutý JPEG, useknutý s `FFD9`, 0 B, PNG s plochou barvou,
  krátké MP4 a MP4 bez `moov`) a skript, který je vygeneruje; ověřit,
  že skript je deterministický (dva běhy = stejné sha256)
- [ ] 1.2 Ověřit na vzorcích z issue (`20151107_140851.jpg`,
  `20151107_135155.jpg`, mimo repozitář) a zapsat do testu jen jejich
  očekávaný stav a důvod, ne soubory

## 2. Kontrola souboru (`file-integrity`)

- [ ] 2.1 Vytvořit `fotoarchiv/integrity.py`: test zarovnaných úseků nul
  s nejdelším úsekem a polohou, dekódování fotky přes Pillow s `draft`,
  `ffprobe` u videa, klasifikace a české důvody; ověřit
  `tests/test_integrity.py` nad vzorky ze skupiny 1 (všechny scénáře
  „Kontrola souboru“ a „Kontrola podle typu souboru“)
- [ ] 2.2 Generátor `iter_check` s průběhem po `STEP` a sha256 v témže
  čtení; ověřit testem, že sha256 souhlasí s `importer.file_sha256`
  a že průběh přijde i uvnitř souboru většího než `STEP` (podvržený
  `STEP`)
- [ ] 2.3 Cache `.work/cache/kontrola/<jméno>.json` podle (klíč,
  velikost, mtime_ns) a zápis sha256 do cache hashů; ověřit testem, že
  nezměněný soubor se podruhé nečte (podvržené `open`) a změněný ano
- [ ] 2.4 Chybějící `ffprobe`: video jen testem nul s poznámkou; ověřit
  testem s podvrženým `shutil.which`
- [ ] 2.5 Zapsat kontrolu do README (nová podkapitola: co se kontroluje,
  stavy, práh, cache) a ověřit, že odkazy z kapitoly Import na ni vedou

## 3. Příkaz `zkontrolovat`

- [ ] 3.1 Přidat do `__main__.py` příkaz `zkontrolovat [AKCE]` (kořen
  a `RAW.ignored/`, ostatní podsložky a `Thumbs.db` přeskočit, nálezy
  na stdout, průběh na stderr, report
  `.work/kontrola/report-<čas>.json`, cache zapisovaná po akcích);
  ověřit `tests/test_integrity.py` nad dočasným archivem se dvěma
  akcemi: výpis, report, archiv beze změny (sha256 všech souborů před
  a po), exit kód
- [ ] 3.2 Report s nejdelším úsekem nul i u souborů pod prahem; ověřit
  testem se vzorkem s 8 KiB nul
- [ ] 3.3 Doplnit příkaz do README (příkazy) a AGENTS.md (Příkazy);
  ověřit, že zdokumentovaný příkaz běží tak, jak je napsaný, nad
  `fotoarchiv-dummy`

## 4. Kontrola v importu (`photo-import`)

- [ ] 4.1 `Imports`: kontrola souborů importu (nahrané i zdroj),
  výsledky z cache v `overview`; endpoint `POST /api/import/<id>/kontrola`
  se streamem NDJSON; ověřit testy v `tests/test_import.py`
  a `tests/test_app.py` (průběh, výsledky z cache při návratu,
  cizí import 404)
- [ ] 4.2 Volba `povolene_poskozene` v `import.json` přes
  `POST /api/import/<id>/poskozene`; plán a provedení vyřadí nepovolené
  poškozené a označí je `poskozeny` s důvodem, změněný soubor
  zkontrolují znovu; výsledek je uvede zvlášť a nechá v pracovním
  adresáři; ověřit testy scénářů „Volba u podezřelých souborů“
  a „Poškozené soubory v plánu a výsledku“
- [ ] 4.3 `DELETE /api/import/<id>/soubor`: smaže jen poškozený nahraný
  soubor shodný s kontrolou, odmítne zdravý, změněný a během provedení;
  zalogovat; ověřit testy včetně odmítnutí
- [ ] 4.4 Ověření velikosti po přenosu v `_copy` i `_move`; ověřit
  testem s podvrženým `os.stat` cíle, že výsledek uvede chybu a soubor
  zůstane
- [ ] 4.5 Klient průvodce (`static/app.js`): průběh kontroly v přehledu,
  seznam poškozených s důvodem, volba „přesto importovat“, potvrzovací
  dialog smazání, poškozené v plánu a výsledku, zablokované tlačítko do
  konce kontroly; ověřit v prohlížeči (`web-ui-headless-checks`) nad
  dočasnými daty se vzorky ze skupiny 1
- [ ] 4.6 Aktualizovat README (Import: Přehled, Plán, Provedení,
  Výsledek) a ověřit, že popis odpovídá chování z 4.5

## 5. Kontrola zdroje v `přetřídit` (`unsorted-import`)

- [ ] 5.1 Kontrola zdroje s průběhem po bajtech a sha256 do cache
  zdroje; ověřit testem, že plán po kontrole zdroj nečte (podvržené
  čtení)
- [ ] 5.2 Smazání poškozeného souboru zdroje jen v produkčním režimu,
  pod zámkem zdroje relace a se shodným snímkem; poškozené zůstávají ve
  zdroji a výsledek je uvede, složka se zbylým poškozeným souborem
  nezanikne; ověřit testy scénářů „Poškozené soubory ve zdroji“
  (produkční i vývojový režim, cizí zámek)
- [ ] 5.3 Klient: ve vývojovém režimu smazání u zdroje nenabízet; ověřit
  v prohlížeči
- [ ] 5.4 Aktualizovat README (Import ze složky `přetřídit`) a ověřit
  soulad s 5.2

## 6. Integrace

- [ ] 6.1 Spustit `pytest -q` a `node --test tests/js/*.test.mjs`,
  ověřit počty testů v souhrnu (ne jen konec výpisu)
- [ ] 6.2 Projít celý import v prohlížeči nad dočasným archivem: upload
  se vzorky z issue i import ze složky `přetřídit`, oba režimy; ověřit
  stavy přehledu, plánu a výsledku a obsah archivu po provedení
