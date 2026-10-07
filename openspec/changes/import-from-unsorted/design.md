## Context

Import (`fotoarchiv/importer.py`) dnes pracuje jen s nahranými soubory:
`import.json` drží záznamy `{nazev, cesta, ulozeno, velikost, mtime_ns,
sha256}`, `iter_plan` z nich staví plán (duplicity podle `sha256`,
kolize jmen), `execute` kopíruje ze stagingu přes `_copy` (dočasný
`.import-*.tmp`, kontrola cíle, přejmenování). Přehled čte EXIF přes
`scan.scan` jen z kořene stagingu. Zámky akcí drží `lock.Locks`
v paměti, klíčem je název akce.

`přetřídit` leží na stejném SMB svazku jako akce, po zploštění má 36
složek první úrovně (5–600 souborů, 24 plochých, ostatní s podsložkami:
obal s jednou podsložkou, skupiny, `NEF`, varianty `JPEG orig`).
Motivace viz proposal.md, požadavky viz `specs/unsorted-import`.

## Goals / Non-Goals

**Goals:**
- Import ze zdroje použije stávající průvodce, plán, skupiny a zápis
  `_metadata.json` beze změny chování; liší se jen původ souborů
  a přenos.
- Na SMB přes VPN číst co nejméně dat: hashovat jen soubory, u kterých
  hrozí duplicita.

**Non-Goals:**
- Import zanořených složek jako samostatných akcí (kontejner
  `70_Kouřil` jde jen jako jedna akce se skupinami, nebo se rozdělí
  ručně).
