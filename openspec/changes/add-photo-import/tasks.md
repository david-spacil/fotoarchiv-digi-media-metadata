## 1. Staging a nahrávání

- [x] 1.1 `fotoarchiv/importer.py`: založení importu (`.work/import/<id>/`,
  `import.json`), uložení streamu po blocích do dočasného souboru,
  sha256 při zápisu, přejmenování po dokončení; ověřit
  `tests/test_import.py` (přerušený zápis v `import.json` není)
- [x] 1.2 Kontrola volného místa a limitu velikosti souboru; ověřit testem
  s podvrženým `disk_usage`
- [x] 1.3 Zahození importu a mazání stagingů starších 7 dní; ověřit testem
  se starým `import.json`
- [x] 1.4 Prefix `.import-` v `archive.is_metadata`; ověřit testem, že
  `list_events` a `scan.root_files` dočasný soubor nepočítají

## 2. Přehled a plán

- [x] 2.1 Přehled: `scan.scan` nad stagingem, typy podle přípony, RAWy,
  nepodporované, `Thumbs.db` vynechat, navržené datum; ověřit testem
  s podvrženým exiftoolem (scénář „Smíšený výběr“)
- [x] 2.2 Validace názvu nové akce (vzor, `/`, `\`, existence přes `_key`);
  ověřit testem (scénář „Existující název“)
- [x] 2.3 `importer.plan`: cíle kořen / `RAW.ignored`, kolize s existujícím
  souborem a uvnitř výběru, duplicity podle sha256 s předfiltrem
  velikosti a cache; ověřit testy „Kolize jména“ a „Duplicita s jiným
  jménem“

## 3. Provedení

- [x] 3.1 `importer.execute`: nový plán, kopie do `.import-*.tmp`, fsync,
  mtime, kontrola cíle a rename, pokračování po chybě, smazání ze
  stagingu; ověřit testy „Import do nové akce“, „Kolize vzniklá po
  zobrazení plánu“ a selhání jednoho souboru (podvržená chyba kopie)
- [x] 3.2 Nová akce: `os.mkdir`, odmítnutí při existenci, zámek pro relaci;
  ověřit testem souběžného vzniku složky

## 4. API

- [x] 4.1 Endpointy `/api/import…` v `app.py` včetně kontroly relace,
  423 bez zámku a 403 ve vývojovém režimu; ověřit testy přes Flask
  test client (scénáře „Import do akce, kterou upravuje jiný“,
  „Vývojový režim“)
- [x] 4.2 Úklid starých stagingů při startu v `__main__.py`; ověřit ručním
  spuštěním se starým stagingem v `.work/import/`

## 5. Klient

- [x] 5.1 Trasa `#/import` a `#/import/<id>`, tlačítko Importovat na seznamu
  a ploše (předvybraný cíl); ověřit v prohlížeči
- [ ] 5.2 Krok Soubory: výběr souborů, složky, drag&drop včetně podsložek,
  upload 2–3 souběžně s průběhem; ověřit v prohlížeči na složce
  s podsložkou a přerušením (zavřít stránku → archiv beze změny)
- [x] 5.3 Kroky Přehled, Cíl (stávající/nová, návrh data, upozornění
  u dokončené akce), Plán, Výsledek s otevřením akce a zahozením;
  ověřit v prohlížeči ve vývojovém i produkčním režimu na kopii archivu
  ve scratch adresáři

## 6. Dokumentace a ověření

- [x] 6.1 `README.md` (Tok práce, sekce Import), `AGENTS.md` (Stav);
  ověřit, že popis odpovídá specu `photo-import`
- [x] 6.2 Celé testy `.venv/bin/python -m pytest -q` a `node --test tests/js`
  zelené; end-to-end import do nové a stávající akce na kopii archivu,
  otevření akce ukáže nové soubory

## 7. Průběh plánu a provedení

- [ ] 7.1 Klient: tlačítka, která čekají na server (plán, nahrání,
  provedení, zahození), se zablokují a ukážou stav; ověřit
  v prohlížeči dvojklikem na „Ukázat plán“ (v logu jeden `/plan`)
- [ ] 7.2 `importer.plan` / `root_hashes` s událostmi průběhu hashování
  (soubor, po 64 MB), endpoint `plan` jako NDJSON stream, klient
  s ukazatelem porovnání; ověřit testem (pořadí událostí, cache se
  počítá jako hotová) a v prohlížeči na velké akci
- [ ] 7.3 `importer.execute` jako generátor událostí (start, průběh po
  64 MB, soubor, výsledek), odebrání ze stagingu po každém souboru;
  ověřit testem pořadí událostí a přerušení uprostřed souboru (žádný
  `.import-*.tmp`, přenesené pryč ze stagingu)
- [ ] 7.4 Endpoint `provest` jako NDJSON stream, odmítnutí před startem
  dál JSON se stavem; ověřit Flask test clientem
- [ ] 7.5 Klient: čtení streamu, ukazatel podle bajtů, výsledek
  z posledního řádku; ověřit v prohlížeči na velkém videu a zavřením
  záložky uprostřed
- [ ] 7.6 `README.md` (Import, Provedení): průběh plánu a provedení
  a chování při přerušení

## 8. Rozpracované importy

- [ ] 8.1 Vlastník importu podle jména (`names.normalize`), `jmeno`
  místo `relace` v API, uložení zvoleného cíle do `import.json`;
  ověřit testy (cizí jméno → 404, jiné pořadí slov/diakritika → vlastní)
- [ ] 8.2 `GET /api/import?jmeno=…` se seznamem rozpracovaných importů;
  ověřit testem
- [ ] 8.3 Příznak „provádí se“ v paměti, 409 `probiha` pro upload,
  zahození a druhé provedení; ověřit testem souběhu
- [ ] 8.4 Klient: sekce „Moje rozpracované importy“ na seznamu akcí
  (Pokračovat, Zahodit), předvyplnění cíle po návratu; ověřit
  v prohlížeči zavřením záložky a pokračováním v nové
- [ ] 8.5 `README.md` (Import, Souběh): vlastník podle jména, seznam
  rozpracovaných importů

## 9. Pojistky

- [ ] 9.1 Provedení se zámkem nejdřív smaže `.import-*.tmp` starší než
  1 h v kořeni akce a v `RAW.ignored/`, uvede je v logu a ve výsledku;
  ověřit testem (starý smaže, čerstvý nechá, jiné skryté soubory nechá)
