## 1. Účty a hesla

- [x] 1.1 Nový modul `fotoarchiv/auth.py`: čtení `uzivatele.json`
      (znovu při změně mtime), `hesla.json` (zápis atomicky, práva
      0600), hash přes `werkzeug.security`, ověření hesla, příznak
      povinné změny, otisk hashe pro relace; ověřit testy
      `tests/test_auth.py` (hash místo hesla v souboru, odebraný
      uživatel, změna hesla mění otisk)
- [x] 1.2 Zdržování po opakovaných chybných pokusech (v paměti) a
      stejná chyba pro neexistující login; ověřit testem
- [x] 1.3 Příkaz `python -m fotoarchiv heslo LOGIN --work …`: vygeneruje
      jednorázové heslo, vypíše ho, uloží hash s příznakem změny;
      neznámý login odmítne; ověřit testem a jedním ručním během

## 2. Server

- [x] 2.1 Tajný klíč relací v pracovním adresáři (vytvořit při prvním
      spuštění, 0600); cookie `HttpOnly`, `SameSite=Lax`, `Secure`
      jen s `--https`
- [x] 2.2 Vstupní kontrola v `app.py` (`before_request`): bez relace
      stránky → přihlášení, API → 401; s povinnou změnou hesla jen
      změna hesla a odhlášení; neplatný otisk nebo odebraný uživatel
      → 401; ověřit testy v `tests/test_app.py`
- [x] 2.3 Endpointy přihlášení, odhlášení (uvolní zámek relace),
      změny hesla (min. 10 znaků, jiné než stávající, zneplatní
      ostatní relace) a `/api/ja` (login, jméno, admin, povinná změna);
      ověřit testy
- [x] 2.4 Přepínač `--bez-prihlaseni`; s `--zapis-do-archivu` server
      odmítne start; bez přihlášení je každý admin; ověřit testem
- [x] 2.5 Jméno držitele zámku z relace místo z požadavku (`lock.py`,
      `app.py`); ověřit testem, že poslané jméno se ignoruje

## 3. Admin

- [x] 3.1 Kontrola role na `/api/immich*` (včetně `sync`) → 403 pro
      běžného uživatele; ověřit testy v `tests/test_immich.py`
- [x] 3.2 Vynucené uvolnění zámku (endpoint jen pro admina); heartbeat
      a uložení původního držitele pak odmítnuty; ověřit testy
      v `tests/test_lock.py` a `tests/test_app.py`
- [x] 3.3 Kontakt pro Nominatim v `nominatim.json` (0600) a endpoint
      pro admina; `Geocoder` čte kontakt za běhu, bez kontaktu vypnuto;
      ověřit testy v `tests/test_geocode.py` (podvržený `fetch`,
      User-Agent po změně kontaktu bez restartu)
- [x] 3.4 `--kontakt` odstranit z CLI; je-li zadán a `nominatim.json`
      neexistuje, převzít hodnotu a vypsat upozornění; ověřit testem

## 4. Klient

- [x] 4.1 Přihlašovací stránka s upozorněním na HTTP; stránka změny
      hesla (i vynucená po jednorázovém heslu); odhlášení a jméno
      uživatele v záhlaví; ověřit v prohlížeči
- [x] 4.2 Při přihlášení nevyžadovat jméno do zámku; dotaz na jméno
      jen bez přihlášení; ověřit v prohlížeči v obou režimech
- [x] 4.3 Nastavení (Immich, kontakt pro Nominatim s předvyplněným
      e-mailem admina) a tlačítko vynuceného uvolnění zámku jen pro
      admina; upozornění původnímu držiteli; ověřit v prohlížeči
      dvěma účty
- [x] 4.4 Odpověď 401 kdekoli v klientu → přesměrování na přihlášení

## 5. Dokumentace

- [x] 5.1 README: přihlášení, `uzivatele.json`, příkaz `heslo`,
      `--bez-prihlaseni`, `--https`, nastavení kontaktu místo
      `--kontakt`; AGENTS.md: příkazy a invariant „hesla jen jako hash
      v `.work/hesla.json`“; ověřit
      `openspec validate add-login --strict` a celé testy
      (`pytest -q`, `node --test tests/js`)
