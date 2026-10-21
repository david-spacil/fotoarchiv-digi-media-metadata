## Context

Ověřeno proti Immichi 3.3.0-rc2 (6. 10. 2026) na knihovně
`Konference Příkladné metody`:
- `POST /api/search/metadata` s `withPeople: true` vrací u assetu
  `originalPath` a `people: [{id, name, …}]`; nepojmenovaný obličej má
  `name: ""`.
- `GET /api/faces?id=<asset>` vrací obličeje s `boundingBoxX1..Y2`,
  `imageWidth`, `imageHeight`, `sourceType` a `person {id, name}`.
- Jména zadávají lidé v Immichi, tvar nevynucuje (`Ukázková, Věra`
  i `Rudolf Smyšlený`). Immich vidí archiv pod jiným kořenem
  (`/immich/archiv/…`).

Z GitHubu (immich-app/immich):
- PR #6455 (sloučen 4. 9. 2024): import oblastí obličejů MWG z metadat
  a sidecarů, vytvoří osobu podle `mwg-rs:Name`; přepínač „Import faces
  from metadata“, výchozí vypnuto.
- Diskuze #15083 (otevřená): zápis obličejů do sidecarů Immich neumí.
- Diskuze #15107 (otevřená): obličeje z metadat se neslučují s ML
  obličeji; podle nálezu `peemot` (1. 4. 2026) proto, že ML obdélníky
  jsou vztažené ke zmenšenině (max 1920 px) a porovnávají se bez
  normalizace.
- `peemot/immich-export`: Immich → JSON → XMP s MWG oblastmi; potřebuje
  `asset.read` a `face.read`. Inspirace, ne závislost.

Zámek akcí je jen v paměti serveru (`lock.py`), proto synchronizace
běží uvnitř serveru (rozhodnuto: varianta A1). Ruční osoby jsou jen
u jednoho souboru akce `2026-09-08 Konference Příkladné metody`;
rozhodnuto je zahodit. Záloha obličejů: varianta B (vždy v JSONu,
do sidecaru jen pro obnovu).

## Goals / Non-Goals

**Goals:**
- Immich jediný zdroj osob; `_metadata.json` nese úplnou zálohu
  pojmenovaných obličejů, ze které jde Immich obnovit.
- Žádné kolize se zápisem uživatele.
- Klíč nikdy v archivu, v repu ani v prohlížeči.

**Non-Goals:**
- Zápis do Immiche (klíč je jen pro čtení).
- Nepojmenované obličeje (Immich je při obnově najde sám), embeddingy,
  náhledy osob, data narození.
