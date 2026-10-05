## 1. Generátor

- [ ] 1.1 `fotoarchiv/xmp.py`: `sidecar(doc, akce, soubor)` vrátí text
  XMP podle specifikace (pole, tagy, `/` → `-`, prázdná pole vynechat);
  ověřit testy v `tests/test_xmp.py` (zděděné autory, GPS z místa, tag
  akce, escapování `&<"`, bajtová shoda dvou běhů)
- [ ] 1.2 Datum se zónou Europe/Prague a GPS ve formátu `DDD,MM.mmmmmmK`;
  ověřit testy (letní, zimní, podzimní dvojí hodina, jen datum, jižní
  a západní souřadnice)
- [ ] 1.3 `export(ws, akce)`: soubory se záznamem, v kořeni,
  neoznačené k vyřazení; zápis jen změněných, atomicky, cesta podle
  režimu; vrátí počty a chyby; ověřit testy (vývojový režim nesahá do
  archivu, druhý běh 0 zapsaných, změna jednoho popisu = 1 zapsaný)
- [ ] 1.4 Režim nanečisto (vrátí počet chybějících/neaktuálních, nic
  nezapíše) a záznam o exportu ve `work/export/<akce>.json` jen po
  exportu bez chyb; ověřit testy (ručně změněný sidecar, export
  s chybou záznam nemění, archiv beze změny)
- [ ] 1.5 Ověřit jeden vygenerovaný sidecar `exiftool -X` nad vzorovou
  fotkou (čte popis, datum se zónou, GPS, tagy)

## 2. Server a CLI

- [ ] 2.1 `archive.py`: počítání souborů akce bez `.xmp`; seznam akcí
  vrací u *hotovo* příznak „změněno po exportu“ z porovnání verzí;
  ověřit testy v `tests/test_archive.py`
- [ ] 2.2 `app.py`: `POST …/export` a `…/dokoncit` se zámkem;
  dokončení uloží `dokonceno`, exportuje a při chybě ho vrátí; detail
  akce vrací výsledek kontroly nanečisto a verzi záznamu o exportu;
  ověřit testy v `tests/test_app.py` (bez zámku 409/403, selhání → bez
  `dokonceno`)
- [ ] 2.3 `__main__.py`: podpříkaz `exportovat [AKCE]` s
  `--zapis-do-archivu`; ověřit testem a jedním ručním během nad kopií
  akce
- [ ] 2.4 `requirements.txt`: `tzdata; sys_platform == "win32"`; ověřit
  `pip install -r requirements.txt` na Linuxu beze změny

## 3. Klient

- [ ] 3.1 Tlačítka Dokončit akci (kontrola `missing()`, potvrzení,
  export, stav *hotovo*) a Exportovat (počty, hláška o vývojovém
  režimu) místo upozornění prototypu; ověřit ručně ve vývojovém režimu
- [ ] 3.2 Stav exportu u tlačítka (počet neaktuálních při otevření,
  „neexportované změny“ po uložení s jinou verzí) a poznámka „změněno
  po exportu“ v seznamu akcí; ověřit ručně: export → úprava popisu →
  hláška → export → hláška zmizí

## 4. Dokumentace

- [ ] 4.1 README (Výstupy: tag akce, formát data a GPS; Ukládání
  a export: porovnání s diskem místo `sha256`, CLI; Tok práce) a
  `AGENTS.md` (Příkazy); ověřit `openspec validate add-xmp-export
  --strict`
