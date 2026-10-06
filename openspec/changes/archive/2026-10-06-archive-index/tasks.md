## 1. Sběr dat

- [x] 1.1 Přidat `tabulate` do `requirements.txt`; ověřit
      `.venv/bin/pip install -r requirements.txt` a import
- [x] 1.2 `fotoarchiv/index.py`: `collect(ws)` — akce podle
      `event_names`, stav z `list_events`, datum a název z JSONu nebo
      ze jména složky, místa akce a souborů, účastníci, osoby
      z `obliceje` s počty, přístroje, počty foto/video; ověřit testy
      v `tests/test_index.py` (akce s metadaty i bez)
- [x] 1.3 Autoři z výsledných `autori` (`model.resolve`) seřazení
      podle počtu souborů a jména, zkrácená jména; ověřit testem
      ze scénáře Řazení autorů a testem autora bez souboru

## 2. Výstupy

- [x] 2.1 `render_md`: hlavička s upozorněním a tabulka `fancy_grid`
      (Datum, Akce, Místa akce, Fotili, Foto, Video); ověřit testem
      řádku ze scénáře Řádek akce a absencí času generování
- [x] 2.2 `render_html` podle mockupu: karty, stav, náhled z
      `thumbs.py` jako `data:` URI, zástupný prvek bez JPEG, upozornění
      jen v komentáři, hledání bez diakritiky, filtry; ověřit testem
      (všechny karty v HTML, žádný externí odkaz) a ručně v prohlížeči
      s vypnutým JavaScriptem
- [x] 2.3 `write(ws)`: cíl podle režimu (kořen / `<work>/index/`),
      odkazy relativní / absolutní, zápis přes `xmp.write_atomic` jen
      při změně, chyba jako varování; ověřit testy (dvojí běh nezmění
      mtime, vývojový režim nesahá do archivu, `_metadata.xlsx`
      beze změny)

## 3. Napojení

- [x] 3.1 `app.py`: `write(ws)` po exportu, dokončení akce a provedení
      importu, varování v odpovědi pod `index`; kontrola nanečisto
      a uložení index nevolají; ověřit testy v `tests/test_app.py`
- [x] 3.2 `__main__.py exportovat`: jednou po smyčce, varování
      vypsat; ověřit testem a jedním ručním během nad `.work`
- [x] 3.3 Klient: varování o indexu ukázat u výsledku exportu
      a importu stejně jako ostatní varování; ověřit ručně

## 4. Dokumentace a ověření

- [x] 4.1 README (Výstupy): index HTML + MD místo CSV, okamžiky
      generování, `_metadata.xlsx` se nemění; AGENTS.md: index mezi
      generovanými výstupy
- [x] 4.2 Celé testy `.venv/bin/python -m pytest -q` a `node --test
      tests/js`; ruční kontrola vygenerovaného indexu nad reálným
      archivem ve vývojovém režimu