- Slučování duplicit po obnově (#15107) — věc Immiche.
- Oprava tvaru jmen v Immichi.
- Ochrana stránky nastavení přihlášením — patří do `add-login`.

## Decisions

**Synchronizace v serveru (A1).** Vlákno démon spuštěné z `create_app`
(jen když je nastavení), běh po startu a pak každých 15 minut, další
běh na tlačítko. Jeden běh najednou (mutex); tlačítko při běžícím
běhu jen vrátí stav. Cron ani CLI se nezavádí.

**Dotazy na Immich.** `GET /api/people` (stránkovaně, včetně skrytých)
→ pojmenované osoby; pro každou `POST /api/search/metadata`
s `personIds: [id]` (stránkovaně) → assety; pro každý takový asset
`GET /api/faces?id=…` → obdélníky (souběžně, malý počet vláken).
Alternativa projít všechny assety s `withPeople` by s celým archivem
znamenala stovky stránek každých 15 minut. Dotazy na obličeje jen
u assetů s pojmenovanou osobou. Selže-li kterýkoli dotaz, běh se celý
zahodí — neúplná mapa by obličeje mazala.

**Oblast.** `x = (x1+x2)/2/imageWidth`, `y = (y1+y2)/2/imageHeight`,
`w = (x2-x1)/imageWidth`, `h = (y2-y1)/imageHeight`, zaokrouhleno na
4 místa. Normalizace podle rozměru, ke kterému Immich obdélník vztahuje,
odstraní problém s měřítkem z #15107 a dává přímo tvar MWG `stArea`.
Zaokrouhlení brání přepisu kvůli šumu po přepočtu ML.

**Orientace (ověřeno 6. 10. 2026, Immich 3.3.0-rc2).** Na
`20260909_132018.jpg` (EXIF Orientation 6, uloženo 4624 × 3468):
(a) ML obličeje z `/api/faces` mají `imageWidth/Height` 1440 × 1920,
tedy zmenšenina už otočené fotky; oblast přepočtená vzorcem výše
a nanesená na otočený originál trefí obličej. Oblast v `obliceje` je
proto přímo vůči otočené fotce, bez další úpravy.
(b) `mwg-rs:Regions` čte Immich vůči fotce v **uloženém** tvaru
a sám je otočí: oblast zapsaná vůči otočené fotce (s rozměry
3468 × 4624) skončila mimo obličej; oblast převedená do uloženého
tvaru (`x = y_d`, `y = 1 − x_d`, `w`/`h` prohozené) s rozměry
4624 × 3468 skončila na obličeji ML s odchylkou do 0,0002. Export pro
obnovu proto převádí oblast do uloženého tvaru podle EXIF Orientation
(1–8) a `AppliedToDimensions` jsou rozměry uloženého obrázku (Pillow
bez `exif_transpose`).
Obličej z metadat se přiřadil ke stávající osobě stejného jména
a ML obličej zůstal vedle něj (duplicita podle #15107).

**Párování.** Poslední dvě části `originalPath` = (složka akce, soubor);
bere se jen složka, která je akcí s `_metadata.json`, a soubor, který
v ní je. Bez konfigurace kořene.

**Zápis.** Pro každou akci: spočítat nové `obliceje` všech souborů
(seřazené podle jména a pak `x`, jména kanonizovaná přes `names.py`);
liší-li se od uložených, získat zámek s relací `immich-sync` a jménem
„Immich (synchronizace)“, načíst aktuální verzi, zapsat, uvolnit.
Drží-li zámek jiná relace, akce se přeskočí. Záznam o exportu se
posune, jestliže odpovídal verzi před zápisem. Zápis jde přes stejnou
cestu jako ukládání z plochy (režim, atomický zápis, verze).

**Model.** `obliceje` mimo dědění v `model.py` i `inherit.js` (shodně,
fixtury); `osoby` se nikde nečte a při uložení se odstraní, stejně jako
`obliceje` mimo soubory. Jména obličejů vstupují do seznamu jmen
(`names.py`). Klient `obliceje` v ukládaném diffu neposílá — nemůže
přepsat, co mezitím zapsala synchronizace.

**Export pro obnovu.** `exportovat --obliceje` přidá do sidecaru
`mwg-rs:Regions` (`AppliedToDimensions` v pixelech originálu, rozměry
přes Pillow s ohledem na výsledek ověření orientace; `RegionList`
s `Area` `unit="normalized"`, `Type` `Face`, `Name`). Sidecar dál skládá
aplikace sama (deterministicky). Export pro obnovu nemění záznam
o exportu; po obnově se běžným exportem sidecary vrátí do běžného
tvaru. Volba jen v CLI — obnova je výjimečná operace správce.

**Nastavení.** `.work/immich.json` `{adresa, klic}`, zápis atomicky
s `0600`. API: `GET /api/immich` (adresa, „klíč …XXXX“, stav posledního
běhu), `PUT /api/immich` (adresa + klíč; změna adresy bez klíče → 400),
`DELETE /api/immich`, `POST /api/immich/test` (`/api/server/version`,
`/api/people?size=1` a `/api/faces` u jednoho assetu — ověří
oprávnění), `POST /api/immich/sync`. Stránka `#/nastaveni`, odkaz
v hlavičce. Systémová klíčenka a proměnná prostředí zamítnuty.

**HTTP klient.** `urllib.request` jako v `geocode.py`, hlavička
`x-api-key`, timeout. Funkce pro dotaz jde podvrhnout v testech.

## Risks / Trade-offs

- [Orientace: obdélník z Immiche a MWG se mohou vztahovat k různě
  otočenému obrázku] → první úkol implementace, ověření na skutečné
  fotce a zkušební import.
- [Obnova vytvoří vedle obličejů z metadat i duplicitní ML obličeje
  (#15107)] → jména se zachovají; v novém Immichi spustit import
  metadat před rozpoznáváním, duplicity řešit v Immichi.
- [Po exportu pro obnovu kontrola nanečisto hlásí sidecary jako
  neaktuální] → záměr; běžný export je vrátí.
- [Synchronizace přepíše `_metadata.json` mezi otevřením akce
  a získáním zámku uživatelem] → ochrana verzí, klient dostane konflikt.
- [Přejmenování nebo přesun souboru = nový asset v Immichi, obličeje
  se ztratí] → známé omezení (README); záloha v `_metadata.json` jde
  s přejmenováním a lze ji obnovit exportem pro obnovu.
- [Stránka nastavení dostupná bez přihlášení] → klíč se nevrací, změna
  adresy vyžaduje klíč; plně řeší `add-login`.
- [Počet dotazů `/api/faces` roste s počtem fotek s pojmenovanými
  osobami] → jen ty assety, souběžnost omezená; při potřebě později
  porovnávat `updatedAt` osob.

## Migration Plan

Po nasazení první synchronizace nahradí jediný ručně vyplněný soubor
obličeji z Immiche; `osoby` se při uložení odstraní. Sidecary dosud
exportovaných akcí obsahují `osoba/…`; kontrola nanečisto je ukáže
jako neaktuální a export je přepíše. Návrat: vrátit commit, ruční osoby
jsou ztracené (rozhodnuto).
