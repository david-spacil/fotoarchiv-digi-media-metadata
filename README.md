# fotoarchiv-digi-media-metadata

Průvodce obohacením metadat digitální fotodokumentace ARÚB
(`FOTOARCHIV/fotoarchiv_fotodokumentace_digitalni_ARUB`). Lokální webová
aplikace s náhledy, ve které se fotkám a videím přiřazují metadata
jednotlivě nebo po skupinách.

Stav: **prototyp** se dvěma režimy. Výchozí vývojový archiv jen čte
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

Aplikace běží na <http://127.0.0.1:5000>. Bez dalších přepínačů je to
vývojový režim: archiv se jen čte, metadata a cache jdou do `.work/`.
Server spouštět jen jednou (zámky akcí jsou v paměti procesu).
Přístup vyžaduje přihlášení (viz Přihlášení níže).

Volitelné přepínače:

- `--zapis-do-archivu` — produkční režim, `_metadata.json` se ukládá do
  složek akcí a provádí se úklid a import.
- `--bez-prihlaseni` — vývojový režim bez přihlášení: každý je admin
  a jméno u zámku se zadává v prohlížeči. S `--zapis-do-archivu` server
  odmítne start.
- `--https` — cookie relace jen přes HTTPS (za reverzní proxy s HTTPS).
- `--work CESTA` — jiný pracovní adresář než `.work`.
- `--host`, `--port` — adresa a port (výchozí `127.0.0.1:5000`).

Napojení na Immich (obličeje) a kontakt pro Nominatim (geokódování
míst) nastavuje admin v aplikaci; uloží se do `.work/immich.json`
a `.work/nominatim.json`. Zastaralý přepínač `--kontakt` server při
startu převezme do `.work/nominatim.json`, pokud ještě neexistuje.

### Přihlášení

Účty jsou lokální. Uživatele zapisuje správce ručně do
`.work/uzivatele.json` (login → kanonické jméno, volitelně e-mail
a příznak admina); aplikace ho jen čte, změna platí bez restartu
a odebraný uživatel přijde o přístup při dalším požadavku:

```json
{"spacil": {"jmeno": "Spáčil, David", "email": "…", "admin": true}}
```

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
požádání, kontakt pro Nominatim) a vynuceně uvolnit zámek akce;
ostatním server vrátí 403 a klient tyto prvky nezobrazí.

Zatím běží přes HTTP ve firemní síti (přijaté riziko): heslo a cookie
jdou sítí čitelně, přihlašovací stránka na to upozorní. Cookie je
`HttpOnly` a `SameSite=Lax`; `Secure` zapne `--https`, až bude
reverzní proxy s HTTPS.