- Dávkový import víc složek najednou (varianta C z issue #5).
- Rozhodování o podsložkách ve zdroji z aplikace (přejmenování na
  `.ignored` dělá uživatel ručně).
- Jiné zdroje než `přetřídit` (`přednášky SKLEP TIC`).

## Decisions

### Záznam importu se zdrojem, soubory se neukládají
`import.json` dostane `zdroj` = název složky první úrovně `přetřídit`;
`soubory` zůstane prázdné. Záznamy souborů server sestaví při každém
přehledu, plánu i provedení z aktuálního výpisu zdroje (`os.walk`
s vynecháním podsložek `*.ignored` a `Thumbs.db`): `cesta` =
`<složka>/<relativní cesta>`, `zdroj` = absolutní cesta místo `ulozeno`.
Prefix názvem složky zajistí, že `selection_root` a skupiny „podle
podsložek“ a „jedna nová skupina“ fungují jako u nahrané složky.

*Alternativa:* uložit výpis do `import.json` při založení. Zastará,
jakmile někdo ve zdroji něco změní; plán se stejně sestavuje znovu.

### Snímek plánu jako měřítko provedení
Každý plán uloží do `import.json` `plan_zdroj` = [{cesta, velikost,
mtime_ns}]. Provedení sestaví záznamy z aktuálního zdroje jako dosud
a porovná je se snímkem: chybějící → operace `chyba` „ve zdroji už
není“, jiná velikost/mtime → `blokovano` „změnil se po plánu“, mimo
snímek → do plánu nejdou, výsledek je nese v `po_planu` (cesty).
Bez snímku → 409 `bez_planu`. Jen import se zdrojem; u nahraných
souborů obsah stagingu mění jen aplikace.

*Alternativa:* seznam cest posílaný klientem s provedením. Po reloadu
mezi plánem a provedením chybí a klientovi by se muselo věřit.

### Hash jen u možných duplicit
`iter_plan` potřebuje `sha256` u každého záznamu. U zdroje ho server
spočítá jen pro soubory, jejichž velikost má soubor v kořeni cílové
akce, nebo jiný soubor výběru; ostatní dostanou zástupnou hodnotu
jedinečnou pro záznam (nemůže se shodovat). Hashe se cachují stejně
jako hashe akce (`.work/cache/sha256/`, podle cesty, velikosti
a mtime) a průběh jde stejnými událostmi `hash`/`hash_prubeh`. Pro
novou akci se tak čte jen pár souborů se shodnou velikostí.

*Alternativa:* hashovat celý zdroj při založení importu. DOD 2016 má
~600 souborů; přes VPN minuty čtení, které ve většině případů nic
nepřinese.

### Přesun přejmenováním, bez kopie
Přenos ze zdroje je `os.rename` po kontrole, že cíl neexistuje (stejně
jako `cleanup._move`, souběh v cílové akci vylučuje zámek akce). Obsah
i mtime se zachovají samy, ověření hashem odpadá. Chybějící zdrojový
soubor nebo `EXDEV` (jiný svazek) je selhání souboru, ne pád importu;
kopie jako záložní cesta se nedělá — `přetřídit` je vždy na svazku
archivu. `execute` dostane přenos jako parametr (kopie ze stagingu /
přesun ze zdroje); průběh u přesunu po souborech, `prubeh` po bajtech
se neposílá.

*Alternativa:* kopie a smazání zdroje. Na SMB pomalé, přechodně
zdvojuje data a přerušení nechá kopie na obou místech.

### Úklid zdroje
Po provedení projde server zdroj odspodu: složku, ve které je jen
`Thumbs.db` nebo nic, smaže (nejdřív `Thumbs.db`, pak `rmdir`).
Podsložky `*.ignored` se neprocházejí ani nemažou — jsou záznamem
o ignorování. Výsledek dostane `zdroj_zbyva` (počty zbylých souborů)
a `zdroj_smazan`.

### Přehled `přetřídit` jako samostatný modul
Nový `fotoarchiv/unsorted.py`: výpis složek první úrovně, počty podle
`importer.kind`, data z názvu (regexy pro `d.m.yyyy`, `yyyy_mm_dd`,
`yyyy_m_d`, `dd_mm_yyyy`, samotný rok jen informativně) a EXIF přes
`scan.scan` volaný na každou složku zdroje zvlášť s `cache_name`
`pretridit-<sha1 relativní cesty>` (cesta má `/` a diakritiku). Endpoint
`GET /api/pretridit` streamuje NDJSON po složkách: nejdřív výpis bez
EXIF (rychlý), pak údaje složek v pořadí. Stejný výpis bez EXIF slouží
kroku Soubory průvodce.

`Imports.overview` pro import se zdrojem sestaví `items` ze stejných
skenů, klíčem je `cesta` (ne `nazev` — zploštělá jména se ve zdroji
mohou opakovat).

### Zámek zdroje v `Locks`
Klíč `přetřídit/<složka>` — obsahuje `/`, takže se nepotká s názvem
akce. Provedení ho získá před prvním přesunem (relace a jméno jako
u akce), během přesunu obnovuje heartbeat po souborech a uvolní ho
v `finally` / `call_on_close`. Obsazený zdroj → odmítnutí 409 se jménem
držitele.

### Založení ze stránky a opakované kliknutí
`POST /api/import` s `zdroj` ověří, že složka existuje, je na první
úrovni `přetřídit` a nekončí `.ignored` (žádné `..` ani `/`). Má-li
uživatel už rozpracovaný import téže složky, vrátí jeho `id` místo
nového. Ze stránky Přetřídit klient pošle i navržený cíl
(`cil`, `nova: true`), uloží se jako u `set_target`.

## Risks / Trade-offs

- [Zástupný hash maskuje duplicitu se stejnou velikostí v jiné akci]
  → Duplicity se hledají jen proti cílové akci i u nahrávání; napříč
  archivem je řešila deduplikace v issue #5.
- [Varianty se stejným jménem (`Procházka 60/JPEG orig`) zablokují
  kořen i podsložku] → Bezpečné (nic se nepřesune); uživatel podsložku
  přejmenuje na `.ignored` a import zopakuje. Popsat v README.
- [Přehled přes VPN pomalý (exiftool na 6 000 souborů)] → cache podle
  (jméno, velikost, mtime), postupné zobrazení; v provozu běží server
  u archivu.
- [Přerušení během přesunu] → každý přesun je atomický rename; přesunuté
  jsou v akci, zbytek ve zdroji; opakovaný import potřebuje nový plán
  (jinak by přesunuté hlásil jako zmizelé). Skupiny se zapíší jen za dokončené provedení —
  stejně jako u kopie.
- [Změna cest v `přetřídit` vs. Immich] → Immich `přetřídit` vynechává;
  cílové akce dostávají nové soubory jako při běžném importu.

## Migration Plan

Žádná migrace dat. Stávající importy (bez `zdroj`) fungují beze změny.
Nasazení = nový build kontejneru. Návrat = předchozí verze; akce
vzniklé přesunem zůstanou platnými akcemi.
