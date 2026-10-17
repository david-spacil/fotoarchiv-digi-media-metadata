# Design

## Context

Motivace viz proposal.md. Stav na `main` (`a9ba96a`), ze kterého návrh
vychází:

- `fotoarchiv/immich.py` dnes jen čte: `GET /api/server/version`,
  `GET /api/people?withHidden=true`, `POST /api/search/metadata`
  (`personIds`), `GET /api/faces?id=`. `collect` bere jen pojmenované
  osoby (ř. 197), takže pro nepojmenované dnes nic nenačítá.
- Asset se se souborem páruje přes poslední dvě části `originalPath`
  (`file_key`, ř. 182); kořen archivu v Immichi se nenastavuje.
- `Sync` (ř. 252) běží po startu a každých 15 min, na požádání přes
  `trigger()`; `/api/immich*` je jen pro admina (`ADMIN_PREFIXES`,
  app.py:33).
- Hotovost a štítek „nekompletní“ počítá `archive.py` (ř. 186–210) přes
  `model.completeness`/`incomplete` jen z `_metadata.json` a výpisu
  složky; klient je kreslí v `app.js` (ř. 643–715).
- Dialogy klienta jsou `<dialog>` + `showModal()` s barevným
  `::backdrop` (`style.css:392`); rozmazání pozadí zatím nikde není.
- Nedokončené akce mají v produkci příponu `.ignored`, Immich je tedy
  nevidí (`event-visibility`).

API Immiche, ze kterého návrh vychází, je ověřené ve spec v3.3.3
(`open-api/immich-openapi-specs.json` @ tag v3.3.3, staženo 2026-10-17):

| Účel | Endpoint | Oprávnění |
|---|---|---|
| oprávnění klíče | `GET /api/api-keys/me` (`permissions`) | – |
| osoby | `GET /api/people` | `person.read` |
| assety alba s osobami | `POST /api/search/metadata` (`albumIds`, `withPeople`, `withExif`, `originalPath`) | `asset.read` |
| obličeje assetu | `GET /api/faces?id=` | `face.read` |
| zmenšenina | `GET /api/assets/{id}/thumbnail?size=preview` | `asset.view` |
| jméno, skrytí | `PUT /api/people` (hromadně; `PUT /api/people/{id}` je deprecated) | `person.update` |
| sloučení | `POST /api/people/merge` (`ids`, první = cíl; `/{id}/merge` je deprecated) | `person.merge` |
| alba | `GET/POST /api/albums`, `GET /api/albums/{id}`, `PUT`/`DELETE /api/albums/{id}/assets` | `album.read`, `album.create`, `albumAsset.create`, `albumAsset.delete` |

## Goals / Non-Goals

**Goals:**
- Projít nepojmenované osoby jedné akce bez přepínání do Immiche
  a mít v aplikaci vidět, kolik jich zbývá.
- Zachovat invariant: `obliceje` zapisuje jen synchronizace a nástroj
  `_metadata.json` nemění.

**Non-Goals:**
- Obličeje bez osoby (Immich je pod prahem „minimum recognized faces“
  k osobě nepřiřadil) a ruční přidávání obličejů.
- Přesouvání jednotlivých obličejů mezi osobami a oprava chybného
  shlukování (dělá se v Immichi).
- Použití nástroje mimo fotoarchiv (např. skeny archivních fotografií).
- Rozpoznání přejmenování akce u alba (viz Open Questions).

## Decisions

### Nástroj prochází osoby (shluky), ne obličeje
Pojmenování shluku je záměr: jedno jméno pokryje i fotky mimo akci.
Alternativa „obličej po obličeji“ by vyžadovala přeřazování obličejů
(`PUT /api/faces/{id}`) a dělala by z nástroje opravu shlukování.

### Fotky akce vymezuje album, které vede synchronizace
Synchronizace najde assety akce přes `POST /api/search/metadata`
s `originalPath` = název akce, výsledek dofiltruje přes `file_key`
(filtr je podřetězec `ILIKE %…%`, takže název akce, který je částí
jiného, vrátí i cizí fotky). Pak album založí nebo doplní. Nástroj
i počty osob pak čtou jen `albumIds` + `withPeople`, což je jeden
stránkovaný dotaz na akci.

