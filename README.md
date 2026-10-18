# fotoarchiv-digi-media-metadata

Průvodce obohacením metadat digitální fotodokumentace ARÚB
(`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Lokální webová
aplikace s náhledy, ve které se fotkám a videím přiřazují metadata
jednotlivě nebo po skupinách.

Aplikace má dva režimy. Výchozí vývojový archiv jen čte
a `_metadata.json` ukládá do pracovního adresáře `.work/` mimo archiv;
produkční (`--zapis-do-archivu`) ukládá `_metadata.json` do složky akce
a úklid provádí. Testy viz `AGENTS.md`.

## Lokální spuštění

Potřeba: Python 3, `exiftool`, `ffmpeg` (bez něj videa nemají náhled)
a připojený archiv (na Fedoře např. `dnf install perl-Image-ExifTool
ffmpeg`).

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m fotoarchiv \
  --archiv /mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
```

Aplikace běží na <http://127.0.0.1:5000> na produkčním WSGI serveru cheroot
v jediném procesu s obslužnými vlákny. Bez dalších přepínačů je to
vývojový režim: archiv se jen čte, metadata a cache jdou do `.work/`.
Server spouštět jen jednou (zámky akcí jsou v paměti procesu).
Přístup vyžaduje přihlášení (viz Přihlášení níže).
Hlavička ukazuje verzi běžícího kódu podle `git describe --tags
--always --dirty` (např. `v0.2.0-1-g5609826`), zjištěnou při startu
serveru; po `git pull` ji ukáže až restart.

Volitelné přepínače:

- `--zapis-do-archivu` — produkční režim, `_metadata.json` se ukládá do
  složek akcí a provádí se úklid a import.
- `--bez-prihlaseni` — vývojový režim bez přihlášení: každý je admin
  a jméno u zámku se zadává v prohlížeči. S `--zapis-do-archivu` server
  odmítne start.
- `--vlakna N` — počet obslužných vláken serveru (výchozí 32).
- `--debug` — vývojový server Werkzeugu s reloaderem pro ladění kódu.
- `--https` — cookie relace jen přes HTTPS (za reverzní proxy s HTTPS).
- `--work CESTA` — jiný pracovní adresář než `.work`.
- `--host`, `--port` — adresa a port (výchozí `127.0.0.1:5000`).

Jednorázové skrytí nedokončených akcí před Immichem (viz
[Archiv](#archiv)), při zastaveném serveru:

```sh
.venv/bin/python -m fotoarchiv skryt --archiv … --zapis-do-archivu
```

Kontrola poškozených souborů v archivu (viz [Poškozené
soubory](#poškozené-soubory)), archiv jen čte:

```sh
.venv/bin/python -m fotoarchiv zkontrolovat [AKCE] --archiv … --work .work
# → kontrola poškození souborů; navíc vypíše nálezy konzistence akcí
#   (nepodporované soubory, osiřelé sidecary, RAWy, podsložky,
#   záznamy bez souboru); --rychle jen konzistenci, --zapis-do-archivu
#   po potvrzení převede nálezy s nápravou do .ignored složek
```

Napojení na Immich (obličeje) a kontakt pro Nominatim (geokódování
míst) nastavuje admin v aplikaci; uloží se do `.work/immich.json`
a `.work/nominatim.json`. Zastaralý přepínač `--kontakt` server při
startu převezme do `.work/nominatim.json`, pokud ještě neexistuje.

### Přihlášení

Účty jsou lokální. Uživatele zapisuje správce ručně do
`.work/uzivatele.json` (login → kanonické jméno, volitelně e-mail
a role); aplikace ho jen čte, změna platí bez restartu a odebraný
uživatel přijde o přístup při dalším požadavku:

```json
{"prikladny": {"jmeno": "Příkladný, Daniel", "email": "…",
               "role": "admin"},
 "novak": {"jmeno": "Novák, Petr", "role": "archivar"},
 "modelova": {"jmeno": "Modelová, Zuzana"}}
```

Role je `"admin"`, `"archivar"`, nebo chybí (běžný uživatel).
Dřívější zápis `"admin": true` a neznámá role jsou chyba: server ani
příkaz `heslo` nenastartují a vypíšou chybné loginy s návodem
(`"admin": true` → `"role": "admin"`). Objeví-li se chybný záznam za
běhu, server běží dál, chybný login nemá přístup (401) a chyba jde do
logu.

Úvodní nebo zapomenuté heslo vydá správce na serveru:

```sh
.venv/bin/python -m fotoarchiv heslo LOGIN --work .work
```

Příkaz vypíše jednorázové heslo; po přihlášení s ním aplikace pustí
jen na změnu hesla. Vydání nového hesla ukončí stávající relace
uživatele. Heslo si pak uživatel mění sám (aspoň 10 znaků, odkaz se
jménem v hlavičce); změna ukončí jeho ostatní relace.

Hesla jsou jen jako hash se solí (`werkzeug.security`, scrypt)
v `.work/hesla.json`, který píše jen aplikace; tajný klíč relací je
v `.work/relace.key`. Všechny tři soubory mají práva jen pro
vlastníka (`uzivatele.json` nastaví správce). Odpověď na chybné
přihlášení neprozradí, zda login existuje; po 5 chybných pokusech na
login server další pokusy zdržuje.

Jen **admin** smí měnit Nastavení (Immich včetně synchronizace na
požádání, kontakt pro Nominatim). **Admin a archivář** smějí stránku
Přetřídit s importem ze složky `přetřídit` a vynuceně uvolnit zámek
akce. Ostatním server vrátí 403 a klient tyto prvky nezobrazí.

**Úprava akce** (zámek, uložení, dokončení, úklid, import do ní): admin
a archivář každou akci, běžný uživatel jen akci, v jejímž `upravili`
je jeho jméno (porovnání jako u jmen) — v praxi tu, kterou sám
naimportoval nebo upravoval. Akci bez `_metadata.json` nebo bez
`upravili` upravují jen admin a archivář. Prohlížet smí každý všechno.
Bez oprávnění server zámek odmítne (403) a klient akci otevře jen ke
čtení s vysvětlením; seznam ji označí „jen ke čtení“ a průvodce
importem ji nenabídne jako cíl. Bez přihlášení smí každý všechno.

Zatím běží přes HTTP ve firemní síti (přijaté riziko): heslo a cookie
jdou sítí čitelně, přihlašovací stránka na to upozorní. Cookie je
`HttpOnly` a `SameSite=Lax`; `Secure` zapne `--https`, až bude
reverzní proxy s HTTPS.

Na Windows místo `.venv/bin/` použít `.venv\Scripts\`.

### Docker

Pro server s Dockerem (např. tam, kde běží Immich) je v repozitáři
`Dockerfile`, `compose.yaml` a `.env.example`. Kontejner běží
v produkčním režimu (`--zapis-do-archivu`) na serveru cheroot v jediném
procesu bez varování vývojového serveru, archiv se připojuje z hostitele
(typicky SMB/CIFS mount) a pracovní adresář je bind mount `./work`;
správce v něm ručně edituje `uzivatele.json`. Před nasazením verze
s rolemi přepsat `"admin": true` na `"role": "admin"` (a doplnit
`"role": "archivar"`), jinak se kontejner restartuje dokola a důvod je
v `docker compose logs`.

```sh
cp .env.example .env          # a vyplnit FOTOARCHIV_ARCHIV, UID, GID
mkdir work                    # pracovní adresář vedle repozitáře
docker compose up -d --build  # http://127.0.0.1:5000
```

Archiv musí být připojený **před** startem kontejneru: jinak Docker
připojí prázdnou složku a po připojení SMB je potřeba kontejner
restartovat (`docker compose restart fotoarchiv`).

Kontejner běží pod UID/GID z `.env` (`user:` v compose). U archivu na
CIFS musí odpovídat vlastníkovi, kterého určují volby mountu (soubor
s přihlašovacími údaji číst netřeba):

```sh
A=/mnt/x/fotoarchiv/FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB
stat -c '%u:%g' "$A"
findmnt -no OPTIONS -T "$A"   # volby uid=, gid=, file_mode=, dir_mode=
```

Stejné UID musí mít i `./work` (`chown UID:GID work`), jinak aplikace
nezapíše cache ani hesla. Zápis do archivu ověřit před ostrým startem
přímo z kontejneru:

```sh
docker compose run --rm --entrypoint sh fotoarchiv \
  -c 'touch /archiv/.zapis-test && rm /archiv/.zapis-test'
```

Účty a příkazy v kontejneru:

```sh
# účty edituje správce na hostiteli: work/uzivatele.json
# (viz Přihlášení), pak jednorázové heslo:
docker compose exec fotoarchiv python -m fotoarchiv heslo LOGIN --work /work
# dávkový export XMP všech akcí:
docker compose exec fotoarchiv python -m fotoarchiv exportovat \
  --archiv /archiv --work /work --zapis-do-archivu
# kontrola poškozených souborů všech akcí (archiv jen čte):
docker compose exec fotoarchiv python -m fotoarchiv zkontrolovat \
  --archiv /archiv --work /work
# jednorázové skrytí nedokončených akcí před Immichem (při zastaveném
# serveru; bez --zapis-do-archivu jen výpis):
docker compose stop fotoarchiv
docker compose run --rm fotoarchiv skryt \
  --archiv /archiv --work /work --zapis-do-archivu
docker compose start fotoarchiv
```

Aktualizace: `git pull && docker compose up -d --build`.

Verzi v hlavičce zapíše build image z `.git` (`git describe --tags
--always`, bez příznaku neuložených změn); `.git` se do image
nekopíruje. Image postavený mimo pracovní kopii gitu ukáže „verze
neznámá“.

Poznámky:

- Vývojový režim v kontejneru: v `compose.yaml` odebrat
  `--zapis-do-archivu` z `command` (metadata pak jdou do `/work`).
- Až poběží reverzní proxy s HTTPS, přidat do `command` přepínač
  `--https` (cookie relace jen přes HTTPS).
- Server smí běžet jen v jedné instanci (zámky akcí v paměti).
- Immich se nastavuje v aplikaci adresou dosažitelnou z kontejneru,
  např. adresou hostitele; případně lze připojit kontejner do sítě
  Immiche jako external network v compose.

## Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`. Zpracovávají se jen
  ty; ostatní (`přednášky SKLEP TIC`, `fotky mimo akce`) se nechávají
  beze změny. Výjimkou je generovaný index `_INDEX.html` a `_INDEX.md`
  (viz [Výstupy](#výstupy)) a `přetřídit`, ze které v produkčním
  režimu přesouvá soubory import (viz [Import](#import)).
- **Nedokončená akce je skrytá před Immichem** (issue #13): její složka
  má příponu `.ignored` (`2026-04-28 kontrola Stezky.ignored`), takže ji
  Immich vynechá stejným vzorem jako ignorované podsložky. Akce se
  v aplikaci, v URL, u zámku i v `.work` jmenuje bez přípony; přípona je
  jen vlastnost složky. Import zakládá novou akci rovnou skrytou,
  dokončení příponu odebere (viz [Tok práce](#tok-práce)) a dokončená
  akce ji už znovu nedostane. Stávající nedokončené akce (a akce
  nakopírované do archivu mimo aplikaci) skryje jednorázově
  `python -m fotoarchiv skryt --archiv … --zapis-do-archivu` při
  zastaveném serveru; bez přepínače jen vypíše, co by přejmenoval.
  Akce, kterou Immich už načetl, z něj skrytím zmizí i s obličeji
  a po dokončení se načte znovu jako nové assety. Existuje-li složka
  s příponou i bez ní, aplikace akci ukáže jako *kolize složek*
  a nepracuje s ní, dokud jednu správce archivu neodstraní nebo
  nesloučí; nic sama nepřesouvá.
- `přetřídit` drží nezatříděné akce k importu, `fotky mimo akce`
  materiál, který akcí není (sbírky, portréty, výběry pro web, podklady
  na večírky). Kopie, které při zploštění `přetřídit` vyšly jako
  duplicity, leží v `přetřídit/_duplicity.ignored/` (viz issue #5);
  složky a podsložky s příponou `.ignored` import nenabízí ani
  nepřesouvá.
- Ve složkách jsou JPG, mp4, RW2, občas png/zip a `Thumbs.db`
  (ignorovat). Některé akce mají podsložky (`RAW`, `Video`, …), viz
  [Podsložky a RAW](#podsložky-a-raw).
- Zdroje se liší kvalitou metadat:

  | vzor názvu            | přístroj          | EXIF                   |
  |-----------------------|-------------------|------------------------|
  | `P*.JPG`              | Panasonic DC-G9   | datum, bez GPS         |
  | `YYYYMMDD_HHMMSS.jpg` | Samsung SM-A528B  | datum, GPS             |
  | `IMG-YYYYMMDD-WA*.jpg`| WhatsApp          | žádný, datum jen v názvu |
  | `IMG_####.jpg`        | ?                 | neověřeno              |

## Podsložky a RAW

Zpracovává se jen kořen složky akce. Kořen má zůstat čistý pro
prohlížení: jen fotky a videa, která patří do Immiche.

- **Podsložky:** u každé podsložky bez přípony `.ignored` se průvodce
  zeptá, např. *„Složka `Video` obsahuje 22 souborů. Přesunout je mezi
  soubory akce, nebo složku ponechat stranou?“* Pro rozhodnutí ukáže až
  8 souborů rovnoměrně z jejích fotek a videí (náhled s názvem, klikem
  zvětšit); bez fotek a videí jen názvy ostatních souborů.
  - *Přesunout:* obsah jde do kořene, prázdná složka (včetně
    `Thumbs.db`) se smaže.
  - *Ponechat:* složka se přejmenuje na `název.ignored` a dál se jí
    průvodce nevšímá.
- **Přípona `.ignored` je jediný záznam o ignorování** — nikde jinde se
  seznam ignorovaných složek nevede. Immich ji vyloučí jedním vzorem.
- **RAW** (`rw2`, `cr2`, `cr3`, `nef`, `arw`, `dng`, `orf`, `raf`, bez
  ohledu na velikost písmen) do Immiche nejde a nepáruje se s JPG.
  - Podsložka, kde RAWy tvoří většinu souborů, se při ponechání
    přejmenuje na `RAW.ignored` bez ohledu na původní název (`raw`,
    `RAWy`, …).
  - RAWy v kořeni průvodce nabídne přesunout do `RAW.ignored`.
- **Vyřazené soubory** (nepovedené fotky, duplicity) se nemažou: soubory
  označené na pracovní ploše úklid přesune do `k_odstraneni.ignored`
  v kořeni akce. Před přesunem zapíše vedle cíle sidecar s rozepsanými
  údaji souboru (bez tagu o vyřazení — vyřazení značí jen složka),
  sidecar v kořeni odstraní a po přesunu smaže záznam souboru
  z `_metadata.json`. Blokuje i existující `<soubor>.xmp` v cíli;
  selže-li zápis sidecaru, soubor zůstane v kořeni i se záznamem.
  Vrácení: soubor ručně přesunout zpět, příští načtení ho přidá jako
  nový soubor bez ručních údajů.
- **Ostatní soubory** v kořeni — nepodporované (PDF, dokumenty, zipy,
  TIFF…) a osiřelé sidecary (`<soubor>.xmp` bez souboru) — úklid
  přesune do `ostatni.ignored` v kořeni akce; v průvodci je přesun
  předem zapnutý. Sidecar, jehož soubor přijde do kořene z podsložky,
  osiřelý není.
- Přesun nikdy nepřepíše existující soubor; operace se shodou názvů se
  přeskočí a nahlásí, ostatní proběhnou a podsložka, ze které něco
  zbylo, se nesmaže. Pokud `RAW.ignored`, `k_odstraneni.ignored` nebo
  `ostatni.ignored` už existuje, soubory se do ní přidají.
- Přesuny a přejmenování mění cesty, které by Immich bral jako nové
  assety. Proto se mají udělat před napojením archivu do Immiche.

### Kontrola akce

Kontrola kořene akce najde, co v něm nepatří nebo si odporuje: soubor,
který není fotka, video ani RAW (*nepodporovaný*), osiřelý sidecar,
RAW v kořeni, podsložku bez `.ignored` a záznam v `_metadata.json`, ke
kterému v kořeni není soubor. Čte jen výpis kořene a `_metadata.json`
(ne obsah souborů), takže běží i při každém načtení seznamu akcí.
Nehlásí `Thumbs.db`, `_metadata.json`, sidecary se souborem, dočasné
soubory aplikace ani obsah podsložek. Názvy porovnává bez ohledu na
velikost písmen a NFC/NFD (`a.JPG.xmp` patří k `a.jpg`).

Seznam akcí ukáže u akce s nálezy štítek „k vyřešení“ (počty
v popisku), lišta pracovní plochy nálezy po druzích (klik vypíše názvy)
a kontrolní stránka dokončení je uvede mezi kontrolami k vyřešení —
dokončit jde i s nimi. Všechno kromě záznamu
bez souboru napraví **Uklidit…** (viz Tok práce); záznam bez souboru
zůstává i s ručními údaji, vrácený soubor se k němu znovu připojí.

m
## Poškozené soubory

Typická vada archivu (issue #10): bloky souboru jsou na kartě nebo
v souborovém systému vynulované a délka souboru zůstala. Nuly na
začátku znemožní soubor otevřít, nuly na konci nebo uprostřed fotky
dekodér často přijme jako platná data a ukáže šedý pruh. Exiftool ani
dekodér druhý případ nepoznají, proto hlavní kontrolou je test nul.

- **Kontrola souboru** přečte soubor jednou (zároveň spočítá sha256):
  - souvislý úsek nul aspoň **64 KiB** začínající na hranici bloku
    4 KiB (u fotek, videí i RAWů); kratší úseky mívají i zdravé
    soubory (metadata z Photoshopu, plochá barva);
  - fotka (jpg, jpeg, png) se dekóduje jako náhled (Pillow, `draft`):
    nerozpoznaný obrázek je nečitelný, useknutý obraz podezřelý;
    useknutý JPEG zakončený značkou konce (`FFD9`) dekodér přijme
    a kontrola ho nepozná;
  - video ověří `ffprobe` (bez čitelného video proudu, např. chybí
    `moov` po přerušeném nahrávání = nečitelné); bez `ffprobe` jen
    test nul s poznámkou; video se celé nedekóduje;
  - u videa MP4/MOV se nuly počítají **jen v obrazových datech** podle
    tabulek vzorků v `moov` (úsek přes obraz i zvuk součtem částí
    v obraze). Nuly mimo ně patří k formátu: výplň `free` (rezerva pro
    `moov`), pevně velké `udta`/`meta` (Panasonic) a ticho
    v nekomprimovaném zvuku PCM (Panasonic, ~188 KiB nul za sekundu).
    Bez čitelných tabulek (fragmentované MP4, poškozená hlavička) se
    počítá celý soubor;
  - RAW jen testem nul.
- **Výsledek:** *v pořádku*, *podezřelý* (otevře se, ale je poškozený),
  nebo *nečitelný* (prázdný, samé nuly, nejde otevřít), vždy s důvodem,
  např. „768 KiB nul od začátku“, „119 KiB nul na konci“.
- **Cache** výsledků je v `.work/cache/kontrola/` podle cesty,
  velikosti a času změny souboru; nezměněný soubor se znovu nečte.
  Změna pravidel kontroly cache zneplatní.
- **Aplikace:** při vytváření nového náhledu souboru z kořene akce se
  kontrola spustí a výsledek doplní do cache akce (prohlížením se
  zásobník plní sám; při hitu cache se soubor nečte). Odznak
  „N poškozených“ je v seznamu akcí i v liště plochy, dlaždice
  poškozeného souboru je červeně orámovaná s důvodem v tooltipu.
  U poškozeného souboru lze potvrdit „Považovat za v pořádku“
  v panelu dlaždice nebo hromadně v dialogu Uklidit…
  (falešná pozitivita dekodéru) — uloží se jako `overeno` a odznak ho
  nadále nepočítá; zrušení je stejné tlačítko. Náprava v archivu jde
  po cestě vyřazení: označit k vyřazení (dlaždice nebo dialog) a uklidit
  (do `k_odstraneni.ignored`, viz `vyradit` v
  [Datovém modelu](#datový-model)); žádná zvlášť složka poškozených
  není.
- **Import** kontroluje soubory v kroku Přehled (viz
  [Import](#import)); poškozené soubory nepřenese bez souhlasu.
- **Archiv:** příkaz `zkontrolovat` (viz [Lokální
  spuštění](#lokální-spuštění)) projde kořen a `RAW.ignored/` jedné nebo
  všech akcí (ostatní podsložky ne) a archiv jen čte. U každé akce
  vypíše a do reportu uloží i nálezy kontroly konzistence (viz
  [Kontrola akce](#kontrola-akce)); s `--rychle` se obsah souborů
  nečte, s `--zapis-do-archivu` příkaz u akcí s nálezy navrhne nápravu
  přesuny (ostatní soubory do `ostatni.ignored`, RAWy do
  `RAW.ignored`, podsložky bez volby se nemění) a po potvrzení ji
  provede; záznamy bez souboru se jen vypíší.
  Vypíše podezřelé a nečitelné soubory s důvodem a souhrn po akcích,
  report uloží do `.work/kontrola/report-<datum-čas>.json`. Report
  uvádí i nejdelší úsek nul u souborů pod prahem, aby šel práh po
  prvním průchodu archivem ověřit; u videa s přečtenými tabulkami
  nejdelší úsek v obrazových datech (`nuly`) i v celém souboru
  (`nuly_soubor`). Přerušení (Ctrl+C) nevadí: hotové
  akce jsou v cache.


## Datový model

Zdroj pravdy je **jeden `_metadata.json` v každé složce akce**. Vše
ostatní (XMP sidecary, index) se z něj generuje.

Hodnoty se dědí **akce → skupina → soubor**; nižší úroveň přepisuje
vyšší. **Každé pole jde přepsat na kterékoli nižší úrovni**, včetně
autorů u jednotlivé fotky. Výjimkou jsou účastníci a místa akce (viz
níže). Skupiny průvodce navrhne automaticky podle
přístroje a vzoru názvu, uživatel je může upravit.

```json
{
  "schema": "fotoarchiv-digi-media-metadata/1",
  "akce": {
    "nazev": "kontrola Stezky Drahanskou vrchovinou",
    "popis": "…",
    "datum_od": "2026-04-28",
    "datum_do": "2026-04-28",
    "mista": ["Vysočany", "Holštejn"],
    "ucastnici": ["Příkladný, Daniel", "Modelová, Zuzana"]
  },
  "souradnice_mist": {
    "Vysočany": {"gps": [49.43, 16.804],
                 "popis": "Vysočany, okres Blansko, …",
                 "osm": "relation/…"},
    "u rybníka": null
  },
  "skupiny": {
    "g9": {
      "autori": ["Příkladný, Daniel", "Modelová, Zuzana"],
      "pristroj": "Panasonic DC-G9"
    }
  },
  "soubory": {
    "P1503712.JPG": {
      "skupina": "g9",
      "datum": "2026-04-28T09:44:36",
      "gps": null,
      "misto": "Holštejn",
      "popis": "…",
      "obliceje": [{"jmeno": "Vzorný, Tomáš",
                    "oblast": [0.2725, 0.432, 0.041, 0.0747]}],
      "sha256": "…"
    },
    "P1503713.JPG": {"skupina": "g9", "vyradit": true}
  },
  "upravili": {"Příkladný, Daniel": "2026-10-14T10:15:02"}
}
```

- **Účastníci akce (`ucastnici`) se nedědí.** Jsou to důležití lidé,
  kteří byli na akci, a přednostní návrhy jmen — ne předpoklad, že jsou
  na každé fotce.
- **Osoby na fotkách jsou pojmenované obličeje z Immiche
  (`obliceje`).** Jen u souboru, nedědí se a v aplikaci se nezadávají:
  zapisuje je jen synchronizace (viz Aplikace, Immich). Položka je
  `{jmeno, oblast}`; `oblast` = `[x, y, w, h]` jako podíly rozměrů
  fotky zobrazené se správnou orientací (střed a velikost, tvar MWG),
  zaokrouhlené na 4 místa. Je to i záloha pojmenovaných obličejů,
  ze které jde Immich obnovit (viz Výstupy). Starší pole `osoby` se
  ignoruje a při uložení odstraní.
- **Místa akce (`mista`) jsou výčet**, fotka nebo skupina má jedno
  `misto`. Jediné místo akce se na fotky dědí; při víc místech se místo
  doplňuje u skupiny nebo fotky (návrhy z míst akce).
- **Souřadnice míst (`souradnice_mist`)** jsou rozhodnutí pro akci:
  přesný název `misto` → `{gps, popis}`, nebo `null` = „bez souřadnic“.
  Nedědí se, platí pro všechny fotky akce s tím místem. Výsledné `gps`
  fotky je vlastní nebo zděděné `gps`, jinak souřadnice jejího místa
  (úroveň `misto`); k souboru se neukládají a GPS z EXIF nepřepisují.
  Kandidáty hledá server v Nominatimu (OSM) až po otevření volby,
  odpovědi cachuje v `.work/cache/geokodovani.json` (sdílené všemi
  akcemi, smazatelné). User-Agent nese kontakt provozovatele, který
  nastavuje admin v Nastavení (jeden pro server, předvyplní se jeho
  e-mail); bez kontaktu je geokódování vypnuté. Předvybraný je kandidát nejbližší fotkám akce
  s GPS; potvrzuje ho uživatel. Přejmenování místa rozhodnutí
  nepřenese.
- **Autorů může být víc.** `autori` znamená „fotil někdo z uvedených“;
  zpětně se nedá zjistit, kdo kdy držel foťák.
- Údaje z EXIF (datum, přístroj, GPS) zapisuje průvodce, u WhatsAppu
  datum z názvu souboru. Ruční údaje doplňuje uživatel.
- `sha256` slouží k odhalení přejmenovaných nebo změněných souborů.
- **`vyradit: true`** označuje soubor k vyřazení (jen u souboru, nedědí
  se). Do XMP exportu takový soubor nejde, do chybějících údajů se
  nepočítá; úklid ho přesune do `k_odstraneni.ignored` a záznam smaže.
- **`overeno: true`** je ruční potvrzení, že soubor je i přes výsledek
  kontroly integrity v pořádku (jen u souboru, nedědí se, do sidecaru
  ani indexu nejde). Takový soubor se nepočítá do odznaku poškozených.
- **`upravili`** = kdo akci ukládal: jméno uživatele → čas jeho
  posledního uložení, dokončení nebo provedení importu do ní (ISO 8601,
  místní čas serveru, na sekundy; import zapisuje u nové akce i akce
  s `_metadata.json`). Zapisuje jen server jménem z přihlášené relace
  (stejné jako u zámku); hodnotu od klienta zahodí a vezme ji z uložené
  verze. Starší akce pole nemají, vznikne prvním uložením. Nedědí se, do
  sidecaru ani indexu nejde; slouží filtru „Moje rozpracované“, řazení
  seznamu akcí a oprávnění k úpravě akce (viz Přihlášení).
- **Osoby v kompletnosti akce** nejsou v `_metadata.json` (nejsou to
  údaje o fotkách a měnily by verzi akce). Počty pojmenovaných
  a neskrytých osob s obličejem v albu akce ukládá synchronizace (a po
  každém kroku nástroj pojmenování) do `.work/immich-osoby.json`
  `{akce: {pojmenovane, celkem, cas}}`. Hotovost je uvádí jen u akce
  s albem ve stavu *obličeje rozpoznány*; nepojmenované osoby dělají
  dokončenou akci „nekompletní“ (viz Aplikace, Immich).
- **Další soubory Immiche ve `.work/`** (nikdy v archivu):
  `immich.json` (adresa, klíč, knihovna; 0600), `immich-alba.json`
  `{akce: {album, stav, cas, chyba?}}` (vazba na album a stav akce
  v Immichi) a `pojmenovani.json` `{login: {akce: [id osoby]}}`
  (osoby odložené volbou „odložit“ v aktuálním kole).
- Originály se nemění.

## Jména osob

Žádný předem daný seznam. **Otevřený seznam návrhů** vzniká ze jmen
použitých ve všech `_metadata.json` v archivu a roste s tagováním.

- Kanonický tvar `Příjmení, Jméno`.
- Při zadání jména formulář porovná vstup se seznamem bez ohledu na
  diakritiku, velikost písmen a pořadí slov. Při shodě nabídne
  „Mysleli jste `Příkladný, Daniel`?“ a kliknutím opravený tvar
  propíše do pole (např. pro `Prikladny, Daniel` nebo
  `Daniel Příkladný`).
- Nové jméno, které nic nepřipomíná, se přijme a od té doby je
  v seznamu.
- Platí pro autory a účastníky. Jména obličejů z Immiche jsou
  v seznamu taky; jméno z Immiche, které se se jménem ze seznamu shoduje
  podle tohoto porovnání, synchronizace zapíše v tvaru ze seznamu,
  jinak tak, jak je v Immichi.

## Výstupy

- **XMP sidecary** pro import do Immich: `foto.jpg.xmp` vedle souboru,
  s rozepsanými zděděnými hodnotami. Generují se z `_metadata.json`,
  ručně se needitují. Co Immich nemá vlastní pole, jde do hierarchických
  tagů `digiKam:TagsList` podle konvencí repa
  [arubrno/archiv-immich](https://github.com/arubrno/archiv-immich)
  (kořen malými písmeny, `/` v názvu → `-`):

  | `_metadata.json` | XMP sidecar |
  |------------------|-------------|
  | `popis`          | `dc:description` |
  | `datum`          | `xmp:CreateDate` s časovou zónou |
  | `gps`, jinak souřadnice `misto` | `exif:GPSLatitude` + `exif:GPSLongitude` |
  | `autori`         | `digiKam:TagsList` > `autor/…` |
  | název složky akce | `digiKam:TagsList` > `akce/…` |

  Datum s časem dostane zónu Europe/Prague platnou v daný okamžik
  (`+01:00` / `+02:00`; při podzimní dvojí hodině letní čas), samotné
  datum (WhatsApp) dostane poledne se zónou — Immich datum bez času
  nepřijme a vezme čas z EXIFu; poledne neposune den ani v UTC. GPS ve
  formátu XMP `DDD,MM.mmmmmmK` (např. `49,24.378000N`). Prázdná pole se
  nezapisují; místo, přístroj, účastníci, osoby ani skupina do
  sidecaru nejdou (osoby má Immich z vlastního rozpoznávání obličejů;
  obličeje jen při obnově, viz níže). Sidecar skládá aplikace sama (ne exiftool), takže obsah
  závisí jen na `_metadata.json` a názvu složky akce.

  Ověřeno na Immichi 3.2 (5. 10. 2026): osoby (`Person`) vznikají jen
  z obličejů se souřadnicemi — `PersonInImage` ani tagy se jmény se
  neberou. Autora Immich nezobrazuje (autor = kdo nahrál). Místo
  (`photoshop:City`, `Iptc4xmpCore:Location`) Immich zahodí i u fotek
  bez GPS a obec bere jen z GPS. Fotky bez GPS proto dostanou
  souřadnice svého místa, geokódované přes Nominatim (OSM) s cache
  a volbou kandidáta (OpenSpec změna `add-place-geocoding`); název
  místa se do sidecaru nezapisuje. U výsledků Nominatimu aplikace
  uvádí „© OpenStreetMap contributors“.
- **Obnova obličejů:** `python -m fotoarchiv exportovat --obliceje`
  přidá do sidecarů souborů s `obliceje` oblasti MWG
  (`mwg-rs:Regions`, `Type` `Face`, `Name` = jméno). Immich se
  zapnutým „Import faces from metadata“ z nich po obnovení metadat
  (Refresh metadata u fotky; hromadná úloha nově nalezené sidecary
  nenačte) vytvoří obličeje přiřazené osobě daného jména (stávající
  osobě stejného jména, jinak nové). Ověřeno na Immichi 3.3.0-rc2
  (6. 10. 2026): Immich čte oblasti MWG vůči obrázku **v uloženém
  tvaru** a sám je otočí podle EXIF Orientation; export proto
  `oblast` převádí podle orientace (1–8) a `AppliedToDimensions` jsou
  uložené rozměry originálu. Obličej z metadat se neslučuje
  s obličejem z rozpoznávání (diskuze immich-app/immich #15107), ve
  stejném Immichi tak vznikne duplicita — obnova je pro nový nebo
  poškozený Immich. Export pro obnovu nemění záznam o exportu; běžný
  export pak sidecary vrátí do běžného tvaru.
- **Immich** bude archiv číst jako externí knihovnu jen pro čtení
  s výjimkami `**/*.ignored/**` (ignorované podsložky i nedokončené
  akce, viz [Archiv](#archiv)) a nezpracovanými složkami první úrovně
  (`přetřídit`, `přednášky SKLEP TIC`, `fotky mimo akce`). Testovací
  knihovna vidí archiv pod `/mnt/media/fotoarchiv/…`; aplikace z ní čte
  jen pojmenované obličeje (viz Aplikace, Immich).
- **Index** celého archivu pro lidi v Průzkumníku, místo ručně
  vedeného `_metadata.xlsx`. Generuje se, needituje; zdrojem jsou jen
  `_metadata.json` a soubory v kořeni akcí. Obsahuje všechny složky
  akcí (i nezpracované) podle data sestupně:
  - `_INDEX.html`: jeden soubor bez externích zdrojů, karta na akci
    (náhled prvního JPEG, datum, název, stav, místa, fotografové,
    účastníci, osoby z obličejů s počtem, počty foto/video, přístroje),
    odkaz do složky akce; s JavaScriptem hledání bez diakritiky
    a filtry roku a stavu. Upozornění na generování jen v komentáři.
  - `_INDEX.md`: upozornění, že je soubor generovaný, a tabulka
    `fancy_grid` (Datum, Akce, Místa akce, Fotili, Foto, Video).

  Fotografové jsou seřazení podle počtu souborů akce ve výsledných
  (zděděných) `autori`, zkráceně `Příjmení J.`. Index se přegeneruje
  po provedení importu, po dokončení akce v aplikaci a na konci
  `python -m fotoarchiv exportovat`, ne při uložení.
  Zapisuje se atomicky a jen při změně obsahu (bez času generování);
  selhání je jen varování. V produkčním režimu jde do kořene archivu
  s relativními odkazy, ve vývojovém do `.work/index/` s odkazy
  `file://` do archivu. `_metadata.xlsx` aplikace nemění; smazat ho je
  na člověku.

## Aplikace

Lokální webová aplikace spouštěná nad složkou archivu. Výchozí je
tmavý režim; přepínač v hlavičce přepne do světlého (pamatuje si ho
prohlížeč, platí i pro přihlášení). Lupa je tmavá v obou režimech.
Plocha je stavěná na okna od 1280 × 720 CSS px (notebook se škálováním)
po široké monitory.

### Tok práce

1. **Seznam akcí** je fronta práce: karta akce nese datum, název
   (odkaz na plochu), počet souborů, stav (nezpracováno / rozpracováno
   / hotovo) a štítky, pruh až 4 náhledů rovnoměrně z celé akce (bez
   souborů k vyřazení; načítají se líně, až je karta vidět), hotovost
   a kdo akci drží („upravuje …“, vlastní zámek „otevřeno u vás“)
   a naposledy upravoval (`upravili`). **Hotovost** = u každého pole
   autoři, datum, místo počet souborů kořene (bez označených
   k vyřazení), které ho mají po zdědění vyplněné, z jejich počtu;
   počítá ji server při výpisu z `_metadata.json` a výpisu složky.
   Má-li akce zjištěné osoby a stav *obličeje rozpoznány*, hotovost
   uvádí i osoby: pojmenované ze všech neskrytých (`osoby 4/6`); při
   nepojmenovaných karta nabídne archiváři a adminovi odkaz na nástroj
   pojmenování osob (otevře plochu akce rovnou s nástrojem).
   Nezpracovaná akce místo hotovosti nabízí zahájení zpracování.
   Dokončená akce, jejímž souborům chybí autoři, datum nebo místo,
   nebo která má podle posledního zjištění nepojmenované osoby, má
   štítek „nekompletní“, upravená po exportu „změněno po exportu“;
   akce s nálezem kontroly (viz Kontrola akce) „k vyřešení“.
   Karty jsou **dlaždice** (náhledy 2 × 2, souhrnný pruh hotovosti)
   nebo **řádky** (pruh hotovosti pro každé pole); přepínač si pamatuje
   prohlížeč. **Filtry** s počty: Vše, Moje rozpracované (rozpracovaná,
   nebo dokončená se změnami po exportu, kterou uživatel ukládal nebo
   drží jeho zámek), K dokončení (rozpracovaná bez chybějících údajů
   a dokončená se změnami po exportu), Nezpracované. **Hledání**
   v názvu ignoruje diakritiku, velikost písmen a koncové samohlásky
   slov („stezky drahanska“ najde „Stezky Drahanskou“). **Řazení**
   podle data akce (výchozí, sestupně), hotovosti (nejméně hotové
   nahoře, nezpracované na konci) nebo poslední úpravy (bez záznamu na
   konci). Filtr, hledání a řazení jsou v adrese seznamu
   (`#/?filtr=…&hledat=…&razeni=…`), takže přežijí návrat z plochy
   a jdou poslat odkazem. Nové fotky a videa se do archivu dostanou
   **importem** (viz Import) do nové nebo stávající akce.
2. **Při prvním otevření akce bez `_metadata.json` průvodce:** úklid
   (podsložky, RAW; potvrzení načte soubory kořene) → údaje akce
   (předvyplněné z názvu složky a dat fotek) → skupiny a autoři.
   Průvodce provede vším povinným; údaje jednotlivých souborů se
   doplňují na ploše. Krok skupiny a autoři ukáže mřížku náhledů po
   skupinách s úpravou skupin (přejmenovat, sloučit, nová skupina
   z výběru, přesun) a u každé skupiny pole autorů; nad skupinami
   jdou zadat i autoři celé akce: skupiny bez vlastních autorů je
   zdědí (fotila-li celou akci stejná parta, stačí je zadat jednou).
   Existuje-li k akci návrh skupin z importu, krok použije jeho
   skupiny (i s autory) a přiřazení pro soubory v kořeni, které návrh
   uvádí, a autory celé akce z návrhu; ostatní soubory dostanou
   automatický návrh. Prvním uložením `_metadata.json` se návrh smaže.
   Akce založená importem `_metadata.json` má, průvodce ji přeskočí.
3. **Pak pracovní plocha** (i při každém dalším otevření): vlevo
   navigátor akce, uprostřed mřížka náhledů po skupinách, vpravo
   formulář podle výběru — nic vybráno = akce, skupina vybraná
   v navigátoru = skupina, vybrané soubory = soubory. Zděděné
   hodnoty jsou ve formuláři vidět a jdou přepsat. Každé pole má
   barevný proužek a štítek zdroje hodnoty: „z akce“, „ze skupiny“,
   „z místa“, „rozdílné“ (různé hodnoty ve výběru) nebo „zadáno“.
   Zadaná hodnota skupiny nebo souborů má tlačítko „vrátit na
   zděděné“; to hodnotu z dané úrovně smaže, stejně jako vyprázdnění
   pole.

   **Navigátor akce** (sloupec vlevo, posouvá se sám) má nahoře řádek
   Akce a pod ním řádek pro každý oddíl mřížky (skupinu, nebo den)
   v pořadí mřížky; soubory bez skupiny jsou posledním oddílem „Bez
   skupiny“, soubory bez data „Bez data“. Řádek oddílu ukazuje název,
   počet souborů, pruh autorů v poměru jejich souborů (nejvýš tři
   barevně, ostatní šedě, bez autorů šrafovaně; titulek uvádí jména
   a počty) a ikonky chybějících údajů s počtem: soubory bez autorů,
   bez data, bez místa (jen má-li akce víc míst) a podle data i bez
   skupiny; skupina bez autorů má místo počtu zvýrazněné „bez autorů“.
   Řádek Akce ukazuje chybějící název či data akce a místa, o jejichž
   souřadnicích není rozhodnuto, a ikonu osoby s počtem nepojmenovaných
   osob podle posledního zjištění („2 nepojmenované osoby“); klik na
   něj otevře archiváři a adminovi nástroj pojmenování osob, ostatním
   údaj jen ukazuje. Soubory k vyřazení se nepočítají.
   Klik na řádek Akce zruší výběr, na skupinu vybere skupinu, na den
   („Bez data“, „Bez skupiny“) jeho soubory, a mřížka na oddíl skočí
   i s předělem nad ním. Klik na chybějící údaj vybere dotčené soubory
   (u místa navíc otevře volbu souřadnic), funguje i jen ke čtení.
   Oddíly, které jsou v mřížce vidět, mají v navigátoru okraj.
   Dlaždici (nebo celý výběr, je-li dlaždice vybraná) jde **přetáhnout
   na řádek skupiny** a přesunout tak do skupiny; ostatní řádky tažení
   nepřijmou, bez zámku akce tažení nejde.

   Lišta akce pod hlavičkou nese název akce, přepínače mřížka/lupa
   (ikony) a zobrazení, velikost náhledů, Importovat a Dokončit akci,
   nálezy kontroly akce a počet souborů k vyřazení. Nevejdou-li se,
   zalomí se na další řádek lišty. Posuvník **Náhledy** mění velikost
   dlaždic mřížky (80–300 px, pamatuje si ho prohlížeč). Panel formuláře jde
   **sbalit** úchytem na jeho levém okraji nebo klávesou `P` (mimo
   textové pole); mřížka nebo lupa pak zabere celou šířku, stav si
   pamatuje prohlížeč. Na širokém monitoru má panel nejvýš 420 px
   a šířku využije mřížka.

   Přepínač **Po skupinách / Podle data** (pamatuje si ho prohlížeč,
   platí pro mřížku i lupu) ukáže místo skupin všechny soubory akce
   v jednom pořadí podle data pořízení, s předěly po dnech
   („út 28. 4. 2026“ v navigátoru) a soubory bez data na konci.
   Mřížka plochy nemá hlavičky oddílů, jen předěly. Dlaždice nemá
   popisek: dole nese pruh podle výsledných autorů (každá osoba akce
   má svou barvu, pruh se dělí na úseky v barvách autorů, nejvýš tři,
   další jako šedý úsek; bez autorů šrafovaný, k vyřazení žádný),
   v rohu ikonu bez data, bez místa, nebo k vyřazení, a název, datum
   a příjmení autorů (u víc než tří „+N“) ukáže překryv při najetí myší
   nebo fokusu z klávesnice. Průvodce je vždy po skupinách, s hlavičkami
   a popisky a bez značek.

   Datum pořízení má dva vstupy s nativním výběrem prohlížeče: den
   a čas (se sekundami). Prázdný čas = hodnota jen s datem (WhatsApp);
   smazání času ponechá den, smazání dne smaže celé datum, čas bez dne
   zadat nejde. U výběru změna dne přepíše každému souboru den a jeho
   čas zůstane, změna času přepíše čas a den zůstane; rozdílnou část
   vstup neukazuje a vedle stojí „rozdílné hodnoty“.

   Místo mřížky jde přepnout na **lupu** (Enter, dvojklik na dlaždici
   nebo přepínač; zpět Esc): velká fotka nebo přehrávač videa a pod ní
   filmový pás celé akce s oddíly (skupinami, nebo dny) oddělenými
   předělem. Šipky přepínají aktuální soubor a vyberou jen jej,
   Shift+šipky výběr rozšiřují; klik do pásu vybírá jako v mřížce.
   Výběr i formulář jsou s mřížkou společné. Navigátor v lupě slouží
   ke skoku: klik na oddíl udělá jeho první soubor aktuálním a jediným
   vybraným; okraj má oddíl aktuálního souboru.

   **Vyřazení:** klávesa Del nebo tlačítko „Vyřadit“ v panelu označí
   vybrané soubory k vyřazení (jsou-li už všechny označené, označení
   zruší). Označené dlaždice zůstávají na místě, zašedlé a přeškrtnuté.
   Lišta ukazuje počet souborů k vyřazení a nálezy kontroly akce.
   Tlačítko **Uklidit…** (je-li co vyřadit nebo napravit, včetně
   poškozených souborů) uloží změny
   a ukáže plán: označené do `k_odstraneni.ignored`, ostatní soubory do
   `ostatni.ignored`, RAWy do `RAW.ignored` a u podsložek volbu
   přesunout/ponechat jako v průvodci — podsložka bez volby zůstane.
   Sekce **Poškozené soubory** je tabulka poškozených souborů kořene
   (náhled, stav a důvod) se dvěma výlučnými sloupci: **Vyřadit**
   (přesune se spolu s ostatními do `k_odstraneni.ignored`) a **V
   pořádku** (`overeno`, kontrola se mýlí); hlavička sloupce označí
   všechny. Výchozí je uložený stav, soubor bez volby zůstane, jak je.
   Volby se zapíší až tlačítkem; bez přesunů jen „Uložit“. Soubor už
   označený k vyřazení je šedý (zrušit jde na dlaždici); ve vývojovém
   režimu je sloupec Vyřadit vypnutý.
   V produkčním režimu plán po potvrzení provede (viz Podsložky a RAW),
   ve vývojovém ho jen ukáže.
4. **Dokončení akce:** tlačítko Dokončit akci na ploše uloží změny
   a otevře **kontrolní stránku** (`#/akce/<název>/dokonceni`, jde
   otevřít i odkazem). Ta ukáže kontroly se stavem v pořádku /
   k vyřešení: údaje akce, chybějící údaje souborů (skupiny a soubory
   bez autorů, soubory bez data, bez skupiny, bez místa, místa bez
   souřadnic), nálezy kontroly akce, poškozené soubory bez rozhodnutí,
   soubory k vyřazení ještě v kořeni a stav exportu (kontrola
   nanečisto; ve vývojovém režimu i kam jdou sidecary). Každá kontrola
   k vyřešení má odkaz „Opravit na ploše“: otevře plochu a vybere
   dotčené soubory nebo skupinu, otevře volbu souřadnic, výpis názvů
   nebo Uklidit…; zpět vede tlačítko Dokončit akci. Při kontrolách
   k vyřešení nese tlačítko stránky text „Přesto dokončit“ (to je
   výslovné potvrzení), jinak „Dokončit“. Stránka sdílí s plochou
   stav akce i zámek (přechod zámek neuvolní); bez zámku je jen ke
   čtení s uvedeným držitelem a tlačítko je neaktivní. Nezpracovanou
   akci přesměruje na průvodce. Dokončení zapíše sidecary, v produkčním
   režimu odebere složce akce příponu `.ignored` (zveřejní ji pro
   Immich, který ji tak poprvé uvidí rovnou se sidecary) a nastaví
   `dokonceno`. Selže-li zápis některého sidecaru nebo přejmenování
   složky (např. soubor v ní drží jiný počítač), akce dokončená
   není a kontrolní stránka chybu ukáže. Po dokončení stránka ukáže
   počty zapsaných, nezměněných a selhaných sidecarů, chyby po souborech
   a odkaz zpět na seznam akcí. Dokončit akci je jediný zápis sidecarů
   z plochy: po úpravě dokončené akce se dokončí znovu. `dokonceno` je
   datum prvního dokončení, opakované dokončení ho nemění; selže-li
   přitom export, akce zůstane dokončená a stránka chybu ukáže. U
   tlačítka plocha ukazuje, kolik sidecarů je neaktuálních, a po úpravě
   „neexportované změny“; seznam akcí u dokončené akce upravené po
   exportu uvede „změněno po exportu“. U dokončené akce je Dokončit
   akci neaktivní, dokud není co dokončovat (neuložené či neexportované
   změny, neaktuální sidecary, selhaný export).

Našeptávání a kontrola jmen viz výše.

### Import

Průvodce importem se spouští ze seznamu akcí (bez cíle) nebo z plochy
akce (s ní jako předvybraným cílem). Kroky: soubory → přehled → cíl →
plán → skupiny a autoři → výsledek. Plán je před popisem, aby se
popisovalo jen to, co se opravdu přenese.

- **Soubory:** jednotlivé soubory i celá složka, výběrem nebo
  přetažením; soubory z podsložek se berou, jako by ležely v jedné
  úrovni. Nahrávají se po jednom (2–3 souběžně, s průběhem) do
  `.work/import/<id>/`, ne do archivu; zavření stránky archiv nezmění.
  Adresa `#/import/<id>` přežije reload. Limit 20 GB na soubor, server
  před nahráním kontroluje volné místo. Import patří jménu uživatele
  (porovnání jako u návrhů jmen; s přihlášením z relace, jméno
  v požadavku server ignoruje), ne záložce: seznam akcí ukazuje
  „Moje rozpracované importy“ (založeno, počet a velikost souborů,
  zamýšlený cíl, poslední aktivita) s tlačítky Pokračovat a Zahodit.
  Cizí import není vidět a jeho adresa hlásí „nenalezen“.

  Admin a archivář mohou místo nahrání zvolit **složku
  v `přetřídit`** („ze složky přetřídit“, nebo ze stránky *Přetřídit*,
  viz níže). Nic se
  nenahrává, průvodce rovnou ukáže přehled. Jednotkou je celá složka
  první úrovně; její podsložky se berou jako u nahrané složky
  (zploštění, skupiny podle podsložek, RAWy do `RAW.ignored/`),
  podsložky `*.ignored` se i s obsahem přeskočí. Seznam souborů se
  sestavuje pokaždé z aktuálního obsahu složky. Opakované zvolení
  téže složky otevře rozpracovaný import uživatele.
- **Přehled:** počty fotek, videí a RAWů, rozsah dat z EXIF (WhatsApp
  z názvu), přístroje, nepodporované soubory. Přijímají se média
  aplikace (jpg, jpeg, png, mp4, mov) a RAWy; `Thumbs.db` se tiše
  přeskočí, ostatní se vypíšou a nepřenesou.

  Po zobrazení přehledu se soubory **zkontrolují** (viz [Poškozené
  soubory](#poškozené-soubory)): stream s průběhem po souborech
  a bajtech, výsledky z cache hned; Pokračovat jde až po doběhnutí.
  Přehled vypíše podezřelé a nečitelné soubory s důvodem. Nečitelný se
  nepřenese nikdy, podezřelý jen se zaškrtnutým „přesto importovat“
  (volba se uloží k importu). Oba jde po potvrzení dialogem (jméno
  a důvod) **smazat**: nahraný z pracovního adresáře, soubor zdroje
  v `přetřídit` jen v produkčním režimu, pod zámkem zdroje (jako
  provedení). Smazat jde jen soubor, který kontrola označila jako
  poškozený a který se od ní nezměnil; smazání se zapíše do logu
  serveru.

  Samostatně se chovají fotky s **odebranou polohou**: Android při
  předání fotky prohlížeči nebo mailem vynuluje GPS blok (ověřeno na
  Pixel 8a, Android 17, 2026-10-09, v Chrome i Firefoxu — `exiftool`
  pak vrátí `GPSVersionID 0 0 0 0` a prázdné souřadnice). Poloha je
  pro archiv zásadní, taková fotka se nepřinese žádnou cestou
  importu, volba „přesto importovat“ se pro ni nenabízí a povolení
  podezřelých ji neuvolní. Přehled ji vypíše v bloku „Odebraná
  poloha“ bez tlačítka Smazat, plán a výsledek ji uvedou mezi
  nepřenesenými s důvodem „telefon odebral polohu“ (originál zůstane
  v pracovním adresáři nebo ve zdroji `přetřídit`). Uživatel má
  předat originál jinou cestou — kabelem nebo FileSenderem
  z počítače. Videa se zatím neřeší (chování Androidu
  u MP4/MOV není změřené). Pokračovat zůstává dostupné, pokud zbývá
  aspoň jedno přenositelné médium.
- **Cíl:** stávající akce, nebo nová — datum se předvyplní nejstarším
  dnem z EXIF, název doplní uživatel; složka `YYYY-MM-DD název` bez
  `/` a `\`, nekončí na `.ignored` a nesmí existovat s příponou
  `.ignored` ani bez ní (bez ohledu na velikost písmen; jinak průvodce
  nabídne zvolit ji jako stávající). Nová akce vznikne skrytá před
  Immichem (`název.ignored`, viz [Archiv](#archiv)). U dokončené akce
  upozorní, že Immich nové soubory uvidí hned a skupiny a autoři
  z importu se do sidecarů dostanou až novým dokončením akce.

  U nové akce krok sbírá i **údaje akce**: název (předvyplněný názvem
  složky bez data a jdoucí s ním, dokud ho uživatel nezmění), datum
  od–do (nejstarší a nejnovější den médií z přehledu), popis, místa
  a účastníky. Pokračovat jde jen s názvem a datem od.
- **Plán:** média do kořene, RAWy do `RAW.ignored/`. Poškozené
  soubory (nečitelné a nepovolené podezřelé) se nepřenesou a plán je
  uvede zvlášť s důvodem; soubor změněný od kontroly se zkontroluje
  znovu. Jméno, které v cíli existuje nebo ho má víc souborů výběru,
  se blokuje.
  Duplicita (stejný sha256 jako soubor v kořeni cílové akce nebo jiný
  soubor výběru) se přeskočí; hashe akce se počítají jen u souborů
  shodné velikosti a cachují se v `.work/cache/sha256/`. Na SMB to
  může trvat minuty, proto server posílá průběh porovnání (stream
  NDJSON, po souboru a u velkých po 64 MB; hashe z cache jsou hned
  hotové) a tlačítko je do konce výpočtu zablokované. Zvolený cíl se
  uloží k importu a po návratu se předvyplní. Plán skupiny neukazuje;
  nabízí jen pokračování ke skupinám a autorům.
- **Skupiny a autoři:** mřížka náhledů přenášených fotek a videí
  (náhledy nahraných souborů i souborů zdroje v `přetřídit`, nic se
  nezapisuje) a panel jako v průvodci akce. Nahoře **výchozí
  rozdělení** (RAWy skupinu nedostanou): *podle podsložek* (jen má-li
  výběr podsložky; skupina = podsložka první úrovně pod nejdelší
  společnou složkou výběru, soubory přímo v ní dostanou skupinu
  pojmenovanou po ní), *jedna nová skupina* (název předvyplněný
  kořenem výběru, jinak `Import YYYY-MM-DD`), *automaticky* (přístroj
  a vzor názvu jako u nové akce), *bez skupiny*, nebo *zařadit do
  skupiny …* (jen akce, jejíž `_metadata.json` skupiny má).
  Předvolba: podsložky → podle podsložek; jinak nová akce a akce bez
  `_metadata.json` → automaticky, ostatní → jedna nová skupina.
  Výchozí rozdělení počítá server z posledního plánu bez nového
  porovnání; změna po ručních úpravách nebo autorech skupin se ptá.
  Pod tím úpravy skupin (přejmenovat, sloučit, nová skupina z výběru,
  přesun), autoři celé akce a u každé skupiny náhledy a autoři.
  Nové skupiny se s existujícími (v `_metadata.json` nebo návrhu)
  samy nesloučí ani při shodě: název nové dostane případně pořadové
  číslo a u každé jde zvolit „nová skupina“ nebo „připojit ke skupině
  …“, existující se shodným názvem (bez diakritiky a velikosti písmen)
  nebo přístrojem nahoře jako shoda; připojená ukazuje autory
  existující skupiny. Existující skupiny cíle jsou jen ke čtení.
  Importujícího aplikace jako autora nepředvyplňuje.

  Údaje akce, volba rozdělení, skupiny, přiřazení, připojení a autoři
  (**popis importu**) se průběžně ukládají do `import.json` (ne do
  archivu) a po návratu se předvyplní. Po novém plánu média, která se
  už nepřenesou, ze skupin vypadnou, nově přenášená dostanou skupinu
  z výchozího rozdělení a ruční úpravy ostatních zůstanou. Má-li
  některá skupina po zdědění prázdné autory, tlačítko importu na to
  upozorní a import provede až druhé kliknutí; jinak druhé kliknutí
  jen potvrzuje zápis do archivu. „Co by se zapsalo“ ukáže souhrn
  popisu (ve vývojovém režimu místo provedení).
- **Provedení** (jen produkční režim, ve vývojovém se plán a krok
  skupin jen ukážou):
  plán se sestaví znovu, soubor se zkopíruje do dočasného
  `.import-*.tmp` v cílové složce, dostane čas změny originálu
  a přejmenuje se, jen pokud cíl pořád neexistuje. Selhání jednoho
  souboru ostatní nezastaví. Import do stávající akce vyžaduje zámek
  akce; nová akce vznikne jen, pokud složka mezitím nevznikla, a zámek
  na ni dostane relace importu. Průběh jde streamem (NDJSON) po
  souborech a u velkých po 64 MB; ukazatel se posouvá podle bajtů.
  Přenesený soubor zmizí z pracovního adresáře hned. Zavření stránky
  kopírování zastaví nejpozději po dalších 64 MB: rozkopírovaný
  dočasný soubor se smaže, přenesené zůstanou v archivu, zbytek
  v pracovním adresáři. Když dočasný soubor smazat nejde (výpadek
  SMB), smaže ho další import do téže akce: před kopírováním odstraní
  `.import-*.tmp` starší než hodinu v kořeni a v `RAW.ignored/`
  a uvede je ve výsledku. Po přenosu (kopii i přesunu) server porovná
  velikost souboru v cíli s originálem; nesoulad je chyba souboru ve
  výsledku a soubor zůstane v archivu. Obsah se zpětně nečte: kopie
  porovnává sha256 přenášených dat a SMB/TCP přenos hlídá sám; vada
  z issue #10 (vynulované bloky) vzniká na kartě, ne přenosem.

  Po přenosu server zapíše popis z `import.json` jen pro skutečně
  přenesená média; blokované, duplicitní a selhané záznam nedostanou
  a skupina bez přeneseného souboru nevznikne. **Nová akce:**
  `_metadata.json` vznikne rovnou s údaji akce z kroku cíl (včetně
  autorů celé akce), skupinami a přenesenými soubory s technickými
  údaji; akce je *rozpracovaná* a otevře se rovnou plocha. **Akce
  s `_metadata.json`:** přenesené soubory (s technickými údaji, jako
  při otevření akce), nové skupiny s autory, připojení a přiřazení
  jdou do `_metadata.json` pod zámkem importu; autoři celé akce jen
  při změně proti stavu v době plánu; stávající záznamy a skupiny se
  nemění. **Akce bez něj:** `_metadata.json` nevznikne, skupiny
  s autory, přiřazení a autoři akce jdou do návrhu
  `.work/navrhy-skupin/<akce>.json` (i v produkčním režimu; další
  import ho doplní) a použije ho průvodce akce. Když zápis selže
  (např. `_metadata.json` mezitím upravený mimo aplikaci), soubory
  zůstanou v archivu a výsledek uvede, že jsou bez skupiny a autorů.
- **Import ze složky `přetřídit`:** provedení soubory **přesouvá**
  (přejmenování na stejném svazku, obsah i čas změny zůstanou), nic
  nekopíruje. Měřítkem je poslední plán (snímek cest, velikostí a časů
  změny v `import.json`; provedení bez něj server odmítne a snímek
  spotřebuje): soubor, který od plánu ze zdroje zmizel, je selhaný,
  změněný blokovaný a přibylý se nepřesune a výsledek ho uvede zvlášť.
  Přesun nepřepíše existující soubor; přesun na jiný svazek je
  selhání souboru. Duplicity, blokované, poškozené a nepodporované
  soubory zůstanou ve zdroji. Kontrola přečte každý soubor zdroje
  jednou a tentýž průchod uloží sha256 do `.work/cache/sha256/`, takže
  plán zdroj znovu nečte; jinak by se sha256 počítal jen u souborů,
  jejichž velikost má soubor v kořeni cílové akce nebo jiný soubor
  výběru. Po provedení server smaže odspodu
  podsložky a nakonec zdrojovou složku, jsou-li prázdné nebo jen
  s `Thumbs.db`; složky `*.ignored` nechá. Výsledek uvede, co ve
  zdroji zůstalo a zda složka zanikla. Import bez zbylých podporovaných
  souborů ve zdroji se zruší; zahození importu zdroj nemění. Varianty
  se stejným jménem (např. `Procházka 60/JPEG orig`) se navzájem
  zablokují a nepřesune se nic z nich: podsložku přejmenujte na
  `.ignored` a import zopakujte. Ve vývojovém režimu přehled, plán
  i krok skupin fungují, provedení ne.
- **Stránka Přetřídit** (odkaz ze seznamu akcí): složky první úrovně
  `přetřídit` (bez `.ignored`) s počty fotek, videí, RAWů a ostatních
  souborů, podsložkami, rozsahem dat z EXIF, datem z názvu
  (`d.m.yyyy`, `yyyy_mm_dd`, `yyyy_m_d`, `dd_mm_yyyy`; samotný rok jen
  informativně) a navrženou akcí `YYYY-MM-DD název` (datum nejstarší
  den z EXIF, jinak z názvu, jinak ho doplní uživatel; název = název
  složky). Výpis přijde hned, údaje z EXIF se doplňují po složkách
  (stream); EXIF se cachuje podle jména, velikosti a času změny.
  Složka s rozpracovaným importem uživatele je zvýrazněná. Kliknutí
  založí (nebo obnoví) import s navrženou novou akcí jako cílem
  a otevře přehled.
- **Výsledek:** přenesené, blokované, duplicitní, poškozené a selhané
  soubory; přenesené zmizí z pracovního adresáře, ostatní tam zůstanou,
  dokud uživatel import nezahodí. Importy neaktivní přes 7 dní server smaže
  při startu. Průvodce nabídne otevřít akci; nové soubory jsou mezi
  „novými od posledního otevření“, metadata se doplňují běžně.

### Immich

Stránka **Nastavení** (odkaz v hlavičce) drží adresu serveru Immich,
API klíč a výběr knihovny archivu. Klíč potřebuje čtení osob, assetů
a obličejů (`person.read`, `asset.read`, `face.read`, `asset.view`);
pro alba akcí, sken knihovny, stav rozpoznávání a nástroj pojmenování
osob i práva k zápisu a čtení front (`person.update`, `person.merge`,
`album.read`, `album.create`, `albumAsset.create`, `albumAsset.delete`,
`library.read`, `library.update`, `queue.read`) — klíč s `all` kryje
vše. Sken knihovny a fronty jsou v Immichi jen pro admina, klíč musí
patřit uživateli s rolí admin. Nastavení se ukládá do
`.work/immich.json` (práva 0600), nikdy do archivu; klíč se do
prohlížeče nevrací (jen „klíč nastaven (…W4No)“) a změna adresy
vyžaduje zadat ho znovu; výběr knihovny se uloží i bez nového klíče
(`knihovna` v `immich.json`, nabídne ho `GET /api/immich/knihovny`).
Otestovat ověří verzi, osoby a čtení obličejů a navíc porovná
oprávnění klíče: chybějící oprávnění, klíč uživatele bez role admin
(odpověď `GET /api/libraries` je 403) a nevybranou knihovnu vypíše
jako varování — čtení obličejů funguje i bez nich, alba akcí, sken
a nástroj pojmenování ne. Nastavení (i synchronizaci na požádání)
smí jen admin.

**Alba dokončených akcí** vymezují fotky akce v Immichi (pro nástroj
pojmenování osob i pro prohlížení). Po dokončení (odebrání přípony
`.ignored`) spustí server hlídače na pozadí: spustí sken knihovny
vybrané v nastavení a pak co 20 s zjišťuje, zda Immich zná všechny
soubory akce; jakmile ano, založí album pojmenované jako akce a později
do něj doplňuje přibývající assety a cizí z alba odebírá. Album ani
asset se nikdy nemažou. Pravidelná synchronizace totéž opakuje pro
každou dokončenou akci (bez skenu), takže album dorovná i po restartu
serveru nebo smazání alba v Immichi; hlídač je jen zrychlení. Vazba
akce → id alba je v `.work/immich-alba.json`; při ztrátě souboru se
album dohledá podle názvu, takže nevznikne duplicitní.

**Stav akce v Immichi** vidí každý přihlášený uživatel na kartě akce
a na ploše akce; bez nastaveného Immiche se nezobrazuje. Hlídač
i synchronizace zapisují do `.work/immich-alba.json` stavy:
`nacitani` („Immich načítá fotky“), `rozpoznavani` („Rozpoznávání
obličejů probíhá“), `rozpoznano` („Obličeje rozpoznány (datum)“)
a `nenalezeno` („Immich fotky akce zatím nenašel“ — hlídač vypršel
a Immich žádné soubory akce nezná). Zobrazení se Immiche neptá:
výpis akcí čte stav ze souboru a plocha jej během načítání
a rozpoznávání obnovuje přes `GET /api/akce/<název>/immich` (ten čte
taky jen soubor; není pod `/api/immich`, který je jen pro admina).
Rozpoznání se pozná jen nepřímo: Immich nemá příznak „obličeje
zpracovány“ — hotovo je, když mají všechny fotky alba zmenšeninu
(`thumbhash`; videa se nepočítají) a fronty `faceDetection`
i `facialRecognition` nemají aktivní ani čekající úlohy. Chyba spojení
nebo chybějící oprávnění stav nemění: zapíše se do `chyba` a vypíše
na stránce Nastavení (jen admin).

**Synchronizace obličejů** běží v serveru po startu, pak každých
15 minut a na tlačítko Načíst osoby:

- Z Immiche se načtou pojmenované osoby (i skryté), jejich assety
  a obličeje na nich; nepojmenované obličeje se ignorují.
- Asset se páruje se souborem podle posledních dvou částí cesty
  (složka akce, soubor), kořen archivu v Immichi se nenastavuje.
  Zpracují se jen akce, které už mají `_metadata.json`. Nedokončenou
  akci Immich nevidí (přípona `.ignored`), obličeje k ní přibudou až
  po dokončení.
- `oblast` se počítá z obdélníku a rozměru, ke kterému ho Immich
  vztahuje (zmenšenina už otočené fotky), takže na měřítku nezáleží.
- `_metadata.json` se přepíše, jen když se obličeje některého souboru
  změnily; soubor bez pojmenovaného obličeje `obliceje` ztratí.
  Synchronizace při zápisu drží zámek akce („Immich (synchronizace)“);
  akci otevřenou uživatelem se zámkem přeskočí a zkusí příště.
- Selže-li kterýkoli dotaz, běh nic nezapíše (neúplná data by obličeje
  mazala). Nastavení ukazuje poslední běh (změněné a přeskočené akce,
  chybu) a čas posledního úspěšného.
- Odpovídal-li záznam o exportu verzi před zápisem, posune se na novou:
  obličeje běžné sidecary nemění.

Ve formuláři souboru jsou osoby jen pro čtení (zašedlá jména
„z Immiche“, u výběru všech souborů); skupina ani akce pole osob nemají.
Bez nastavení pole uvádí „Immich není napojen“. Klient obličeje při
ukládání neposílá, server je převezme z uložené verze.

Přejmenování nebo přesun souboru je v Immichi nový asset bez obličejů;
záloha v `_metadata.json` jde s přejmenováním a obnoví se exportem pro
obnovu.

**Nástroj pojmenování osob** (smí admin a archivář, ostatním server
vrátí 403) prochází po jedné nepojmenované a neskryté osobě Immiche
s obličejem na fotce v albu akce, seřazené podle počtu obličejů.
Otevírá se jako překryv nad plochou akce (rozmazané pozadí) tlačítkem
v liště akce, klikem na nepojmenované osoby v navigátoru a z karty
odkazem (`#osoby` v adrese plochy); u stavu *rozpoznávání obličejů*
upozorní, že další osoby mohou přibýt. Zavření vrátí na plochu
a odstraní `#osoby` z adresy.
U každé ukáže až 3 výřezy z různých fotek (zmenšeniny proxyuje
server — klíč Immiche neopouští server) s metadaty z Immiche a po
zdědění i ze souboru archivu. Osobu lze pojmenovat (do Immiche se
zapisuje kanonický tvar `Příjmení, Jméno`, u stejnojmenné existující
osoby nabídne server sloučení), skrýt, nebo odložit; odložené osoby
jsou per uživatel a akce v `.work/pojmenovani.json`, nové kolo je
vymaže. Klávesy fungují i v poli jména: Enter uloží, PageDown odloží,
Alt+Delete skryje, Esc zavře; další volba se neodešle, dokud
předchozí zápis neskončil. Nástroj zapisuje jen do Immiche (`PUT
/api/people`, `POST /api/people/merge`), `_metadata.json` nemění
a nevyžaduje zámek akce. Po každé akci přepočítá počty osob
do `.work/immich-osoby.json`; zavření nástroje po změně spustí
synchronizaci, takže se jména brzy objeví v `obliceje`.

### Ukládání a export

- `_metadata.json` se ukládá průběžně, atomicky (dočasný soubor
  a přejmenování), v produkčním režimu do složky akce, ve vývojovém do
  `.work/metadata/<akce>/`. Rozpracovaná metadata z `.work` převezme do
  archivu jednorázově `python -m fotoarchiv prevzit` (jen u akcí, které
  `_metadata.json` v archivu ještě nemají).
- XMP sidecary se zapisují při dokončení akce (i opakovaném)
  a dávkově `python -m fotoarchiv exportovat [AKCE]` (bez akce všechny
  s `_metadata.json`; zámky nekontroluje). **Přepisují se
  jen změněné:** obsah sidecaru se generuje deterministicky (bez
  časových razítek) a porovná s obsahem na disku; zapíše se atomicky,
  jen když chybí nebo se liší. Sidecar vznikne jen k souborům se
  záznamem, v kořeni a neoznačeným k vyřazení; jiné `.xmp` se nemažou.
  Ve vývojovém režimu jdou sidecary do `.work/xmp/<akce>/`.
- Po exportu bez chyb se do `.work/export/<akce>.json` zapíše verze
  (sha256) `_metadata.json`, ze které export vznikl. Liší-li se od
  aktuální, akce má neexportované změny; bez záznamu je stav neznámý.
  Do archivu ani do `_metadata.json` se nic z toho nezapisuje.
- Před uložením `_metadata.json` aplikace ověří, že ho mezitím nezměnil
  někdo jiný; jinak uložení odmítne a nabídne znovunačtení.

### Souběh

Aplikace běží jako jeden sdílený server (cheroot); zámek otevřené akce drží
server v paměti (kdo, relace prohlížeče, od kdy, poslední heartbeat).
Proto **server smí běžet jen jako jeden proces** (vlákna ano — výchozí 32,
víc workerů ne). Do archivu se žádný soubor zámku nezapisuje.

- Při otevření akce klient požádá o zámek. Drží-li akci někdo jiný,
  otevře ji jen ke čtení s upozorněním „Akci upravuje …“.
- Klient zámek obnovuje heartbeatem (~1 min), dokud je akce otevřená;
  při odchodu z akce nebo zavření stránky ho uvolní.
- Zámek bez heartbeatu ~5 min (podle hodin serveru) je opuštěný a jde
  převzít. Kdo o zámek přijde, přepne se jen ke čtení.
- Uložení, provedení úklidu a import do stávající akce bez zámku
  server odmítne; kontrola verze `_metadata.json` platí i pro
  držitele zámku.
- Restart serveru zámky zahodí; klient je při dalším heartbeatu získá
  znovu, pokud je akce volná.
- „Kdo“ je kanonické jméno přihlášeného uživatele (jméno poslané
  klientem server ignoruje); jen bez přihlášení (`--bez-prihlaseni`)
  jméno zadané v prohlížeči.
- Bez oprávnění k úpravě (viz Přihlášení) klient zámek nežádá a server
  ho odmítne; přijde-li uživatel o oprávnění během držení zámku, server
  odmítne i jeho další změny.
- Admin a archivář mohou zámek jiné relace vynuceně uvolnit (opuštěná rozdělaná
  práce, tlačítko u hlášky „Akci upravuje …“). Původní držitel při
  dalším heartbeatu přejde jen ke čtení s upozorněním, kdo zámek
  uvolnil; jeho neuložené změny server odmítne.
- Odhlášení uvolní zámky, které relace přihlášení drží.
- Rozpracovaný import patří jménu, ne záložce; vidí ho jen jeho
  vlastník. Během provedení importu server odmítne nahrávání,
  zahození i další provedení téhož importu (příznak v paměti); nahrávat
  z víc záložek najednou lze. Průvodce v jiné záložce upozorní, že se
  import právě nahrává nebo kopíruje jinde.
- Drží-li zámek akce jiná záložka téhož jména, hláška místo „Akci
  upravuje …“ radí zavřít původní záložku. Zámek nové akce, který
  server vzal pro provedení importu, se při přerušení provedení uvolní.
- Provedení importu ze složky `přetřídit` drží navíc zámek zdroje
  `přetřídit/<složka>` (vlastní relace vedle zámku cílové akce,
  heartbeat po přesunutém souboru). Jiné provedení importu téže složky
  server odmítne s uvedením, kdo ji přesouvá; po skončení nebo
  přerušení se zámek uvolní.

Metadata (JPG, mp4) čte `exiftool`. Náhledy
(320 px do mřížky, 1600 px do lupy) se cachují lokálně mimo archiv —
archiv leží na SMB; lupa si sousední fotky načítá předem. Videa se do
lupy posílají přímo z archivu, jen ke čtení.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
