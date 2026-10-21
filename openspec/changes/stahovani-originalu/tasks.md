## 1. Server: originál a ZIP

- [ ] 1.1 Endpoint originálu s `?stahnout=1` vrací přílohu
  (`Content-Disposition: attachment`, název z disku, UTF-8); bez
  parametru zůstává inline pro lupu. Ověřit testem na dummy akci:
  hlavička, obsah shodný s originálem, podsložka a `..` → 404.
- [ ] 1.2 Pomocný modul pro streamovaný ZIP (`ZIP_STORED`, zip64,
  generátor po blocích, přeskočení zmizelého souboru). Ověřit
  testem: ZIP z generátoru se otevře `zipfile`, obsah médií sedí
  bajt po bajtu, soubor smazaný po startu chybí a ZIP je platný.
- [ ] 1.3 `GET /api/akce/<nazev>/zip`: média z kořene bez vyřazených,
  `_metadata.json` a sidecary z `xmp.sidecar()` (bez obličejů),
  párování názvů po NFC, název ZIPu bez `.ignored`. Ověřit testy:
  vyřazený soubor a `RAW.ignored` chybí, sidecar nese neexportovaný
  popis, akce bez JSONu dá jen média, skrytá akce jde stáhnout,
  archiv i `.work` se nezmění, nepřihlášený požadavek je odmítnut.
- [ ] 1.4 `POST /api/akce/<nazev>/zip` se seznamem `soubory`
  (formulářová data): přesně vybraná média včetně vyřazených, kontrola
  všech názvů před prvním bajtem, název `<akce> (N souborů).zip`.
  Ověřit testy: výběr s vyřazeným, neplatný název → 404 bez ZIPu,
  prázdný výběr → 400, stažení bez zámku u akce zamčené jiným.

## 2. Klient

- [ ] 2.1 Ikona `stahnout` v `icons.js` a odkaz na kartě akce
  v přehledu (`download`, `aria-label`, `title` „Stáhnout akci (ZIP)“,
  klik neotevře plochu), styly v `style.css`. Ověřit ručně v aplikaci
  na dummy archivu: ikona v dlaždicích i řádcích, ve světlém i tmavém
  vzhledu, stáhne se `<akce>.zip`.
- [ ] 2.2 Tlačítko „Stáhnout (N)“ v nástrojích výběru na ploše:
  jeden soubor přes `?stahnout=1`, víc přes neviditelný `<form>` POST;
  dostupné i jen pro čtení. Ověřit ručně: 1 soubor dá originál,
  3 soubory ZIP se 3 médii, bez zámku tlačítko funguje.
- [ ] 2.3 Dokumentace: `docs/navod/seznam-akci.md`,
  `docs/navod/pracovni-plocha.md` a oddíl Aplikace v `README.md`
  (co ZIP obsahuje, sidecary z aktuálního JSONu). Ověřit, že odkazy
  v `docs/README.md` vedou na existující soubory.

## 3. Integrace

- [ ] 3.1 Celé testy `pytest -q` a `node --test tests/js/*.test.mjs`
  projdou; ruční stažení akce s videem přes `python -m fotoarchiv`
  na dummy archivu, ZIP se rozbalí systémovým nástrojem.

## Workflow follow-up

- Po revizi a sloučení změnu archivovat (`/opsx:archive`) a ověřit
  synchronizaci do `openspec/specs/event-download`.
