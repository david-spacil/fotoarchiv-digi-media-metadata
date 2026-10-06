## 1. Výpočet skupin (server)

- [x] 1.1 `importer.group_plan` pro režimy podslozky / jedna / auto /
  zadne / existujici včetně kořene výběru a RAWů bez skupiny; ověřit
  testy v `tests/test_import.py` (DOD 2015 se dvěma přístroji v jedné
  podsložce, výběr bez podsložek, prázdný kořen)
- [x] 1.2 Shody s existujícími skupinami (název bez diakritiky
  a velikosti písmen, stejný přístroj) bez automatického připojení,
  připojení jen podle `pripojit`, odlišení `gid`/názvu při kolizi;
  ověřit testy scénářů „Skupiny ve stávající akci“
- [x] 1.3 Uložení volby skupin do `import.json` (`set_target`)
  a vrácení v `overview`; ověřit testem návratu k importu

## 2. API

- [x] 2.1 `/api/import/<id>/plan` přijme `skupiny`, plán obsahuje
  `skupina` u operací a seznam nových a existujících skupin; ověřit
  testem v `tests/test_app.py`
- [x] 2.2 `GET /api/akce/<nazev>/skupiny` bez skenu (z `_metadata.json`,
  jinak z návrhu, jinak `null`); ověřit testem
- [x] 2.3 `/provest` po přenosu: akce s `_metadata.json` → `merge_scan`
  + skupiny jen pro přenesené → `ws.save`; výsledek s `skupiny.zapsano`;
  ověřit testy „Import do rozpracované akce“ a „Blokovaný soubor bez
  skupiny“ a konfliktu verze (soubory zůstanou, `zapsano: false`)
- [x] 2.4 `/provest` u akce bez `_metadata.json` → návrh
  v `.work/navrhy-skupin/<akce>.json`, druhý import ho sloučí;
  `_metadata.json` nevznikne; `GET …/skupiny` vrací skupiny návrhu;
  ověřit testem
- [x] 2.5 `GET /api/akce/<nazev>` u nové akce použije návrh (zbytek
  `propose_groups`) a `PUT …/metadata` s `version: null` návrh smaže;
  ověřit testy scénářů „Skupiny z importu v průvodci“

## 3. Klient

- [x] 3.1 Krok cíle: blok Skupiny s dostupnými režimy, předvolbou,
  názvem jedné skupiny a výběrem existující skupiny; předvyplnění po
  návratu; ověřit ručně v prohlížeči na `přetřídit/DOD 2015`
- [x] 3.2 Plán: sloupec skupiny, u nových skupin volba „nová /
  připojit ke skupině …“ se shodami nahoře (bez přepočtu plánu),
  `pripojit` se posílá s `/provest`; výsledek uvede
  nezapsané skupiny; ověřit ručně (vývojový režim plán, produkční
  na kopii archivu provedení)

## 4. Dokumentace a ověření

- [x] 4.1 README (Import, Tok práce) o volbě skupin a návrhu
  v `.work/`; ověřit diffem
- [x] 4.2 `pytest -q` a `node --test tests/js` zelené
