## Context

`GET /api/akce` (`Workspace.list_events`) čte jen kořeny akcí
(`os.scandir`) a `_metadata.json`; na serveru trvá 0,16–0,19 s pro
13 akcí. Rekurzivní průchod celého archivu včetně `_kos.ignored` na
CIFS trvá 0,7–1,2 s (8 113 souborů, ~0,1 ms na soubor, medián akce
16–18 ms, největší složka `přetřídit` 0,3–0,7 s); viz komentář v #56.
Měřeno na serveru za provozu aplikace.

Stav, který nepatří do archivu, aplikace drží ve `.work/` jako JSON
zapisovaný atomicky (`.tmp` + `os.replace`, např. `scan.py`,
`immich.py`). Vysypání koše běží ve vlákně `kos-vysypani` v `app.py`
jen v produkčním režimu. Klient řadí a filtruje v `static/fronta.js`
(čisté funkce s testy), `fmtSize` je zatím v `static/app.js`.

## Goals / Non-Goals

**Goals:**
- Velikost akcí a koše bez zpomalení výpisu akcí.
- Jeden zdroj údaje (`.work/velikosti.json`) pro seznam, součty i koš.

**Non-Goals:**
- Živý údaj (sledování změn souborového systému, inotify na CIFS).
- Velikost složek mimo akce (`přetřídit`, `fotky mimo akce`) a volné
  místo na disku.
- Zabrané bloky (`st_blocks`) — na SMB nespolehlivé.

## Decisions

### Modul `fotoarchiv/velikost.py` s jedním pracovním vláknem

Třída `Velikosti(ws)`:
- `bajtu(path_list)` — rekurzivní součet `st_size` přes `os.scandir`
  se zásobníkem, `follow_symlinks=False`; chyby `OSError` u podsložky
  zalogovat a pokračovat (údaj je pak spodní odhad, ne pád).
- cache `{"akce": {nazev: {"bajtu", "cas"}}, "kos": {id: {...}}}`
  v `.work/velikosti.json`, čtení a zápis pod `threading.Lock`, zápis
  atomicky.
- `akce()` / `kos()` — kopie slovníků pro výpis bez I/O kromě čtení
  JSON (drží se v paměti, soubor se čte jen při startu).
- `zmena(nazev)` a `zmena_kos(id)` — zařadí přepočet do fronty
  (množina bez duplicit) a probudí vlákno.
- `presun_do_kose(nazev, id)`, `vratit_z_kose(id, nazev)`,
  `odebrat_z_kose(ids)` — přesuny údaje bez průchodu.
- vlákno `velikosti` zpracovává frontu po jedné položce; když je
  fronta prázdná, čeká na událost s časovým limitem do dalšího denního
  přepočtu. Denní přepočet zařadí všechny akce (`ws.event_names()`)
  a všechny složky koše a odebere z cache položky, které už neexistují.
  Při startu zařadí akce a položky koše bez údaje.

Proč fronta a jedno vlákno, ne synchronní přepočet v endpointu:
endpointy (import běží jako stream, úklid, dokončení) nemusí čekat na
SMB a vždy prochází archiv nejvýš jeden průchod, takže denní přepočet
nesoupeří s přepočtem po změně. Synchronní přepočet by byl při
naměřených desítkách ms také možný, ale u velké akce (stovky ms až
sekundy) by prodlužoval odpověď. Údaj je „k datu“, krátké zpoždění po
změně spec připouští.

Proč vlastní vlákno a ne vlákno `kos-vysypani` (issue navrhovalo
přidat k němu): to běží jen v produkčním režimu, kdežto velikost má
smysl i ve vývojovém režimu (archiv se jen čte). Testy vlákno
nespouští (parametr `velikost_interval=None` v `create_app`, stejně
jako `kos_interval`) a volají přepočet přímo.

### Klíče cache

