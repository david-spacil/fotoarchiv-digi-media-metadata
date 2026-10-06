## 1. Plán a provedení (server)

- [ ] 1.1 `cleanup.py`: konstanta `k_odstraneni.ignored`, `plan()` přijme
  označené názvy a naplánuje přesuny s kolizemi; ověřit testy
  v `tests/test_cleanup.py` (označený soubor, kolize, chybějící soubor,
  existující složka)
- [ ] 1.2 `_move()` zakládá i `k_odstraneni.ignored`; ověřit testem
  provedení s neexistující i existující složkou
- [ ] 1.3 `app.py`: endpointy úklidu čtou označení z uloženého
  `_metadata.json`; po provedení odstraní záznamy úspěšně přesunutých
  souborů s kontrolou verze; ověřit testy v `tests/test_app.py`
  (úspěch, blokovaný přesun ponechá záznam, vývojový režim 403)
- [ ] 1.4 Sidecar vyřazeného souboru: zapsat `xmp.sidecar()` do
  `k_odstraneni.ignored/`, sidecar v kořeni odstranit; kolize i s `.xmp`
  v cíli; ověřit testy (zápis, existující sidecar v kořeni, kolize
  `.xmp`, selhaný zápis ponechá soubor i záznam)

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

- [ ] 3.1 README: Podsložky a RAW (`k_odstraneni.ignored`), Datový model
  (`vyradit`), Tok práce (Del, úklid z plochy); ověřit `openspec
  validate discard-files --strict`
