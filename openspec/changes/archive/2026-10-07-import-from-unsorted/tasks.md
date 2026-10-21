## 1. Přehled `přetřídit` (`fotoarchiv/unsorted.py`)

- [x] 1.1 Výpis složek první úrovně (bez `*.ignored` a souborů),
  rekurzivní výpis souborů složky s vynecháním podsložek `*.ignored`
  a `Thumbs.db`, počty podle `importer.kind`, názvy podsložek; ověřit
  testy v `tests/test_unsorted.py` (scénáře „Složka s duplicitami“,
  „Podsložky v počtech“, chybějící `přetřídit` → prázdný seznam)
- [x] 1.2 Datum z názvu složky (`d.m.yyyy`, `yyyy_mm_dd`, `yyyy_m_d`,
  `dd_mm_yyyy`, samotný rok jen jako rok); ověřit parametrizovaným
  testem na názvech z `přetřídit` (`komise_Vzorovice_31.8.2012`,
  `2018_10_22_Tisková…`, `2019_4_8_Zlaty…`,
  `Opavske_expozitury_Prislo_12_09_2019`, `DOD 2017`)
- [x] 1.3 EXIF přes `scan.scan` po složkách zdroje s `cache_name`
  `pretridit-<sha1>`, rozsah dat, navržená akce (EXIF → název →
  bez data); ověřit testem s podvrženým exiftoolem, že druhé volání
  exiftool nespustí (scénáře „EXIF má přednost“, „Druhé otevření“)

## 2. Import se zdrojem (`fotoarchiv/importer.py`)

- [x] 2.1 `Imports.create` se `zdroj` (validace názvu: první úroveň,
  bez `/`, `..`, `.ignored`; existující import téže složky uživatele
  vrátí jeho id; volitelný cíl), `owned` uvádí `zdroj`; ověřit testy
  v `tests/test_import.py`
- [x] 2.2 Sestavení záznamů souborů ze zdroje (`cesta` s prefixem
  složky, `zdroj` místo `ulozeno`) a `overview` nad skeny zdroje
  s klíčem `cesta`; ověřit testem scénáře „Vyloučená podsložka“
  a předvolby skupin podle podsložek
- [x] 2.3 Hash jen u souborů se shodnou velikostí (v kořeni cíle nebo
  ve výběru), cache a události `hash`/`hash_prubeh`, zástupná hodnota
  pro ostatní; ověřit testem, že bez shody velikostí se žádný soubor
  zdroje nečte, a scénářem „Duplicita zůstane“
- [x] 2.4 Přesun ze zdroje v `execute` (přenos jako parametr, rename
  s kontrolou cíle, chybějící zdroj / `EXDEV` → chyba souboru, průběh
  po souborech); ověřit testy: obsah a mtime zachované, existující cíl
  nepřepsán, zmizelý zdrojový soubor = selhaný
- [x] 2.5 Úklid zdroje odspodu (prázdné nebo jen `Thumbs.db`,
  `*.ignored` netknuté), `zdroj_zbyva` a `zdroj_smazan` ve výsledku,
  zrušení importu bez zbylých přenositelných souborů; zahození zdroj
  nemění; ověřit scénáři „Vyprázdněná složka“, „Zbytky“, „Zahození
  importu ze zdroje“
- [x] 2.6 Snímek plánu (`plan_zdroj` v `import.json` při každém plánu)
  a porovnání v provedení (zmizelý → chyba, změněný → blokováno,
  přibylý → `po_planu`, bez snímku → `bez_planu`); ověřit testy
  scénářů „Zmizel po plánu“, „Přibyl po plánu“, „Změnil se po plánu“

## 3. Server (`fotoarchiv/app.py`)

- [x] 3.1 `GET /api/pretridit` (stream NDJSON: výpis, pak údaje složek)
  a `POST /api/import` se `zdroj`; ověřit testy v `tests/test_app.py`
  včetně odmítnutí `../x` a `_duplicity.ignored`
- [x] 3.2 Zámek zdroje `přetřídit/<složka>` v provedení (získání,
  heartbeat po souborech, uvolnění i při přerušení, 409 se jménem);
  ověřit testem scénáře „Dva importy téže složky“ a uvolnění po
  zavření streamu
- [x] 3.3 Vývojový režim: přehled a plán ze zdroje fungují, provedení
  403 a zdroj beze změny; ověřit testem

## 4. Klient (`fotoarchiv/static/app.js`)

- [x] 4.1 Odkaz „Přetřídit“ v seznamu akcí a stránka `#/pretridit`:
  tabulka složek s postupně doplňovanými údaji, zvýraznění vlastního
  rozpracovaného importu, klik založí/obnoví import s navrženým cílem
  a otevře přehled; ověřit ručně v prohlížeči nad kopií vzorku
  `přetřídit` v testovacím archivu
- [x] 4.2 Krok Soubory: volba „ze složky přetřídit“ se seznamem složek;
  přehled a plán bez nahrávání; výsledek se zbytky zdroje
  a „Rozpracované importy“ se zdrojem; ověřit ručně (scénáře „Zdroj
  místo nahrání“, „Zbytky zdroje ve výsledku“)
- [x] 4.3 Výsledek: přibylé po plánu zvlášť; odmítnutí `bez_planu`
  vrátí průvodce na krok Cíl

## 5. Dokumentace a ověření

- [x] 5.1 README: Archiv (`přetřídit` mění import), Import (zdroj
  přetřídit, přesun, `.ignored` ve zdroji, varianty se stejným jménem),
  Souběh (zámek zdroje); ověřit přečtením diffu
- [x] 5.2 Celé sady testů zelené: `.venv/bin/python -m pytest -q`
  a `node --test tests/js/*.test.mjs`
- [x] 5.3 Zkušební import jedné malé složky (`AMČR 8.11.2017`, 1 soubor)
  v produkčním režimu proti kopii archivu, ne proti produkci; ověřit,
  že akce vznikla, zdrojová složka zmizela a index se přegeneroval
