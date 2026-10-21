## 1. Koš v archivu (server, bez UI)

- [x] 1.1 Nový modul koše: ID (`YYYYMMDDTHHMMSS-xxxx`), zápis
  `_smazano.json` (atomicky, do složky akce před přesunem), přesun do
  `_kos.ignored/<ID>/` přes `Workspace.event_dir` bez přepsání, úklid
  záznamu při selhání přesunu, výpis koše (záznam / neznámá složka).
  Ověřit testy v novém `tests/test_trash.py` na dummy archivu: akce
  s příponou i bez, dvojí smazání téhož názvu, selhání přesunu nechá
  akci beze změny, kolize přípony se odmítne.
- [x] 1.2 Obnovení pod `slozka` ze záznamu, odmítnutí při obsazeném
  názvu (s příponou i bez), odstranění záznamu. Ověřit testy:
  obnovená skrytá akce má příponu, obsazený název nic nepřesune.
- [x] 1.3 Ověřit, že `_kos.ignored` se neobjeví v `list_events`, indexu,
  návrzích jmen, kontrole konzistence ani synchronizaci obličejů
  (testy s akcí v koši, jejíž `_metadata.json` obsahuje unikátní jméno).
- [x] 1.4 Dokumentace: `docs/navrh/archiv.md` (koš, záznam, lhůta)
  a AGENTS.md (invariant: jediné trvalé mazání je vysypání koše).
  Ověřit, že odkazy v `docs/README.md` vedou na existující soubory.

## 2. Vysypání a úklid

- [x] 2.1 Vysypání: jen složky se záznamem starším 7 dní, `rmtree` jen
  pro přímé potomky koše, záznam se maže poslední, log. Ověřit testy
  s podvrženým časem: 6 dní zůstane, 8 dní zmizí, složka bez záznamu
  zůstane, symlink ven se nesmaže.
- [x] 2.2 Stav `.work` putuje se záznamem: smazání vyjme položky
  `immich-alba.json`, `immich-osoby.json`, `pojmenovani.json` a záznam
  exportu do `_smazano.json` (cache kontroly a návrh importu zahodí),
  obnovení je vrátí; vysypání smaže náhledy souborů z cache. Ověřit
  testy: nová akce stejného názvu po smazání nemá vazbu na album,
  obnovení vrátí stav, vysypání smaže náhledy.
- [x] 2.3 `albums.py`: fronta alb ke smazání `.work/kos-alba.json`,
  smazání alba podle ID přes klient Immiche (úspěch nebo 404 odebere
  z fronty); test připojení hlásí `album.delete`. Ověřit testy proti `FakeImmich` (úspěch, chyba
  Immiche ponechá vazbu a další běh smaže album, synchronizace album
  akce v koši nemění).
- [x] 2.4 Denní vlákno v serveru (start + 24 h, nic ve vývojovém režimu)
  a příkaz `python -m fotoarchiv vysypat` (bez `--zapis-do-archivu`
  jen výpis). Ověřit testy příkazu a `docs/provoz/prikazy.md`
  + blok Příkazy v AGENTS.md.
- [x] 2.5 Přegenerování indexu po smazání, obnovení a vysypání. Ověřit
  testem, že index po smazání akci neobsahuje a po obnovení ano.

## 3. API a oprávnění

- [x] 3.1 Endpoint smazání akce: jen admin (403 jinak), opsaný název
  a neprázdný důvod, jméno z relace, zámek akce (cizí platný zámek
  odmítne), log; ve vývojovém režimu vrátí plán bez zápisu. Ověřit
  testy v `tests/test_app.py` (archivář 403, špatný název, bez důvodu,
  jméno v požadavku ignorováno, cizí zámek, vývojový režim nezmění
  archiv).
- [x] 3.2 Endpointy koše (`/api/kos`: výpis, obnovení) v
  `ADMIN_PREFIXES`. Ověřit testy (archivář 403, výpis se zbývajícími
  dny, obnovení obsazeného názvu 409).
- [x] 3.3 Import s cílem ve smazané akci selže při provedení jako
  u neexistující akce. Ověřit testem v `tests/test_import.py`.

## 4. Klient

- [x] 4.1 Plocha akce (i průvodce prvním otevřením — nezpracovanou
  akci admin smaže bez průchodu průvodcem): tlačítko „Smazat akci…“
  jen pro admina, dialog
  s opsáním názvu a důvodem (potvrzení aktivní až při shodě), po
  smazání návrat na seznam; ve vývojovém režimu zobrazení plánu. Čistou
  logiku shody názvu do malého modulu s testem v `tests/js/`; ověřit
  `node --test tests/js/*.test.mjs`.
- [x] 4.2 Stránka Koš (odkaz ze seznamu jen pro admina): název, kdo,
  kdy, důvod, počet souborů, datum trvalého smazání, Obnovit; neznámé
  složky bez tlačítka. Ověřit ručně na dummy archivu v produkčním
  režimu (smazat, zobrazit v koši, obnovit).
- [x] 4.3 Návod `docs/navod/smazani-akce.md` a odkaz z
  `docs/README.md`. Ověřit, že popsaný postup odpovídá UI z 4.1–4.2.

## 5. Integrace

- [x] 5.1 Celé testy: `.venv/bin/python -m pytest -q`
  a `node --test tests/js/*.test.mjs` zelené.
- [x] 5.2 Ověřit proti testovacímu Immichi (ne produkčnímu, s dummy
  fotkami): dokončená akce smazaná do koše → sken → obnovení → sken;
  zapsat do `docs/navrh/immich.md`, zda se assety vrátily i s obličeji.

## 6. Sken knihovny po smazání a obnovení

- [x] 6.1 `albums.Hlidac`: `zastavit(akce)` (ukončí běžícího hlídače)
  a `skenovat()` (jen sken na pozadí, produkce, vybraná knihovna).
  `akce_smazat` u dokončené akce zastaví hlídače a spustí sken,
  `kos_obnovit` u dokončené akce spustí hlídače. Ověřit testy
  v `tests/test_immich.py` (sken po smazání dokončené, bez skenu
  u nedokončené, sken po obnovení, nedostupný Immich).
- [x] 6.2 Dokumentace: `docs/navrh/immich.md`, `docs/navrh/archiv.md`,
  návod a invariant v AGENTS.md (sken i po smazání a obnovení).

## Workflow follow-up

- Archivovat změnu po review a sloučení.
