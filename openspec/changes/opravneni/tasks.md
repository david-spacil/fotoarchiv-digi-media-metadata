## 1. Účty, role a rozhodnutí o oprávnění

- [ ] 1.1 `auth.Users`: pole `role` (`admin` | `archivar` | žádná),
  `get` vrací `role`; `problems()` hlásí záznamy s klíčem `admin`
  a s neznámou `role`; chybné záznamy za běhu nedostanou přístup
  a jdou do logu. Ověřit testy v `tests/test_auth.py` (stará podoba,
  neznámá role, změna souboru za běhu bez restartu, ostatní loginy
  fungují dál).
- [ ] 1.2 `__main__`: start serveru i příkaz `heslo` při chybném
  `uzivatele.json` skončí s výpisem loginů a návodem. Ověřit testem
  (CLI s `"admin": true` → nenulový návratový kód, text obsahuje login
  a `"role": "admin"`).
- [ ] 1.3 Pomocná funkce rolí (admin, archivar s admin ⊃ archivář);
  `NOBODY` = admin; `/api/ja` (`me()`) vrací `role`, `admin`,
  `archivar`. Ověřit testem `/api/ja` pro každou roli.
- [ ] 1.4 `model.can_edit(user, doc)` podle design.md. Ověřit testy
  v `tests/test_model.py` včetně scénáře „Jméno bez diakritiky“
  a dokumentu None / bez `upravili`.

## 2. Vynucení na serveru

- [ ] 2.1 `zamek_ziskat` vrátí 403 `jen_cteni` uživateli bez oprávnění;
  `require_lock` po kontrole zámku ověří oprávnění znovu (403).
  Ověřit testy v `tests/test_app.py` nad `login_app`: cizí akce → 403
  na zámek; vlastní akce (jméno v `upravili`) → zámek; archivář →
  zámek u akce bez `upravili`; odebraná role během držení zámku →
  uložení 403.
- [ ] 2.2 `/api/akce` doplní u každé akce `upravit` přes
  `model.can_edit`. Ověřit testem výpisu pro běžného uživatele
  a archiváře.
- [ ] 2.3 `ADMIN_PREFIXES` jen Nastavení; `/api/pretridit`,
  `zamek_vynutit`, `import_create` se `zdroj` a `import_execute`
  u importu se zdrojem povolí adminovi a archiváři, jinak 403. Ověřit
  testy: archivář → přetřídit i uvolnění zámku projde, Nastavení 403;
  běžný uživatel → 403 a import nevznikne; upravit
  `test_force_release_admin_only`.
- [ ] 2.4 Pomocná `owner()` (jméno z relace, bez přihlášení
  z požadavku) nahradí všechna čtení `jmeno` u endpointů importů.
  Ověřit testem: přihlášený uživatel s podvrženým `jmeno` cizího
  importu dostane 404 u přehledu, plánu, provedení i zahození;
  stávající testy importu bez přihlášení dál procházejí.
- [ ] 2.5 `write_description` zapíše `upravili` (`model.touch`) jménem
  z `owner()` u nové akce i akce s `_metadata.json`. Ověřit testem:
  import do nové akce běžným uživatelem → `upravili` má jeho jméno
  a následný zámek projde.

## 3. Klient

- [ ] 3.1 Plocha akce s `upravit === false` nezískává zámek a ukáže
  `lockNotice` jen ke čtení s vysvětlením bez „Zkusit znovu“; 403
  `jen_cteni` ze zámku vede na totéž. Ověřit ručně nad `test-archiv`
  přihlášeným uživatelem bez role (cizí akce jen ke čtení, vlastní
  upravitelná).
- [ ] 3.2 Karta v seznamu akcí označí akci bez `upravit` štítkem „jen
  ke čtení“. Ověřit ručně v seznamu.
- [ ] 3.3 Průvodce importem nabídne jako stávající cíl jen akce
  s `upravit`; odkaz Přetřídit, volba zdroje v kroku Soubory
  a „Uvolnit zámek“ podle `me.archivar`, Nastavení podle `me.admin`.
  Ověřit ručně jako běžný uživatel, archivář a admin; `node --test
  tests/js/*.test.mjs` prochází.

## 4. Dokumentace a ověření

- [ ] 4.1 README (Přihlášení: pole `role` s příkladem, chyba u starého
  zápisu, kdo smí upravit akci, `přetřídit` a uvolnění zámku admin
  i archivář, vlastník importu z přihlášení; `upravili` i z importu;
  Docker: přepis `uzivatele.json` před nasazením) a AGENTS.md
  (invariant `upravili`, role). Ověřit přečtením diffu.
- [ ] 4.2 Celé testy: `.venv/bin/python -m pytest -q` a `node --test
  tests/js/*.test.mjs` procházejí.
