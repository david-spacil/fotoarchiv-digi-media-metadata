# Proposal

## Why

Autoři celé akce (`akce.autori`) dělají víc škody než užitku (issue #43).
Průvodce importu se na ně ptá i při doimportu dalších fotek do stávající
akce a změna v tomto poli přepíše autory všem skupinám, které je dědí.
Fotky jedné akce navíc skoro vždy pocházejí od víc lidí. V produkci pole
k 19. 10. 2026 nepoužívá žádná z 11 akcí s `_metadata.json`; autoři jsou
jen u skupin (8 akcí) a souborů (4 akce).

Když se kvůli tomu zvedá verze schématu, odstraní se zároveň klíče,
které nic nečte: starší `osoby` (dnes se při uložení mažou)
a `datum_od`/`datum_do` u skupiny (pozůstatek prototypu, žádný požadavek
je nezavádí, v produkci nevyplněné).

## What Changes

- **BREAKING (data):** `_metadata.json` přejde na schéma
  `fotoarchiv-digi-media-metadata/2`. Proti `/1` vypadnou `akce.autori`,
  `osoby` na všech úrovních a `datum_od`/`datum_do` u skupiny. Klíč
  `sha256` u souboru a `osm` u souřadnic místa zůstávají.
- Server dokument `/1` při načtení převede v paměti na `/2` (vypuštěné
  klíče zahodí), takže každý zápis už ukládá `/2`. Vypuštěné klíče se
  nedědí a nejdou do sidecarů ani indexu, ani když v souboru zůstanou.
- Nový příkaz `python -m fotoarchiv migrovat`: bez `--zapis-do-archivu`
  vypíše, co by změnil; s ním převede všechny `_metadata.json` v archivu
  na `/2` a u akcí, jejichž export byl aktuální a převod sidecary
  nemění, přenese záznam o exportu na novou verzi.
- Průvodce prvním otevřením a průvodce importu přestanou nabízet pole
  „Autoři celé akce“. Autoři se zadávají jen u skupin a souborů,
  upozornění na skupinu bez autorů zůstává (import se po druhém
  potvrzení provede).
- Import přestane přenášet autory akce do `_metadata.json` i do návrhu
  skupin v pracovním adresáři.
- Formulář skupiny přestane nabízet pole datum od / datum do.
- README: datový model, průvodce, import a nasazení (spustit migraci).

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `metadata-model`: verze schématu `/2`, výčet vypuštěných klíčů,
  autoři jen u skupiny a souboru, převod starších dokumentů při
  načtení a příkaz `migrovat`.
- `metadata-workspace`: odebrán požadavek „Autoři akce v průvodci“,
  návrh skupin z importu bez autorů akce.
- `photo-import`: krok skupiny a autoři bez autorů celé akce, zápis
  popisu importu bez autorů akce.

## Impact

- `fotoarchiv/archive.py` (`SCHEMA`), `fotoarchiv/model.py` (vypuštěné
  klíče, převod, `clean`, `resolve`), `fotoarchiv/static/inherit.js`
  (stejné dědění), `fotoarchiv/__main__.py` (příkaz `migrovat`).
- `fotoarchiv/app.py` (návrh a zápis popisu importu, detail importu),
  `fotoarchiv/importer.py` (`merge_proposal`), `fotoarchiv/static/app.js`
  (`FIELDS`, krok autorů průvodce, krok skupin importu, souhrn importu),
  `fotoarchiv/static/importdesc.js` (výchozí popis importu).
- Testy: `tests/test_model.py`, `test_app.py`, `test_import.py`,
  `test_xmp.py`, `tests/js/*.test.mjs`, fixtury
  `tests/fixtures/inheritance/`.
- Provoz: po nasazení jednorázově spustit `migrovat
  --zapis-do-archivu` při zastaveném serveru (README, Docker).
