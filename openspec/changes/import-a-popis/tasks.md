## 1. Server: popis importu a náhledy

- [x] 1.1 Uložení popisu k importu: `PUT /api/import/<id>/popis`
  (kontrola majitele, tvar `{akce, skupiny, soubory, pripojit}`,
  zápis do `import.json` pod `popis`, `aktivita`); `GET …/<id>` popis
  vrací; ověřit testem v `tests/test_import.py` (uložení, cizí import,
  neplatný tvar 400)
- [x] 1.2 `POST /api/import/<id>/skupiny`: výchozí rozdělení
  přenášených médií z posledního plánu (`group_plan`, shody
  s existujícími skupinami), uložení volby; plán bez pole `skupiny`;
  ověřit testy rozdělení podle podsložek, automaticky a „zařadit do
  skupiny“ a že změna volby plán nepočítá znovu
- [x] 1.3 `GET /api/import/<id>/nahled/<soubor>` z pracovního adresáře
  i ze zdroje `přetřídit` přes `thumbs.thumbnail`; ověřit testem
  (nahraný soubor, soubor zdroje, cizí import 404, zdroj beze změny)

## 2. Server: zápis popisu při provedení

- [x] 2.1 Nová akce: provedení založí `_metadata.json` z popisu (údaje
  akce, skupiny s přenesenými soubory, záznamy s technickými údaji);
  ověřit testem, že akce je *rozpracovaná*, blokovaný soubor nemá
  záznam a prázdná skupina nevznikne
- [x] 2.2 Akce s `_metadata.json`: nové skupiny s autory, `pripojit`,
  `akce.autori` jen při změně; stávající záznamy beze změny; ověřit
  testy scénářů Import do rozpracované akce a Zvolené připojení
- [x] 2.3 Akce bez `_metadata.json`: návrh skupin s autory a autory
  akce (`merge_proposal`, `apply_proposal`); ověřit testem scénáře
  Druhý import do neotevřené akce
- [x] 2.4 Selhání zápisu popisu: soubory zůstanou, výsledek je uvede
  bez skupiny a autorů; index po importu nové akce *rozpracovaná*
  (`archive-index`); ověřit testy

## 3. Klient: sdílený krok skupiny a autoři

- [x] 3.1 Kontext mřížky (zdroj náhledů, režim `import` bez ukládání
  akce) a funkce kroku skupiny a autoři: mřížka, nástroje skupin,
  autoři akce, řádky skupin s náhledy a autory; ověřit ručně
  v průvodci akce nad akcí bez `_metadata.json` ve `.work`
- [x] 3.2 Průvodce akce v pořadí úklid → údaje akce → skupiny
  a autoři (načtení při potvrzení úklidu, předvyplnění dat); ověřit
  scénáře Průvodce prvním otevřením a Autoři akce v průvodci ručně
  a `pytest -q`, `node --test tests/js/*.test.mjs`

## 4. Klient: import a popis

- [x] 4.1 Kroky soubory → přehled → cíl → plán → skupiny a autoři →
  výsledek; plán bez volby skupin, tlačítko provedení v kroku skupin;
  ověřit scénáře Kroky průvodce importem
- [x] 4.2 Cíl u nové akce s údaji akce a předvyplněním; ověřit scénáře
  Údaje nové akce v cíli
- [x] 4.3 Krok skupiny a autoři nad popisem importu: výchozí rozdělení
  s potvrzením při změně, připojení k existujícím skupinám, průběžné
  ukládání popisu, sladění s novým plánem (logiku sladění vytáhnout do
  modulu s testem v `tests/js/`), měkká povinnost autorů; ověřit
  scénáře Skupiny a autoři v importu a Volba skupin
- [x] 4.4 Vývojový režim: krok skupin ukáže, co by se zapsalo, bez
  provedení; ověřit ručně ve vývojovém režimu nad složkou v `přetřídit`

## 5. Dokončení

- [x] 5.1 Ruční průchod v produkčním režimu nad kopií archivu (ne nad
  produkčním): nová akce ze složky s podsložkami, import do akce
  s `_metadata.json`, import do akce bez něj a její průvodce; ověřit
  `_metadata.json` a návrh skupin na disku
- [x] 5.2 README, oddíly Tok práce a Import (pořadí kroků, krok
  skupiny a autoři, zápis u nové akce, návrh s autory); ověřit
  přečtením oproti delta specům
