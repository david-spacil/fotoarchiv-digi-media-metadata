## Context

Technické údaje souborů importu dává `scan.scan` (jedno volání
`exiftool -json -n` nad tagy `TAGS`, cache podle jména, velikosti
a času změny v `.work/cache/scan/`). `parse_record` dnes z GPS bere jen
číselné `GPSLatitude`/`GPSLongitude`, takže vynulovaný blok vypadá
stejně jako žádný. Nepřenášení poškozených řeší `Importer._damaged`
→ `iter_plan(..., damaged)`, které takové soubory z operací vynechá
a uvede je zvlášť s důvodem; provedení jde přes stejný `iter_plan`.

Ověřený výstup `exiftool -json -n` (Pixel 8a, Android 17):
odebraná `{"GPSVersionID": "0 0 0 0", "GPSLatitude": "",
"GPSLongitude": ""}`, originál `{"GPSVersionID": "2 2 0 0",
"GPSLatitude": 49.135…, "GPSLongitude": 16.246…}`.

## Goals / Non-Goals

**Goals:**
- Fotka s odebranou polohou se do archivu nedostane žádnou cestou
  importu.

**Non-Goals:**
- Videa: jak Android zachází s polohou v MP4/MOV, není ověřené;
  řeší se samostatně po měření.
- Zpětná kontrola souborů, které už v archivu jsou (`zkontrolovat`).
- Obnova polohy z jiného zdroje.

## Decisions

### Rozpoznání ve skenu, ne v kontrole integrity
Do `TAGS` přibude `GPSVersionID`; `parse_record` přidá
`"poloha_odebrana": True`, když `GPSVersionID == "0 0 0 0"` a šířka
ani délka nejsou čísla. Patří to ke skenu (EXIF), ne do `integrity`
(obsah souboru, jiná cache a jiné stavy). Alternativa „podezřelý
soubor“ v kontrole by ho šlo povolit a míchala by dvě různé věci.

### Zneplatnění cache skenu
Starší záznamy cache příznak nemají a přeskočily by se. Záznam cache
dostane verzi (`"v": 2`); záznam bez ní se bere jako chybějící
a exiftool ho přečte znovu. Jednorázový přepočet skenů je levný
(jen tagy, ne obsah).

### Nepřenášení přes stávající cestu poškozených
`Importer` sloučí do `damaged` pro `iter_plan` i soubory s odebranou
polohou s výsledkem `{"stav": "bez_polohy", "duvod": "telefon odebral
polohu"}`. Plán a výsledek je tak vynechají a uvedou se stejnou
mechanikou (zůstanou ve stagingu / zdroji, provedení je znovu
vyhodnotí). Klient je podle `stav` vypíše jako samostatnou skupinu
„Odebraná poloha“. Volba „přesto importovat“ se pro tento stav
nenabízí a `set_allowed` ji nepřijme.
Alternativa samostatný parametr `iter_plan` → víc kódu ve stejné
smyčce bez rozdílu v chování.

### Přehled
`overview` přidá k souboru `poloha_odebrana` a seznam
`odebrana_poloha` (cesty). Pokračovat zůstává dostupné, pokud zbývá
aspoň jedno přenositelné médium (stejně jako u poškozených).

## Risks / Trade-offs

- [Jiný výrobce vynuluje blok jinak (např. bez `GPSVersionID`)] →
  pravidlo by ho nechytilo a fotka projde bez polohy jako dnes; rozšířit
  po dalším vzorku. Záměrně úzké, aby neblokovalo fotky, které polohu
  nikdy neměly.
- [Kolega nemá jinou cestu, jak originál předat] → přehled říká proč
  a co dělat; obchvat (kabel, FileSender z počítače, `přetřídit`)
  je mimo aplikaci.
- [Smazání poškozeného souboru nabízí přehled i pro tento stav?] →
  ne; soubor není poškozený, jen bez polohy. Zůstane do zahození
  importu.

## Migration Plan

Nasazení obvykle; první otevření importu přepočítá sken (verze cache).
Návrat = předchozí obraz, cache v2 starší kód ignoruje jen tím, že
čte `data` (pole navíc nevadí).
