# Tasks

## 1. Klient Immiche: zápis a oprávnění klíče

- [ ] 1.1 `immich.py`: metody klienta `api_key_permissions`
  (`GET /api/api-keys/me`), `update_people` (`PUT /api/people`),
  `merge_people` (`POST /api/people/merge`), `albums`/`album`/
  `create_album`/`add_album_assets`/`remove_album_assets`,
  `search_album` (`albumIds`, `withPeople`, `withExif`, stránkování),
  `thumbnail` (`size=preview`, binární odpověď). `FakeImmich`
  v `tests/test_immich.py` rozšířit o tytéž endpointy a záznam zápisů.
  Ověření: unit testy na tvar požadavků (metoda, cesta, tělo, cíl
  sloučení = první id).
- [ ] 1.2 `test_connection`: krok oprávnění porovná `permissions` se
  seznamem pro alba a nástroj (`all` = vše) a chybějící vrátí jako
  varování. Ověření: testy „klíč jen pro čtení“ (varování se seznamem,
  test projde) a „klíč s `all`“. Stránka nastavení (`app.js`) varování
  zobrazí. README, Aplikace → Immich: potřebná oprávnění klíče
  a varování.

## 2. Alba akcí v synchronizaci

- [ ] 2.1 Projít s uživatelem provedení alb (design.md, „Fotky akce
  vymezuje album“ a Open Questions) a případné změny zapsat do
  design.md a delty `immich-people` jako samostatný commit
  v `openspec/`. Ověření: uživatel provedení odsouhlasí.
- [ ] 2.2 Synchronizace: pro dokončené akce dohledat assety
  (`originalPath` + `file_key`), album založit nebo dohledat podle
  názvu, doplnit chybějící a odebrat cizí assety. Vazba ve
  `.work/immich-alba.json` (atomický zápis). Nedokončenou akci
  přeskočit, při chybějícím oprávnění zapsat do stavu běhu. Ověření:
  testy v `tests/test_immich.py` na scénáře Alba akce (nová akce, Immich
  fotky nezná, album smazané, cizí akce se stejným podřetězcem cesty,
  klíč bez práv k albům, synchronizace nikdy nemaže album ani asset).
  README, Aplikace → Immich: alba akcí.

## 3. Osoby akce v synchronizaci

- [ ] 3.1 Synchronizace pro akce s albem spočítá pojmenované a neskryté
  nepojmenované osoby s obličejem v albu a uloží je do
  `.work/immich-osoby.json`. Při chybě dotazu nechá předchozí stav.
  Ověření: testy na scénáře Osoby akce (4 z 6, skrytá se nepočítá,
  po pojmenování 5 z 6, chyba zachová stav).

## 4. Osoby v kompletnosti akce

- [ ] 4.1 `archive.py`/`model.py`: hotovost dostane `osoby`
  `[pojmenovane, celkem]` z `.work/immich-osoby.json` (jen když akce
  má zjištění), `incomplete` vrátí i `osoby` při nepojmenovaných.
  Výpis akcí se Immiche neptá. Ověření: testy v `tests/test_archive.py`
  (nebo `tests/test_model.py`, podle místa výpočtu) na scénáře Stav
  akce a Hotovost akce s osobami.
- [ ] 4.2 Karta akce (`app.js`): osoby v hotovosti (`osoby 4/6`), odkaz
  na nástroj u archiváře a admina při nepojmenovaných, štítek
  „nekompletní“ i kvůli osobám. Navigátor: ikona osoby s počtem na
  řádku Akce, klik otevře nástroj (ostatním jen údaj). Ověření:
  prohlížeč nad testovacím archivem s podvrženými počty ve `.work/`.
  README, Aplikace → seznam akcí a plocha: osoby v kompletnosti.

## 5. Server nástroje pojmenování

- [ ] 5.1 Nový modul `fotoarchiv/naming.py` (bez Flasku): ze stránky
  `search_album` sestaví osoby k pojmenování (nepojmenované, neskryté,
  bez odložených, pořadí podle počtu obličejů v akci) a ke každé až
  3 výřezy z různých assetů s největším obličejem. Připojí metadata
  z Immiche a z `_metadata.json` po zdědění (`model`) přes `file_key`.
  Ověření: `tests/test_naming.py` na scénáře Osoby k pojmenování,
  Náhledy obličeje (3 z 5, 1 z 1) a Metadata zdrojové fotky (spárovaná
  i nespárovaná fotka).
- [ ] 5.2 Odložené osoby: `.work/pojmenovani.json`
  `{login: {akce: [id]}}`, atomický zápis, vyřazení id, které mezitím
  dostalo jméno nebo bylo skryto, nové kolo vymaže odložení. Ověření:
  testy na scénáře Odložení osoby (znovuotevření, konec kola, jiný
  uživatel).
- [ ] 5.3 Endpointy v `app.py`: `GET /api/akce/<nazev>/osoby`,
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

- [ ] 6.1 Nový modul `fotoarchiv/static/naming.js`: čistá funkce výřezu
  (obdélník + rozměr zmenšeniny → výřez) a pořadí kroků kola. Ověření:
  `tests/js/naming.test.mjs` (`node --test tests/js/*.test.mjs`,
  zkontrolovat počet testů ve výstupu).
- [ ] 6.2 Překryv nad plochou akce (`<dialog>`, `::backdrop`
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

- [ ] 7.1 AGENTS.md: invariant „do Immiche zapisuje jen nástroj
  pojmenování (osoby) a synchronizace (alba)“, soubory nástroje ve
  `.work/` a role archivář pro nástroj. README, Datový model: osoby
  v kompletnosti a soubory ve `.work/`. Ověření: diff obou souborů
  odpovídá specifikaci.
- [ ] 7.2 Ruční zkouška uživatele proti skutečnému Immichi: test
  připojení s rozšířeným klíčem, založené album dokončené akce, průchod
  nástrojem na mobilu i notebooku, převzetí jména do `obliceje` po
  zavření. Ověření: hlášení uživatele.