Na Windows místo `.venv/bin/` použít `.venv\Scripts\`.

## Archiv

- Na první úrovni složky akcí `YYYY-MM-DD název`. Zpracovávají se jen
  ty; ostatní (`přetřídit`, `přednášky SKLEP TIC`) se nechávají beze
  změny. Výjimkou je generovaný index `_INDEX.html` a `_INDEX.md`
  (viz [Výstupy](#výstupy)).
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
- Přesun nikdy nepřepíše existující soubor; operace se shodou názvů se
  přeskočí a nahlásí, ostatní proběhnou a podsložka, ze které něco
  zbylo, se nesmaže. Pokud `RAW.ignored` nebo `k_odstraneni.ignored` už
  existuje, soubory se do ní přidají.
- Přesuny a přejmenování mění cesty, které by Immich bral jako nové
  assety. Proto se mají udělat před napojením archivu do Immiche.

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
    "ucastnici": ["Spáčil, David", "Kopáčová, Zuzana"]
  },
  "souradnice_mist": {
    "Vysočany": {"gps": [49.43, 16.804],
                 "popis": "Vysočany, okres Blansko, …",
                 "osm": "relation/…"},
    "u rybníka": null
  },
  "skupiny": {
    "g9": {
      "autori": ["Spáčil, David", "Kopáčová, Zuzana"],
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
      "obliceje": [{"jmeno": "Hlava, Miloš",
                    "oblast": [0.2725, 0.432, 0.041, 0.0747]}],
      "sha256": "…"
    },
    "P1503713.JPG": {"skupina": "g9", "vyradit": true}
  }
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
  se). Do XMP exportu takový soubor nejde, do lišty chybějících údajů se
  nepočítá; úklid ho přesune do `k_odstraneni.ignored` a záznam smaže.
- Originály se nemění.

## Jména osob

Žádný předem daný seznam. **Otevřený seznam návrhů** vzniká ze jmen
použitých ve všech `_metadata.json` v archivu a roste s tagováním.

- Kanonický tvar `Příjmení, Jméno`.
- Při zadání jména formulář porovná vstup se seznamem bez ohledu na
  diakritiku, velikost písmen a pořadí slov. Při shodě nabídne
  „Mysleli jste `Spáčil, David`?“ a kliknutím opravený tvar propíše do
  pole (např. pro `Spacil, David` nebo `David Spáčil`).
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
  datum (WhatsApp) zůstane bez času a zóny. GPS ve formátu XMP
  `DDD,MM.mmmmmmK` (např. `49,24.378000N`). Prázdná pole se
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
  s výjimkami `**/*.ignored/**` a nezpracovávanými složkami první úrovně
  (`přetřídit`, `přednášky SKLEP TIC`). Testovací knihovna vidí
  archiv pod `/mnt/media/fotoarchiv/…`; aplikace z ní čte jen
  pojmenované obličeje (viz Aplikace, Immich).
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
  po provedení importu, po exportu z aplikace (Exportovat, dokončení)
  a na konci `python -m fotoarchiv exportovat`, ne při uložení.
  Zapisuje se atomicky a jen při změně obsahu (bez času generování);
  selhání je jen varování. V produkčním režimu jde do kořene archivu
  s relativními odkazy, ve vývojovém do `.work/index/` s odkazy
  `file://` do archivu. `_metadata.xlsx` aplikace nemění; smazat ho je
  na člověku.

## Aplikace

Lokální webová aplikace spouštěná nad složkou archivu.

### Tok práce

1. **Seznam akcí** se stavem (nezpracováno / rozpracováno / hotovo)
   a chybějícími údaji. Dokončená akce, jejímž souborům v kořeni (kromě
   označených k vyřazení) po zdědění chybí autoři, datum nebo místo,
   má navíc štítek „nekompletní“. Nové fotky a videa se do archivu dostanou
   **importem** (viz Import) do nové nebo stávající akce.
2. **Při prvním otevření akce průvodce:** úklid (podsložky, RAW) →
   načtení a skupiny → údaje akce → autoři skupin. Průvodce provede
   vším povinným; údaje jednotlivých souborů se doplňují na ploše.
   V kroku autoři skupin jdou nad skupinami zadat i autoři celé akce:
   skupiny bez vlastních autorů je zdědí (fotila-li celou akci stejná
   parta, stačí je zadat jednou).
   Existuje-li k akci návrh skupin z importu, krok skupin použije jeho
   skupiny a přiřazení pro soubory v kořeni, které návrh uvádí;
   ostatní dostanou automatický návrh. Prvním uložením
   `_metadata.json` se návrh smaže.
3. **Pak pracovní plocha** (i při každém dalším otevření): vlevo mřížka
   náhledů po skupinách, vpravo formulář podle výběru — nic vybráno =
   akce, hlavička skupiny = skupina, vybrané soubory = soubory. Zděděné
   hodnoty jsou ve formuláři vidět a jdou přepsat. Lišta ukazuje, co
   chybí („2 skupiny bez autorů, 14 souborů bez data“).

   Datum pořízení má dva vstupy s nativním výběrem prohlížeče: den
   a čas (se sekundami). Prázdný čas = hodnota jen s datem (WhatsApp);
   smazání času ponechá den, smazání dne smaže celé datum, čas bez dne
   zadat nejde. U výběru změna dne přepíše každému souboru den a jeho
   čas zůstane, změna času přepíše čas a den zůstane; rozdílnou část
   vstup neukazuje a vedle stojí „rozdílné hodnoty“.

   Místo mřížky jde přepnout na **lupu** (Enter, dvojklik na dlaždici
   nebo přepínač; zpět Esc): velká fotka nebo přehrávač videa a pod ní
   filmový pás celé akce se skupinami oddělenými předělem. Šipky
   přepínají aktuální soubor a vyberou jen jej, Shift+šipky výběr
   rozšiřují; klik do pásu vybírá jako v mřížce. Výběr i formulář jsou
   s mřížkou společné.

   **Vyřazení:** klávesa Del nebo tlačítko „Vyřadit“ v panelu označí
   vybrané soubory k vyřazení (jsou-li už všechny označené, označení
   zruší). Označené dlaždice zůstávají na místě, zašedlé a přeškrtnuté.
   Lišta ukazuje počet souborů k vyřazení a tlačítko **Uklidit…**: to
   uloží změny, ukáže plán přesunu do `k_odstraneni.ignored`
   a v produkčním režimu ho po potvrzení provede (viz Podsložky a RAW);
   ve vývojovém jen ukáže plán.
4. **Dokončení akce** uloží změny, zkontroluje úplnost (co chybí,
   ukáže a dokončí až po potvrzení), zapíše sidecary a nastaví
   `dokonceno`. Selže-li zápis některého sidecaru, akce dokončená
   není. Tlačítko **Exportovat** zapíše sidecary bez kontroly
   a bez dokončení. U tlačítka plocha ukazuje, kolik sidecarů je
   neaktuálních, a po úpravě „neexportované změny“; seznam akcí
   u dokončené akce upravené po exportu uvede „změněno po exportu“.
   U dokončené akce je Dokončit akci neaktivní, dokud není co
   dokončovat (neuložené či neexportované změny, neaktuální sidecary,
   selhaný export).

Našeptávání a kontrola jmen viz výše.

### Import

Průvodce importem se spouští ze seznamu akcí (bez cíle) nebo z plochy
akce (s ní jako předvybraným cílem). Kroky: soubory → přehled → cíl →
plán → výsledek.

- **Soubory:** jednotlivé soubory i celá složka, výběrem nebo
  přetažením; soubory z podsložek se berou, jako by ležely v jedné
  úrovni. Nahrávají se po jednom (2–3 souběžně, s průběhem) do
  `.work/import/<id>/`, ne do archivu; zavření stránky archiv nezmění.
  Adresa `#/import/<id>` přežije reload. Limit 20 GB na soubor, server
  před nahráním kontroluje volné místo. Import patří jménu uživatele
  (porovnání jako u návrhů jmen), ne záložce: seznam akcí ukazuje
  „Moje rozpracované importy“ (založeno, počet a velikost souborů,
  zamýšlený cíl, poslední aktivita) s tlačítky Pokračovat a Zahodit.
  Cizí import není vidět a jeho adresa hlásí „nenalezen“.
- **Přehled:** počty fotek, videí a RAWů, rozsah dat z EXIF (WhatsApp
  z názvu), přístroje, nepodporované soubory. Přijímají se média
  aplikace (jpg, jpeg, png, mp4, mov) a RAWy; `Thumbs.db` se tiše
  přeskočí, ostatní se vypíšou a nepřenesou.
- **Cíl:** stávající akce, nebo nová — datum se předvyplní nejstarším
  dnem z EXIF, název doplní uživatel; složka `YYYY-MM-DD název` bez
  `/` a `\` a nesmí existovat (bez ohledu na velikost písmen; jinak
  průvodce nabídne zvolit ji jako stávající). U dokončené akce
  upozorní, že nové soubory budou bez metadat.

  Ve stejném kroku se volí **skupiny** importovaných médií (RAWy
  skupinu nedostanou): *podle podsložek* (jen má-li výběr podsložky;
  skupina = podsložka první úrovně pod nejdelší společnou složkou
  výběru, soubory přímo v ní dostanou skupinu pojmenovanou po ní),
  *jedna nová skupina* (název předvyplněný kořenem výběru, jinak
  `Import YYYY-MM-DD`), *automaticky* (přístroj a vzor názvu jako
  u nové akce), *bez skupiny*, nebo *zařadit do skupiny …* (jen akce,
  jejíž `_metadata.json` skupiny má). Předvolba: podsložky → podle
  podsložek; jinak nová akce a akce bez `_metadata.json` →
  automaticky, ostatní → jedna nová skupina. Volba se uloží k importu
  spolu s cílem.
- **Plán:** média do kořene, RAWy do `RAW.ignored/`. Jméno, které
  v cíli existuje nebo ho má víc souborů výběru, se blokuje.
  Duplicita (stejný sha256 jako soubor v kořeni cílové akce nebo jiný
  soubor výběru) se přeskočí; hashe akce se počítají jen u souborů
  shodné velikosti a cachují se v `.work/cache/sha256/`. Na SMB to
  může trvat minuty, proto server posílá průběh porovnání (stream
  NDJSON, po souboru a u velkých po 64 MB; hashe z cache jsou hned
  hotové) a tlačítko je do konce výpočtu zablokované. Zvolený cíl se
  uloží k importu a po návratu se předvyplní. U každého přenášeného
  média plán ukáže cílovou skupinu (nové označené). Nové skupiny se
  s existujícími (v `_metadata.json` nebo návrhu) samy nesloučí ani
  při shodě: název nové dostane případně pořadové číslo a u každé jde
  zvolit „nová skupina“ nebo „připojit ke skupině …“, existující se
  shodným názvem (bez diakritiky a velikosti písmen) nebo přístrojem
  nahoře jako shoda. Volba připojení plán nepřepočítává, posílá se až
  s provedením.
- **Provedení** (jen produkční režim, ve vývojovém se plán jen ukáže):
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
  a uvede je ve výsledku.

  Po přenosu server zapíše skupiny jen pro skutečně přenesená média.
  Akce s `_metadata.json`: přenesené soubory (s technickými údaji,
  jako při otevření akce), nové skupiny a přiřazení jdou rovnou do
  `_metadata.json` pod zámkem importu; stávající záznamy a skupiny se
  nemění. Akce bez něj: `_metadata.json` nevznikne, skupiny jdou do
  návrhu `.work/navrhy-skupin/<akce>.json` (i v produkčním režimu;
  další import ho doplní) a použije ho průvodce akce. Když zápis
  selže (např. `_metadata.json` mezitím upravený mimo aplikaci),
  soubory zůstanou v archivu a výsledek uvede, že jsou bez skupiny.
- **Výsledek:** přenesené, blokované, duplicitní a selhané soubory;
  přenesené zmizí z pracovního adresáře, ostatní tam zůstanou, dokud
  uživatel import nezahodí. Importy neaktivní přes 7 dní server smaže
  při startu. Průvodce nabídne otevřít akci; nové soubory jsou mezi
  „novými od posledního otevření“, metadata se doplňují běžně.

### Immich

Stránka **Nastavení** (odkaz v hlavičce) drží adresu serveru Immich
a API klíč. Stačí klíč jen pro čtení s oprávněními ke čtení osob,
assetů a obličejů (`face.read`). Ukládá se do `.work/immich.json`
(práva 0600), nikdy do archivu; klíč se do prohlížeče nevrací (jen
„klíč nastaven (…W4No)“) a změna adresy vyžaduje zadat ho znovu.
Otestovat ověří verzi, osoby a čtení obličejů. Nastavení
(i synchronizaci na požádání) smí jen admin.

**Synchronizace obličejů** běží v serveru po startu, pak každých
15 minut a na tlačítko Načíst osoby:

- Z Immiche se načtou pojmenované osoby (i skryté), jejich assety
  a obličeje na nich; nepojmenované obličeje se ignorují.
- Asset se páruje se souborem podle posledních dvou částí cesty
  (složka akce, soubor), kořen archivu v Immichi se nenastavuje.
  Zpracují se jen akce, které už mají `_metadata.json`.
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

### Ukládání a export

- `_metadata.json` se ukládá průběžně, atomicky (dočasný soubor
  a přejmenování), v produkčním režimu do složky akce, ve vývojovém do
  `.work/metadata/<akce>/`. Rozpracovaná metadata z `.work` převezme do
  archivu jednorázově `python -m fotoarchiv prevzit` (jen u akcí, které
  `_metadata.json` v archivu ještě nemají).
- XMP sidecary se zapisují při dokončení akce, samostatným tlačítkem
  Exportovat a dávkově `python -m fotoarchiv exportovat [AKCE]` (bez
  akce všechny s `_metadata.json`; zámky nekontroluje). **Přepisují se
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

Aplikace běží jako jeden sdílený server; zámek otevřené akce drží
server v paměti (kdo, relace prohlížeče, od kdy, poslední heartbeat).
Proto **server smí běžet jen jako jeden proces** (vlákna ano, víc
workerů ne). Do archivu se žádný soubor zámku nezapisuje.

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
- Admin může zámek jiné relace vynuceně uvolnit (opuštěná rozdělaná
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

Metadata (JPG, mp4) čte `exiftool`. Náhledy
(320 px do mřížky, 1600 px do lupy) se cachují lokálně mimo archiv —
archiv leží na SMB; lupa si sousední fotky načítá předem. Videa se do
lupy posílají přímo z archivu, jen ke čtení.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
