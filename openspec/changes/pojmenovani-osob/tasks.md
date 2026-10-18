# Tasks

## 1. Klient Immiche: zápis a oprávnění klíče

- [x] 1.1 `immich.py`: metody klienta `api_key_permissions`
  (`GET /api/api-keys/me`), `update_people` (`PUT /api/people`),
  `merge_people` (`POST /api/people/merge`), `albums`/`album`/
  `create_album`/`add_album_assets`/`remove_album_assets`,
  `search_album` (`albumIds`, `withPeople`, `withExif`, stránkování),
  `thumbnail` (`size=preview`, binární odpověď), `libraries`
  (`GET /api/libraries`), `scan_library` (`POST …/{id}/scan`), `queue`
  (`GET /api/queues/{name}`). `FakeImmich`
  v `tests/test_immich.py` rozšířit o tytéž endpointy a záznam zápisů.
  Ověření: unit testy na tvar požadavků (metoda, cesta, tělo, cíl
  sloučení = první id).
- [x] 1.2 `test_connection`: krok oprávnění porovná `permissions` se
  seznamem pro alba, sken, fronty a nástroj (`all` = vše) a chybějící
  vrátí jako varování. Varuje i při 403 na `GET /api/libraries` (klíč
  bez role admin) a při nevybrané knihovně. Ověření: testy „klíč jen
  pro čtení“ (varování se seznamem, test projde), „klíč s `all`“
  a „klíč bez role admin“. Stránka nastavení (`app.js`) varování
  zobrazí. README, Aplikace → Immich: potřebná oprávnění klíče
  a varování.
- [x] 1.3 Výběr knihovny v nastavení: `GET /api/immich/knihovny`
  (admin) vrátí knihovny Immiche, uložení přidá `knihovna` do
  `immich.json` (`Settings`). Ověření: testy uložení a načtení id,
  scénář Výběr knihovny; stránka nastavení výběr ukáže.

## 2. Alba a stav akcí v Immichi

- [x] 2.1 Projít s uživatelem provedení alb (design.md, „Fotky akce
  vymezuje album“ a Open Questions) a případné změny zapsat do
  design.md a delty `immich-people` jako samostatný commit
  v `openspec/`. Ověření: uživatel provedení odsouhlasí.
- [x] 2.2 Stav akcí ve `.work/immich-alba.json`
  (`{akce: {album, stav, cas, chyba?}}`), atomický zápis pod zámkem
  v paměti, čtení pro výpis akcí bez Immiche. Ověření: unit testy
  zápisu a načtení, poškozený nebo chybějící soubor = prázdný stav.
- [x] 2.3 Udržení alba (společné pro hlídač i synchronizaci):
  assety akce přes `originalPath` + `file_key` bez označených
  k vyřazení, album dohledat podle vazby nebo názvu, jinak založit,
  doplnit chybějící a odebrat cizí assety, zjistit rozpoznání
  (`thumbhash` u všech fotek + prázdné fronty `faceDetection`
  a `facialRecognition`) a zapsat stav. Pravidelná synchronizace to
  udělá pro každou dokončenou akci, bez skenu. Ověření: testy
  v `tests/test_immich.py` na scénáře Album akce (Immich fotky nezná,
  album smazané, cizí akce se stejným podřetězcem cesty, klíč bez práv
  k albům, nikdy nemaže album ani asset, restart serveru) a Stav akce
  v Immichi (rozpoznání doběhlo, fronta neprázdná, asset bez
  `thumbhash`, chyba spojení stav nemění).
- [x] 2.4 Hlídač po dokončení: `akce_finish` po úspěšném zveřejnění
  spustí na pozadí sken vybrané knihovny a hlídání akce
  (`HLIDAC_INTERVAL`, `HLIDAC_LIMIT`, nejvýš jeden na akci, opakované
  dokončení ho pustí znovu). Hotovo podle všech souborů alba, nebo
  podle prázdné fronty `library` a nezměněného počtu nalezených. Po
  rozpoznání `Sync.trigger()`, po vypršení stav `nenalezeno`. Ve
  vývojovém režimu bez skenu. Odpověď dokončení na Immich nečeká.
  Ověření: testy s `FakeImmich` a zkráceným intervalem na scénáře
  Dokončení akce, Dokončení nečeká na Immich, Vývojový režim, Immich
  fotky nenašel; test, že chyba Immiche nemění výsledek dokončení.
- [x] 2.5 `GET /api/akce/<nazev>/immich` (každý přihlášený, jen ze
  `.work/`), stav na kartě akce (`app.js`, data z výpisu akcí) a na
  ploše akce s obnovováním během `nacitani` a `rozpoznavani`.
  Ověření: test endpointu (bez dotazu na `FakeImmich`), prohlížeč nad
  testovacím archivem s podvrženým stavem ve `.work/`: karta i plocha,
  běžný uživatel stav vidí, plocha přejde na další stav bez obnovení
  stránky.
  README, Aplikace → Immich: alba akcí, sken po dokončení a stav akce.

## 3. Osoby akce v synchronizaci

- [x] 3.1 Synchronizace pro akce s albem spočítá pojmenované a neskryté
  nepojmenované osoby s obličejem v albu a uloží je do
  `.work/immich-osoby.json`. Při chybě dotazu nechá předchozí stav.
  Ověření: testy na scénáře Osoby akce (4 z 6, skrytá se nepočítá,
  po pojmenování 5 z 6, chyba zachová stav).

