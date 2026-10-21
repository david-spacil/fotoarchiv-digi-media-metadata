## Context

- Relativní cesta každého nahraného souboru je v `import.json`
  (`soubory[].cesta`): u výběru složky `webkitRelativePath`
  (`DOD 2015/DOD 2015_Lenka/x.jpg`), u přetažení `fullPath`, u výběru
  jednotlivých souborů jen jméno. Do archivu jde soubor pod `nazev`
  (zploštěně).
- `Imports.overview` už pouští exiftool nad nahranými soubory (přístroj,
  datum) s cache `import-<id>`; `scan.propose_groups` pracuje nad
  seznamem `{nazev, pristroj}`.
- Provedení importu drží zámek akce: klient ho bere u stávající akce
  (`acquireLock`), server u nové (`locks.acquire` v `import_execute`)
  a `require_lock` ho ověřuje. Provedení je jen v produkčním režimu.
- `GET /api/akce/<nazev>` u akce bez `_metadata.json` sestaví dokument
  přes `model.new_document(…, scan.propose_groups(files))`; u akce
  s ním doplní nové soubory přes `model.merge_scan` (bez skupiny).
- `Workspace.save(name, doc, version)` ukládá atomicky s kontrolou
  verze.

## Goals / Non-Goals

**Goals:**
- Jedna funkce, která z `cesta`/přístrojů a volby spočítá přiřazení
  souborů ke skupinám; stejný výsledek pro plán i provedení.
- Zápis do `_metadata.json` týmž způsobem, jakým ho mění plocha (verze,
  zámek), bez souběžné úpravy z klienta.

**Non-Goals:**
- Kombinace voleb (část podle podsložek, část do existující skupiny).
  Doladí se na ploše běžnými nástroji pro skupiny.
- Údaje skupin kromě `nazev` a `pristroj` (autoři z názvu podsložky se
  neodvozují).
- Zachování podsložek na disku — zploštění zůstává.

## Decisions

**Volba skupin je součást cíle importu.** Klient ji posílá s cílem do
`/plan` i `/provest` (`skupiny: {"rezim": "podslozky" | "jedna" |
"auto" | "zadne" | "existujici", "nazev"?, "skupina"?}`); server ji
ukládá do `import.json` vedle `cil` (`set_target`), aby šla po návratu
předvyplnit. Alternativa — samostatný krok průvodce — přidává klik bez
nové informace; volba závisí na cíli (existující skupiny), takže patří
k němu.

**Výpočet v `importer.group_plan(entries, scanned, doc, volba)`.**
Vrací `{"skupiny": {gid: {nazev, pristroj?}}, "prirazeni": {nazev: gid},
"nove": [gid…]}` jen pro média s výsledkem `ok`. Kořen výběru =
společný prefix adresářových částí `cesta`. Režim `auto` volá
`propose_groups` nad podmnožinou souborů s přístroji z `overview`
(exiftool cache už existuje, nový běh se neplatí). Funkce nic
nepřipojuje sama: u každé nové skupiny vrátí `shody` (existující
skupiny se stejným názvem bez diakritiky a velikosti písmen nebo se
stejným přístrojem) a připojení použije jen z `volba["pripojit"]`
(`{nova_gid: existujici_gid}`). Přečíslování kolizí `gid`/názvu je
tamtéž.
`gid` nových skupin přes `scan.slug`, kolize řeší sufix `-2…` jako
`propose_groups`.

**Akce s `_metadata.json` — zápis po přenosu v `import_execute`.**
Po události `vysledek` server: `ws.load` → `scan.scan(event_dir)`
(technické údaje přenesených souborů, cache akce) → `model.merge_scan`
→ doplnit `skupiny` (jen nové gid) a `skupina` u přenesených souborů,
které ji nemají → `ws.save(…, version)`. Výsledek dostane pole
`skupiny: {"zapsano": bool, "chyba"?}`. Klient pak `_metadata.json`
nemá otevřený (drží jen zámek z průvodce importu), takže konflikt verze
nastane jen při ruční úpravě souboru mimo aplikaci; pak se nic
nepřepíše a výsledek ohlásí soubory bez skupiny. Alternativa — zapsat
v klientovi po výsledku — by vyžadovala načíst celou akci (exiftool nad
akcí) v průvodci importu a závisela na otevřené záložce.

**Akce bez `_metadata.json` — návrh v `.work/navrhy-skupin/<akce>.json`.**
Formát jako výstup `propose_groups` (`skupiny`, `prirazeni`). Další
import do téže akce návrh doplní; skupiny návrhu se v plánu chovají
jako existující (včetně nabídky připojení). V `akce_detail` pro
`novy`: přiřazení z návrhu pro soubory v kořeni, zbytek
`propose_groups`; skupiny bez souborů vypadnou. `PUT
/api/akce/<nazev>/metadata` při vzniku souboru (`version is None`)
návrh smaže. Návrh je v `.work/` i v produkčním režimu — je to
přechodný stav, ne zdroj pravdy; jeho ztráta znamená jen automatický
návrh.

**Připojení se volí v plánu, ne v kroku cíle.** Shody jsou známé až
po výpočtu skupin. Klient posílá `pripojit` jen s `/provest`; plán se
kvůli němu nepřepočítává (hashování by se opakovalo zbytečně), server
ho při provedení aplikuje na znovu spočtené skupiny a neznámé gid
ignoruje. Předvolba „nová skupina“: chybné sloučení dvou autorů se na
ploše hůř pozná než zbytečně rozdělená skupina, kterou jde sloučit.

**Klient.** Krok cíle dostane blok „Skupiny“ s radii podle dostupných
režimů. Podsložky pozná klient z `cesta` v přehledu. Pro „zařadit do“
potřebuje skupiny cílové akce: nový `GET /api/akce/<nazev>/skupiny`
vrací jen `skupiny` z `_metadata.json`, jinak z návrhu (bez skenu;
`null`, když není ani jedno). `GET /api/akce/<nazev>` by spustil exiftool nad celou akcí.
Plán dostane sloupec skupiny a pod ním seznam nových skupin s výběrem
„nová skupina / připojit ke skupině …“; shody jsou v nabídce nahoře
a označené.

## Risks / Trade-offs

- [`scan.scan` celé akce po importu na SMB trvá] → cache exiftoolu
  akce; nové soubory se čtou jen jednou a tutéž práci by stejně udělalo
  příští otevření akce.
- [Uživatel otevře akci v jiné záložce během provedení] → nejde,
  provedení drží zámek akce.
- [Výběr skládaný z víc přetažení nemá společný kořen] → kořen je
  prázdný, podsložky = první složka každé cesty, soubory bez složky
  zůstanou bez skupiny; plán to ukáže.
