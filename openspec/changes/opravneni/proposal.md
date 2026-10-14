## Why

Každý přihlášený uživatel dnes může upravit kteroukoli akci a importovat
ze složky `přetřídit`. Na sdíleném serveru to má být jinak (issue #31):
běžný uživatel smí měnit jen akce, na kterých sám pracoval (v praxi ty,
které naimportoval), celý archiv spravuje admin a nová role archivář.
Navíc server u rozpracovaných importů věří jménu z požadavku, takže
přihlášený uživatel může pracovat s cizím importem.

## What Changes

- **BREAKING** Role v `uzivatele.json` jako pole `"role": "admin"` nebo
  `"role": "archivar"` (bez role běžný uživatel) místo `"admin": true`.
  Starý zápis nebo neznámá role: server (i příkaz `heslo`) odmítne start
  s výpisem loginů a návodem; za běhu takový login neplatí a chyba jde
  do logu.
- Nová role **archivář**: upravuje všechny akce, smí `přetřídit`
  a vynucené uvolnění zámku. Adminovi zůstává navíc jen Nastavení
  serveru.
- **Oprávnění k úpravě akce**: admin a archivář všechny akce, běžný
  uživatel jen akce, v jejichž `upravili` je jeho jméno. Prohlížet
  smí všichni všechno. Server odmítne zámek akce (403) a bez zámku nejde
  uložit, dokončit, uklidit ani importovat do stávající akce.
- Klient otevře akci bez oprávnění jen ke čtení s vysvětlením, seznam
  ji označí a průvodce importem ji nenabídne jako cíl.
- Import zapíše do `upravili` jméno toho, kdo import provedl (nová akce
  i akce s `_metadata.json`), jinak by uživatel nemohl upravit akci,
  kterou sám naimportoval. **BREAKING** vůči invariantu „`upravili` jen
  z uložení a dokončení“.
- Stránka **Přetřídit** a import ze zdroje v `přetřídit` jen pro admina
  a archiváře (server 403, klient odkaz skryje).
- Vlastník rozpracovaného importu se bere z přihlášení, ne z požadavku
  (cizí import → 404 i s podvrženým jménem).
- Bez přihlášení (vývojový režim) zůstává každý admin.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `user-login`: pole `role` s kontrolou starého zápisu, role admin
  zúžená na Nastavení, nové požadavky na roli archivář a oprávnění
  k úpravě akce.
- `metadata-model`: `upravili` zapisuje i provedení importu.
- `photo-import`: vlastník importu z přihlášení; cílem importu jen
  akce, kterou uživatel smí upravit; zápis `upravili` při provedení.
- `unsorted-import`: přehled `přetřídit` a import ze zdroje jen admin
  a archivář.

## Impact

- `fotoarchiv/auth.py` (pole `role`, kontrola souboru),
  `fotoarchiv/__main__.py` (kontrola při startu a u `heslo`),
  `fotoarchiv/app.py` (vstupní kontrola, zámek, `require_lock`,
  vynucené uvolnění, `/api/akce`, `/api/ja`, `/api/pretridit`, import
  se zdrojem, jméno vlastníka importů, `write_description`),
  `fotoarchiv/model.py` (pomocná funkce oprávnění).
- `fotoarchiv/static/app.js`: plocha jen ke čtení, karta seznamu, cíl
  importu, odkaz Přetřídit, uvolnění zámku (`me.admin` → role).
- README (Přihlášení, `upravili`) a AGENTS.md (invariant `upravili`).
- Testy `tests/test_auth*.py`, `tests/test_app*.py`, import.
- Data: akce bez `upravili` (starší) smí měnit jen admin a archivář;
  správce musí před nasazením přepsat `uzivatele.json` na pole `role`
  (jinak server nenastartuje).