Album vzniká v synchronizaci, ne při dokončení: ve chvíli dokončení
složka teprve ztrácí `.ignored` a Immich ji ještě neproskenoval.
Vazba akce → id alba je ve `.work/immich-alba.json`. Při ztrátě
souboru se album dohledá podle názvu, takže se nezakládá duplicitní.

Alternativa „bez alba, vždy `originalPath`“ zamítnuta: stejný dotaz
s dofiltrováním by se opakoval při každém otevření nástroje a album
je navíc v Immichi užitečné samo o sobě. Uživatel si provedení alb
vyhradil k podrobnému rozmyšlení, až na ně přijde řada (úkol 2.1);
tento oddíl je výchozí návrh.

### Počty osob ve `.work/immich-osoby.json`
Hotovost se nesmí ptát Immiche (seznam akcí musí zůstat rychlý), proto
počty ukládá synchronizace: `{akce: {pojmenovane, celkem, cas}}`.
Nástroj po každé akci počty akce přepočítá z odpovědi, kterou už má,
takže karta a navigátor jsou aktuální hned po zavření. Do
`_metadata.json` počty nepatří: nejsou to údaje o fotkách a měnily by
verzi akce i stav „změněno po exportu“.

### Kolo a odložené osoby ve `.work/pojmenovani.json`
Struktura `{login: {akce: [person_id, …]}}`, zápis atomicky jako ostatní
soubory ve `.work/`. Kolo = množina odložených. Vyprázdní ji až volba
„projít odložené znovu“, nebo když odložená osoba mezitím dostala jméno
nebo byla skryta (při načtení se taková id vyřadí). Alternativy:
`localStorage` (nepřežije jiný prohlížeč nebo mobil) a stav jen
v relaci (nepřežije zavření), obě zamítnuty podle rozhodnutí v issue.

### Endpointy pod akcí, role archivář
- `GET /api/akce/<nazev>/osoby`: seznam osob k pojmenování, výřezy
  (asset id + obdélník + rozměr zmenšeniny) a metadata.
- `GET /api/akce/<nazev>/osoby/nahled/<asset_id>`: proxy zmenšeniny,
  jen pro asset z alba akce.
- `POST /api/akce/<nazev>/osoby/<person_id>` s `{"akce": "pojmenovat" |
  "sloucit" | "nevim" | "skryt", "jmeno"?, "cil"?}`.
- `POST /api/akce/<nazev>/osoby/kolo`: nové kolo (vymaže odložení
  uživatele v akci).
- `POST /api/akce/<nazev>/osoby/hotovo`: zavření; spustí `Sync.trigger()`,
  pokud relace v nástroji něco změnila.

Nejsou pod `/api/immich`, protože ten je celý jen pro admina. Kontrola
role je `auth.rights(...)["archivar"]`, stejně jako u přetřídit.
Zámek akce se nevyžaduje: nástroj `_metadata.json` nemění a souběh dvou
archivářů nad jednou osobou skončí posledním zápisem v Immichi, což je
neškodné. Alternativa „vyžadovat zámek“ zamítnuta, protože by blokovala
pojmenování v akci, kterou zrovna někdo upravuje.

### Zápis i ve vývojovém režimu
Vývojový režim chrání archiv, Immich archivem není. Bez zápisu by nástroj
nešel vyzkoušet. Testy používají podvržený Immich (`FakeImmich`), na
skutečný server nesahají. Rozhodnutí je v proposal jako BREAKING
(provoz), aby bylo vidět.

### Výřez v klientu z jedné zmenšeniny
Server vrátí obdélník z `GET /api/faces` a rozměr zmenšeniny
(`imageWidth/Height`), na kterou se Immich vztahuje. Klient výřez
vykreslí z proxované zmenšeniny `preview` (CSS `object-view-box`, nebo
canvas, jako záloha). Obdélník platí pro otočenou zmenšeninu, stejně
jako u `area()`. Výpočet výřezu je čistá funkce v `naming.js` s unit
testem. Alternativa „ořez na serveru“ (Pillow) zamítnuta: přidala by
práci serveru a další cache.

