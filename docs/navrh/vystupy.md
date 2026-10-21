[← Dokumentace](../README.md)

# Výstupy

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
  formátu XMP `DDD,MM.mmmmmmK` (např. `49,07.404000N`). Prázdná pole se
  nezapisují; místo, přístroj, účastníci, osoby ani skupina do
  sidecaru nejdou (osoby má Immich z vlastního rozpoznávání obličejů;
  obličeje jen při obnově, viz níže). Sidecar skládá aplikace sama (ne exiftool), takže obsah
  závisí jen na `_metadata.json` a názvu složky akce.
  Stejně vzniká i sidecar v ZIPu stažené akce nebo výběru, a to
  v paměti z přibaleného `_metadata.json`; sidecary na disku se pro
  ZIP nečtou (viz
  [Stažení originálů](../navod/pracovni-plocha.md#stažení-originálů)).

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
  akce, viz [Archiv](archiv.md)) a nezpracovanými složkami první úrovně
  (`přetřídit`, `přednášky SKLEP TIC`, `fotky mimo akce`). Testovací
  knihovna vidí archiv pod `/immich/archiv/…`; aplikace z ní čte
  jen pojmenované obličeje (viz [Immich](immich.md)).
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