## 4. Osoby v kompletnosti akce

- [x] 4.1 `archive.py`/`model.py`: hotovost dostane `osoby`
  `[pojmenovane, celkem]` z `.work/immich-osoby.json` (jen když akce
  má zjištění a stav `rozpoznano`), `incomplete` vrátí i `osoby`
  při nepojmenovaných.
  Výpis akcí se Immiche neptá. Ověření: testy v `tests/test_archive.py`
  (nebo `tests/test_model.py`, podle místa výpočtu) na scénáře Stav
  akce a Hotovost akce s osobami.
- [x] 4.2 Karta akce (`app.js`): osoby v hotovosti (`osoby 4/6`), odkaz
  na nástroj u archiváře a admina při nepojmenovaných, štítek
  „nekompletní“ i kvůli osobám. Navigátor: ikona osoby s počtem na
  řádku Akce, klik otevře nástroj (ostatním jen údaj). Ověření:
  prohlížeč nad testovacím archivem s podvrženými počty ve `.work/`.
  README, Aplikace → seznam akcí a plocha: osoby v kompletnosti.

## 5. Server nástroje pojmenování

- [x] 5.1 Nový modul `fotoarchiv/naming.py` (bez Flasku): ze stránky
  `search_album` sestaví osoby k pojmenování (nepojmenované, neskryté,
  bez odložených, pořadí podle počtu obličejů v akci) a ke každé až
  3 výřezy z různých assetů s největším obličejem. Připojí metadata
  z Immiche a z `_metadata.json` po zdědění (`model`) přes `file_key`.
  Ověření: `tests/test_naming.py` na scénáře Osoby k pojmenování,
  Náhledy obličeje (3 z 5, 1 z 1) a Metadata zdrojové fotky (spárovaná
  i nespárovaná fotka).
- [x] 5.2 Odložené osoby: `.work/pojmenovani.json`
  `{login: {akce: [id]}}`, atomický zápis, vyřazení id, které mezitím
  dostalo jméno nebo bylo skryto, nové kolo vymaže odložení. Ověření:
  testy na scénáře Odložení osoby (znovuotevření, konec kola, jiný
  uživatel).
- [x] 5.3 Endpointy v `app.py`: `GET /api/akce/<nazev>/osoby`,
  `GET …/osoby/nahled/<asset_id>` (404 mimo album), `POST
  …/osoby/<person_id>` (pojmenovat / sloučit / nevím / skrýt),
  `POST …/osoby/kolo` (nové kolo), `POST …/osoby/hotovo` (při změně
  `Sync.trigger()`). Role archivář a výš (403 jinak), bez zámku, bez
  zápisu do `_metadata.json`, klíč v žádné odpovědi. Chyba Immiche =
  502 s chybou, nic se neodloží. Po akci přepočítat počty osob akce.
  Ověření: testy v `tests/test_app.py` s `FakeImmich` na scénáře
  Oprávnění nástroje, Pojmenování osoby (zapíše se kanonický tvar),
  Sloučení (cíl = existující osoba) i odmítnuté sloučení, Skrytí,
  Chyba Immiche, Převzetí jmen po zavření a na to, že `_metadata.json`
  zůstane beze změny.
  README, Aplikace → Immich: nástroj pojmenování osob.

## 6. Klient nástroje

- [x] 6.1 Nový modul `fotoarchiv/static/naming.js`: čistá funkce výřezu
  (obdélník + rozměr zmenšeniny → výřez) a pořadí kroků kola. Ověření:
  `tests/js/naming.test.mjs` (`node --test tests/js/*.test.mjs`,
  zkontrolovat počet testů ve výstupu).
- [x] 6.2 Překryv nad plochou akce (`<dialog>`, `::backdrop`
  s `backdrop-filter: blur`): výřezy s metadaty, pole jména
  s našeptáváním `/api/jmena` a kontrolou `/api/jmena/kontrola`
  (návrh tvaru, potvrzení převodu), nabídka sloučení s náhledem
  existující osoby, tlačítka Nevím a Skrýt, počítadlo, konec kola
  s nabídkou projít odložené, chyba Immiche. Otevření z plochy,
  z navigátoru a ze seznamu (`#osoby` v URL plochy), zavření zpět
  na plochu. Ověření: headless prohlížeč nad testovacím archivem
  s podvrženým Immichem: screenshot rozmazaného pozadí, průchod
  pojmenovat → sloučit → nevím → skrýt → konec kola, běžný uživatel
  odkazy nevidí.

## 7. Dokumentace a ruční ověření

- [x] 7.1 AGENTS.md: invariant „do Immiche zapisuje jen nástroj
  pojmenování (osoby), dokončení a synchronizace (alba, sken knihovny
  jen při dokončení)“, soubory nástroje ve
  `.work/` a role archivář pro nástroj. README, Datový model: osoby
  v kompletnosti a soubory ve `.work/`. Ověření: diff obou souborů
  odpovídá specifikaci.
- [ ] 7.2 Ruční zkouška uživatele proti skutečnému Immichi: test
  připojení s rozšířeným klíčem, výběr knihovny, dokončení akce →
  stav na ploše → založené album → „obličeje rozpoznány“ (ověřit, že
  se neohlásí předčasně, a doladit `HLIDAC_*`), průchod
  nástrojem na mobilu i notebooku, převzetí jména do `obliceje` po
  zavření. Ověření: hlášení uživatele.
