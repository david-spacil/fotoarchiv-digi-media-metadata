## 0. Předpoklad

- [ ] 0.1 Rozhodnout otevřenou otázku XMP sidecaru (design.md) podle
  stavu změny generování XMP; ověřit zápisem rozhodnutí do design.md

## 1. Plán a provedení (server)

- [ ] 1.1 `cleanup.py`: konstanta `vyrazene.ignored`, `plan()` přijme
  označené názvy a naplánuje přesuny s kolizemi; ověřit testy
  v `tests/test_cleanup.py` (označený soubor, kolize, chybějící soubor,
  existující složka)
- [ ] 1.2 `_move()` zakládá i `vyrazene.ignored`; ověřit testem
  provedení s neexistující i existující složkou
- [ ] 1.3 `app.py`: endpointy úklidu čtou označení z uloženého
  `_metadata.json`; po provedení odstraní záznamy úspěšně přesunutých
  souborů s kontrolou verze; ověřit testy v `tests/test_app.py`
  (úspěch, blokovaný přesun ponechá záznam, vývojový režim 403)

## 2. Klient

- [ ] 2.1 Del a tlačítko přepínají `vyradit` u výběru (mřížka i lupa,
  ne ve formulářových polích a bez zámku); ověřit ručně v prohlížeči
- [ ] 2.2 Odlišení označených dlaždic v mřížce a pásu lupy
  (`style.css`); ověřit ručně
- [ ] 2.3 `inherit.js` `missing`: vynechat označené soubory; ověřit
  testem v `tests/js`
- [ ] 2.4 Lišta: počet k vyřazení a tlačítko úklidu; dialog plánu,
  provedení, výsledek a znovunačtení dokumentu; ověřit ručně ve
  vývojovém (jen plán) i produkčním režimu nad kopií akce

## 3. Dokumentace

- [ ] 3.1 README: Podsložky a RAW (`vyrazene.ignored`), Datový model
  (`vyradit`), Tok práce (Del, úklid z plochy); ověřit `openspec
  validate discard-files --strict`
