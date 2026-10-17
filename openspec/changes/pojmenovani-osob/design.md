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
  nevidí (`event-visibility`). `akce_finish` (app.py:372) příponu
  odebere, ale Immich složku načte až při svém příštím skenu knihovny.

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
| knihovny | `GET /api/libraries` | `library.read`, jen admin |
| sken knihovny | `POST /api/libraries/{id}/scan` (asynchronní, celá knihovna) | `library.update`, jen admin |
| fronty úloh | `GET /api/queues/{name}` (`statistics.active`, `waiting`, …) | `queue.read`, jen admin |

Asset nemá příznak „obličeje zpracovány“. Má jen `resized` (zmenšenina
hotová), a ta je vstupem detekce obličejů. Rozpoznání proto jde
poznat jen nepřímo, z `resized` a z front `faceDetection`
a `facialRecognition`.

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

### Fotky akce vymezuje album
Assety akce se hledají přes `POST /api/search/metadata` s `originalPath`
= název akce. Výsledek se dofiltruje přes `file_key`, protože filtr je
podřetězec `ILIKE %…%` a název akce, který je částí jiného, by vrátil
i cizí fotky. Do alba patří spárované soubory kořene kromě označených
k vyřazení (stejně jako hotovost). Nástroj i počty osob pak čtou jen
`albumIds` + `withPeople`, což je jeden stránkovaný dotaz na akci.

Album nemá popis a nesdílí se s dalšími uživateli Immiche. Patří
uživateli klíče. Vazba akce → id alba je ve `.work/immich-alba.json`.
Při ztrátě souboru se album dohledá podle názvu, takže nevznikne
duplicitní.

Alternativa „bez alba, vždy `originalPath`“ zamítnuta: dotaz
s dofiltrováním by se opakoval při každém otevření nástroje. Album je
navíc v Immichi užitečné samo o sobě.

### Album zakládá dokončení akce, synchronizace ho udržuje
Po úspěšném zveřejnění složky (odebrání `.ignored`) spustí
`akce_finish` hlídač akce na pozadí a hned odpoví. Dokončení na Immich
nikdy nečeká a chyba Immiche dokončení neshodí. Hlídač:

1. spustí sken knihovny vybrané v nastavení
   (`POST /api/libraries/{id}/scan`);
2. po `HLIDAC_INTERVAL` (20 s) se ptá `search/metadata` na assety akce.
   Hotovo je, když Immich zná všechny soubory alba. Druhá možnost:
   fronta `library` je prázdná a počet nalezených se mezi dvěma dotazy
   nezměnil (soubory, které Immich nenaimportuje, by jinak hlídače
   držely do vypršení);
3. založí album, nebo doplní a odebere assety, je-li už vazba;
4. sleduje rozpoznávání: hotovo je, když mají všechny assety alba
   `resized` a fronty `faceDetection` i `facialRecognition` nemají
   aktivní ani čekající úlohy. Pak spustí `Sync.trigger()` (obličeje,
   počty osob);
5. po `HLIDAC_LIMIT` (60 min) skončí a další práci převezme pravidelná
   synchronizace.

Na akci běží nejvýš jeden hlídač. Opakované dokončení ho pustí znovu,
což je žádoucí: sken načte i nové sidecary. Pravidelná synchronizace
dělá kroky 2–4 pro každou dokončenou akci (bez skenu), takže album
dorovná i po restartu serveru, po smazání alba v Immichi nebo po změně
složky. Hlídač je jen zrychlení, ne jediná cesta.

Fronty jsou společné celému Immichi, takže rozpoznávání cizích fotek
ohlášení „rozpoznáno“ jen oddálí, nikdy neuspíší. Rozpoznávání krátce
po vzniku assetu ještě nemusí být ve frontě. Tento závod pokrývá
podmínka `resized`: detekce se zařazuje až po zmenšenině
(pravděpodobné podle chování Immiche, v API neověřené; ověří ruční
zkouška 7.2). Obličeje pod prahem „minimum recognized faces“ Immich
přiřadí k osobám až nočním během. Stav „rozpoznáno“ proto neznamená, že
počet osob už se nezmění. Pravidelná synchronizace počty dorovná.

