## 1. Sken

- [x] 1.1 `scan.py`: tag `GPSVersionID`, příznak `poloha_odebrana`
  v `parse_record`; ověřit testem nad záznamy exiftoolu (odebraná,
  platná, bez bloku GPS, WhatsApp) v `tests/test_scan.py`
- [x] 1.2 Verze záznamu cache skenu; záznam bez verze se načte znovu;
  ověřit testem, že stará cache vede k novému volání exiftoolu

## 2. Import

- [x] 2.1 `Importer.overview`: `poloha_odebrana` u souboru a seznam
  `odebrana_poloha`; ověřit testem přehledu s podvrženým exiftoolem
- [x] 2.2 Plán a provedení: fotky s odebranou polohou do `damaged`
  se stavem `bez_polohy`; nepřenesou se ani u nahrání, ani u
  `přetřídit` (zůstanou ve zdroji); `set_allowed` je nepovolí; ověřit
  testy plánu a provedení v obou režimech

## 3. Klient

- [ ] 3.1 Přehled: blok „Odebraná poloha“ s vysvětlením a seznamem,
  bez volby povolení a bez Smazat; plán a výsledek je uvedou jako
  samostatnou skupinu; ověřit ručně na `2026-09-17 Test.ignored`
  fotkách (vývojový režim, import ze souborů)

## 4. Dokumentace a ověření

- [x] 4.1 README, Import: pravidlo, důvod (Android, měření Pixel 8a
  2026-10-09) a co dělat (předat originál jinou cestou)
- [x] 4.2 `.venv/bin/python -m pytest -q` a
  `node --test tests/js/*.test.mjs` projdou
