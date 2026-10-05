## 1. Kořen metadat a režim

- [x] 1.1 `Workspace` dostane kořen metadat (archiv / `work/metadata`);
  `metadata_path`, `metadata_files` a `list_events` ho používají;
  ověřit testy v `tests/test_archive.py` pro oba režimy
- [x] 1.2 Přepínač `--zapis-do-archivu` v `__main__.py`, výpis režimu při
  startu; ověřit spuštěním obou režimů nad testovacím archivem
- [x] 1.3 Příkaz `prevzit` (kopie z `.work`, `xb`, výpis převzatých
  a přeskočených); ověřit testem s akcí, která metadata v archivu už má

## 2. Zámek

- [x] 2.1 `lock.py`: získání, heartbeat, uvolnění, opuštění po 5 min
  (injektovatelné hodiny), jedna akce na relaci; ověřit unit testy
  včetně „ztraceného zámku“
- [x] 2.2 API zámku v `app.py` (POST/PUT/DELETE + POST uvolnit pro
  beacon); ověřit testy v `tests/test_app.py`
- [x] 2.3 `PUT …/metadata` vyžaduje zámek (423 bez něj), kontrola verze
  beze změny; ověřit testem uložení bez zámku a s cizím zámkem

## 3. Provedení úklidu

- [x] 3.1 `cleanup.execute` podle designu (kontrola cíle před
  `rename`, `mkdir RAW.ignored`, mazání jen prázdné složky
  s `Thumbs.db`, stavy `hotovo` / `blokovano` / `chyba`); ověřit testy
  scénářů ze specu včetně kolize vzniklé po náhledu a chyby oprávnění
- [x] 3.2 `POST …/uklid/provest` (jen produkční režim, vyžaduje
  zámek); ověřit testem, že ve vývojovém režimu vrátí chybu a archiv
  se nezmění

## 4. Klient

- [x] 4.1 Dialog jména s našeptáváním, uložení do `localStorage`;
  ověřit ručně v prohlížeči
- [x] 4.2 Relace v `sessionStorage`, získání zámku při otevření akce,
  heartbeat 60 s, uvolnění při zavření akce a `pagehide`; ověřit ve
  dvou prohlížečích
- [x] 4.3 Režim jen pro čtení (upozornění s držitelem, zakázané úpravy,
  přechod při ztrátě zámku); ověřit ve dvou prohlížečích
- [x] 4.4 Krok úklidu: v produkčním režimu tlačítko provést a výsledek
  operací, pak sken kořene; ve vývojovém beze změny; ověřit na kopii
  akce s podsložkami a RAWy

## 5. Ověření na serveru a dokumentace

- [x] 5.1 Na Debianu nad skutečným připojením archivu (SMB/NFS) ověřit
  atomické uložení, přejmenování složky, vlastníka a práva nových
  souborů — na testovací akci mimo ostrá data
- [x] 5.2 README (Stav, Souběh — zámek v serveru místo
  `_metadata.lock`, Ukládání) a AGENTS.md (Stav, příkazy, „jeden
  proces“); ověřit, že `openspec validate write-to-archive` projde
- [x] 5.3 `pytest -q` a `node --test tests/js` projdou