### Výběr až 3 fotek
Z fotek alba s obličejem osoby se vezmou 3 s největším obličejem
(plocha obdélníku vůči zmenšenině), každá z jiného assetu. Velký obličej
je nejlépe rozpoznatelný a výběr je deterministický, takže test nezávisí
na pořadí odpovědi Immiche.

### Shoda jména a sloučení
Seznam osob Immiche se při otevření nástroje načte jednou
(`GET /api/people`). Shoda se hledá přes `names.normalize`. Kanonický
tvar a návrhy jdou ze stávajících `/api/jmena` a `/api/jmena/kontrola`
(`names.check`: `mysleli_jste`, `prevod`). Sloučení volá
`POST /api/people/merge` s `ids = [existující, aktuální]`, cílem je
existující osoba. Pojmenování a skrytí jde přes hromadné `PUT /api/people`
s jednou položkou.

### Překryv s rozmazaným pozadím
Nástroj je `<dialog>` přes plochu akce, `::backdrop` dostane
`backdrop-filter: blur(…)` s poloprůhledným `var(--backdrop)`. Bez
podpory `backdrop-filter` zůstane jen barevné pozadí. Odkaz ze seznamu
je URL plochy akce s parametrem (např. `#osoby`), který po načtení
plochy nástroj otevře. Klient nástroje je nový ES modul
`static/naming.js`, aby nerostl `app.js`.

### Test oprávnění klíče
`test_connection` přidá krok `GET /api/api-keys/me` a porovná
`permissions` se seznamem potřebným pro alba a nástroj. Chybějící
oprávnění je varování, ne chyba: čtecí synchronizace funguje dál.
Klíč s `all` má vše.

## Risks / Trade-offs

- [Pojmenování shluku přepíše i fotky mimo akci a chybný shluk se tím
  rozšíří] → záměr uživatele. Nástroj ukazuje výřezy jen z akce
  a u pole jména upozorní, že jméno dostane osoba na všech fotkách
  v Immichi.
- [Hromadný zápis do Immiche při chybě v kódu] → každá operace se týká
  jedné osoby, jinak nic. Alba se jen doplňují a odebírají z nich
  assety, nikdy se nemažou. Testy proti `FakeImmich` kontrolují, že
  synchronizace neposílá nic mimo tato volání.
- [Album podle `originalPath` zachytí cizí akci se stejným podřetězcem
  v cestě] → dofiltrování přes `file_key` (složka akce + soubor přesně).
- [Počty osob jsou staré až 15 min] → nástroj je přepočítá hned, ostatní
  změny v Immichi se projeví při dalším běhu, karta ukazuje stav
  posledního zjištění.
- [Velké akce: `withPeople` vrátí mnoho dat] → stránkování po 1000,
  stejné jako u stávajících dotazů. Při prvním běhu se počty zjišťují
  postupně, akce bez zjištění osoby v hotovosti nemají.
- [Uživatel smaže album v Immichi] → synchronizace ho založí znovu
  (scénář v `immich-people`).

## Migration Plan

1. Admin rozšíří klíč Immiche o oprávnění z tabulky. Test připojení
   chybějící vypíše.
2. Po nasazení první běh synchronizace založí alba všem dokončeným
   akcím, které Immich zná, a uloží počty osob. Akce bez zjištění
   zůstávají bez osob v hotovosti.
3. Návrat: stará verze `.work/immich-alba.json`, `immich-osoby.json`
   ani `pojmenovani.json` nečte. Alba v Immichi zůstanou a jdou smazat
   ručně.

## Open Questions

- Přejmenování akce: přejmenovat album, nebo založit nové? (Dnes
  aplikace akce nepřejmenovává. Až začne, vazba ve `.work/` se musí
  přenést.)
- Výsledná sada polí metadat zdrojové fotky (uživatel ji chce doladit
  na prototypu). Spec určuje minimum.
- Přesná podoba alb (úkol 2.1): popis alba, sdílení s dalšími
  uživateli Immiche (`albumUsers`), zahrnout soubory označené
  k vyřazení?
