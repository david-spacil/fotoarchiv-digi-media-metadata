## 1. Server

- [x] 1.1 Odebrat endpoint `POST /api/akce/<akce>/export` z `app.py`;
      testy, které ho volají (`test_export_endpoint`,
      `test_overeno_se_nededi_a_neexportuje`), převést na dokončení
      (rozpracovaná akce ve vývojovém režimu: sidecary v
      `.work/xmp/`, index po dokončení, archiv beze změny) a přidat
      test, že `/export` vrací 404
- [x] 1.2 `/dokoncit`: zachovat existující `dokonceno`; vracet ho na
      `null` jen u akce, která ho před požadavkem neměla. Testy
      v `tests/test_app.py`: opakované dokončení zachová datum (datum
      prvního dokončení podvržené v `_metadata.json`), selhání zápisu
      sidecaru u dokončené akce nechá `dokonceno` i stav *hotovo*;
      ověřit, že oba testy na původním kódu selžou
- [x] 1.3 `pytest -q` celé sady zelené

## 2. Klient

- [x] 2.1 `static/app.js`: odebrat tlačítko Exportovat, `runExport`
      zjednodušit na dokončení, tooltip s cílem sidecarů
      (`exportTarget`) přesunout na Dokončit akci; u dokončené akce
      po selhání exportu ukázat „Dokončeno …“ spolu s chybou
- [x] 2.2 `node --test tests/js/*.test.mjs` zelené
- [x] 2.3 Ověřit v prohlížeči (vývojový režim, vygenerovaný archiv ve
      scratchi): lišta plochy bez Exportovat, dokončení rozpracované
      akce, úprava dokončené akce → „neexportované změny“ a aktivní
      tlačítko, opakované dokončení zachová „Dokončeno <datum>“

## 3. Dokumentace

- [x] 3.1 README: Tok práce (bod Dokončení akce bez tlačítka
      Exportovat, `dokonceno` = datum prvního dokončení, selhání
      u dokončené akce), Výstupy (kdy se zapisují sidecary), index
      (okamžiky generování); `grep -n Exportovat README.md AGENTS.md`
      najde už jen příkaz `exportovat`