Akce podle názvu bez přípony (jako zámek a `.work`); kolizi řeší
`bajtu` nad oběma složkami (`ws.archiv / nazev` a `… + .ignored`,
existují-li), ne přes `ws.event_dir`, který při kolizi vyhazuje.
Položky koše podle ID složky v `_kos.ignored`. Údaj o koši se do
`_smazano.json` nepíše: záznam je historie smazání, ne cache, a jeho
přepis po přesunu je zbytečné riziko.

### Napojení v `app.py`

- `akce_list`: `event["bajtu"] = velikosti.akce().get(nazev, {})
  .get("bajtu")`; nic dalšího nečte.
- `GET /api/velikost` → `{"akce": součet, "kos": součet}` pro každého
  přihlášeného (žádná položka v `ADMIN_PREFIXES`). Součet akcí jen přes
  názvy, které jsou dnes v archivu, aby záznam smazané složky (změna
  přes SMB) do denního přepočtu nenafukoval součet. Klient by součet
  akcí uměl sečíst z `bajtu`, ale součet koše potřebuje endpoint tak
  jako tak a dva zdroje pro jeden řádek by se mohly rozejít.
- `zmena(nazev)` po: úspěšném `import_execute` (cílová akce),
  `akce_cleanup_execute`, `akce_finish` (přejmenování složky, sidecary).
- `akce_smazat` (produkce): `presun_do_kose(nazev, result["id"])`.
- `kos_obnovit`: `vratit_z_kose(id, nazev)` a `zmena(nazev)`.
- `vysypat()`: po `trash.purge` odebrat z `kos` ID, jejichž složka
  v `_kos.ignored` už neexistuje (jeden `scandir` koše).
- `GET /api/kos`: `trash.entries` dostane volitelný slovník velikostí
  a doplní `bajtu` (bez průchodu složek).

`akce_list` pro akci, která nemá údaj, zavolá `zmena(nazev)`, aby
nová akce (vzniklá přes SMB) nemusela čekat na denní přepočet.

### Klient

- `fronta.js`: přesunout sem `fmtSize` (export, `app.js` ho importuje),
  nové řazení `["velikost", "Podle velikosti", …]` (bez údaje na konci,
  shoda `byDate`) a `celkemText(akce, kos)` → `Celkem 25 GB
  (+5 GB v koši)` / bez závorky při `kos` 0 nebo `null`.
- `app.js`: `eventMeta` doplní ` · ${fmtSize(e.bajtu)}`, je-li
  `bajtu != null`; seznam načte `/api/velikost` paralelně s `/api/akce`
  a řádek součtu ukáže pod filtry; chyba endpointu = řádek se neukáže.
- Stránka Koš: sloupec velikosti z `bajtu`.

## Risks / Trade-offs

- [Údaj po změně přes SMB až den starý] → přijatelné podle #56;
  CLI příkazy, které mění archiv (`zkontrolovat --zapis-do-archivu`,
  `exportovat`, `skryt`), běží mimo server a zachytí je denní přepočet.
- [Denní přepočet zatíží SMB současně s prací uživatelů] → ~1 s pro
  dnešní archiv, i 10× větší archiv kolem 10 s; jedno vlákno, žádný
  paralelismus.
- [Přerušený přepočet (restart serveru)] → cache se zapisuje po každé
  položce atomicky; neúplný stav = některé položky starší, při startu
  se doplní chybějící.
- [Souběh přepočtu a přesunu do koše] → přesun údaje i zápis výsledku
  přepočtu jdou pod stejným zámkem; výsledek přepočtu akce, která
  mezitím zmizela z archivu, se zahodí (kontrola existence složky
  před zápisem).
- [Více procesů] → stejně jako zámek akcí jen jeden proces serveru
  (`AGENTS.md`); `.work/velikosti.json` píše jen server.

## Migration Plan

Žádná migrace dat. Po nasazení první start zařadí všechny akce a koš
k přepočtu na pozadí; do jeho doběhnutí (sekundy) karty velikost
neuvádějí. Návrat = předchozí image; `.work/velikosti.json` se pak
ignoruje a jde smazat.