Ve vývojovém režimu se `.ignored` neodebírá a sken nic nového nenajde,
proto se nespouští. Kroky 2–4 proběhnou, pokud Immich fotky akce už
zná.

Zamítnuto: jen spustit sken a nechat album pravidelné synchronizaci
(album až po 15 min a déle, uživatel neví kdy); konec podle fronty
`library` jako jediné kritérium (fronta je společná všem knihovnám);
čekat v požadavku dokončení (minuty, timeout).

### Stav akce v Immichi, viditelný všem
Stav je ve `.work/immich-alba.json`:
`{akce: {album, stav, cas, chyba?}}`. Zapisuje ho hlídač
i synchronizace (atomicky, pod zámkem v paměti):

| stav | význam | uživatel vidí |
|---|---|---|
| `nacitani` | sken spuštěn, Immich fotky akce ještě nezná všechny | „Immich načítá fotky“ |
| `rozpoznavani` | album je, obličeje se zpracovávají | „Rozpoznávání obličejů probíhá“ |
| `rozpoznano` | rozpoznávání doběhlo (s časem) | „Obličeje rozpoznány (datum)“ |
| `nenalezeno` | hlídač vypršel a Immich fotky nezná | „Immich fotky akce zatím nenašel“ |

Chybějící oprávnění nebo nedostupný Immich stav nemění. Zapíšou se do
`chyba` a ukážou se jen na stránce nastavení. Stav vidí každý
přihlášený uživatel na kartě akce a na ploše akce. Výpis akcí ho čte ze
`.work/`, Immiche se neptá. Plocha během `nacitani` a `rozpoznavani`
stav obnovuje přes `GET /api/akce/<nazev>/immich` (jen tento soubor,
bez dotazu na Immich). Bez nastaveného Immiche se stav nezobrazuje.

Nástroj pojmenování jde otevřít od stavu `rozpoznavani`. Do
`rozpoznano` ale ukazuje upozornění, že seznam osob ještě není úplný.
Počty osob na kartě se do `rozpoznano` neuvádějí, aby akce nevypadala
jako hotová, dokud Immich obličeje teprve hledá.

### Knihovnu vybírá admin
Nastavení Immiche dostane výběr knihovny ze `GET /api/libraries`.
Id se uloží do `immich.json`. Odvodit knihovnu z cesty archivu nejde,
protože cesta v kontejneru Immiche je jiná. Bez vybrané knihovny se
sken nespouští, kroky 2–4 běží dál. Test připojení na to upozorní.

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
`permissions` se seznamem potřebným pro alba, sken, fronty a nástroj.
Chybějící oprávnění je varování, ne chyba: čtecí synchronizace funguje
dál. Klíč s `all` má vše. Sken a fronty jsou v Immichi jen pro admina,
takže klíč musí patřit uživateli s rolí admin. Test to pozná podle
odpovědi `GET /api/libraries` (403) a vypíše to. Varuje i tehdy, když
není vybraná knihovna.

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
- [Sken je vždy pro celou knihovnu a u archivu na SMB může trvat
  dlouho] → spouští se jen při dokončení (ne v pravidelné
  synchronizaci). Hlídač má limit a pak práci převezme synchronizace.
- [Klíč admina Immiche má širší práva, než aplikace potřebuje] →
  oprávnění klíče se omezí na seznam z tabulky. Klíč zůstává jen
  ve `.work/immich.json`.
- [„Obličeje rozpoznány“ se ohlásí dřív, než Immich doplní noční
  přiřazení] → stav znamená „hlavní zpracování doběhlo“. Počty osob
  dorovnává pravidelná synchronizace.

## Migration Plan

1. Admin vytvoří klíč pod uživatelem s rolí admin v Immichi
   s oprávněními z tabulky a v nastavení vybere knihovnu archivu. Test
   připojení vypíše, co chybí.
2. Po nasazení první běh synchronizace založí alba všem dokončeným
   akcím, které Immich zná. Jejich stav je rovnou `rozpoznano`, pokud
   fronty rozpoznávání stojí. Uloží i počty osob. Akce bez zjištění
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
- Délka `HLIDAC_INTERVAL` a `HLIDAC_LIMIT` se doladí podle ruční
  zkoušky na skutečném archivu (7.2).
