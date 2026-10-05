## 1. Model

- [ ] 1.1 Výsledné GPS z `souradnice_mist` v `model.resolve`
  a `static/inherit.js`; nové fixtury (bez GPS, s EXIF GPS, `null`);
  ověřit `pytest tests/test_model.py` a `node --test tests/js`
- [ ] 1.2 Počet míst bez souřadnic ve výpočtu chybějících údajů (JS);
  ověřit testem v `tests/js`

## 2. Server

- [ ] 2.1 `geocode.py`: normalizace dotazu, cache v `work/cache`,
  zámek a interval 1,1 s, User-Agent s kontaktem; ověřit unit testy
  s podvrženým HTTP (druhý dotaz z cache, interval mezi dotazy)
- [ ] 2.2 `GET /api/geokodovani` a volba `--kontakt` (bez ní 503);
  ověřit testy v `tests/test_app.py`
- [ ] 2.3 Jeden skutečný dotaz na Nominatim přes server (`Holštejn`)
  a opakování z cache; ověřit, že druhý dotaz neodešel (log)

## 3. Klient

- [ ] 3.1 Volba souřadnic u místa: kandidáti s popisem, předvýběr podle
  GPS akce, ruční souřadnice, „bez souřadnic“, atribuce OSM; uložení do
  `souradnice_mist`; ověřit v prohlížeči na akci s Vysočany
- [ ] 3.2 Formulář ukazuje GPS zděděné z místa odlišeně; ověřit
  v prohlížeči
- [ ] 3.3 Položka lišty „N míst bez souřadnic“ s výběrem souborů;
  ověřit v prohlížeči

## 4. Dokumentace

- [ ] 4.1 README (Datový model: `souradnice_mist`; Výstupy) a AGENTS.md
  (`--kontakt`, přístup ven); `openspec validate add-place-geocoding`
  projde
