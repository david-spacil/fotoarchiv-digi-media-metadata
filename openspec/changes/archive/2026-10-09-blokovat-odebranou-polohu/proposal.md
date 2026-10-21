## Why

Android při předání fotky webovému prohlížeči (Chrome i Firefox, výběr
z galerie i přes Soubory → `DCIM/Camera`) vynuluje blok GPS v EXIF:
`GPSVersionID 0 0 0 0`, prázdné souřadnice, zbytek souboru bajt po
bajtu stejný (ověřeno na Pixel 8a, Android 17, 2026-10-09: originál
49.13579 N, 16.24680 E; kopie po importu 40 nulových bajtů v bloku
GPS). Webová stránka si oprávnění k poloze médií říct nemůže. Poloha
je pro archiv jedna z nejdůležitějších informací, takže fotka, která ji
cestou ztratila, se do archivu dostat nesmí — kolega ji musí předat
jinou cestou. Stejně ztrácejí polohu i fotky přeposlané mailem
z telefonu, takže pravidlo platí pro každý import.

## What Changes

- Sken EXIF rozpozná **odebranou polohu**: blok GPS existuje
  (`GPSVersionID` je `0 0 0 0`) a souřadnice jsou prázdné.
- Přehled importu uvede fotky s odebranou polohou s důvodem a návodem
  (předat originál jinou cestou); import je **nepřenese**, bez možnosti
  povolení.
- Plán a výsledek je uvedou jako samostatnou skupinu nepřenesených;
  zůstanou v pracovním adresáři / ve zdroji `přetřídit` jako poškozené.
- Fotky bez bloku GPS (WhatsApp, přístroj bez GPS, vypnutá poloha)
  a fotky s platnými souřadnicemi se importují jako dosud.
- Mobilní import v prohlížeči tím na Androidu prakticky nepůjde;
  odkládá se ze změny `mobilni-verze` do nalezení jiné cesty (nativní
  aplikace, Immich, Syncthing).

## Capabilities

### New Capabilities
<!-- žádné -->

### Modified Capabilities
- `photo-import`: nový požadavek — fotka s odebranou polohou se
  nepřenese; přehled, plán a výsledek ji uvádějí s důvodem.

## Impact

- `fotoarchiv/scan.py` — tag `GPSVersionID`, příznak v technických
  údajích, zneplatnění cache skenu.
- `fotoarchiv/importer.py` — přehled (`overview`), plán a provedení
  (nepřenesené jako u poškozených).
- `fotoarchiv/static/app.js` — výpis v přehledu, plánu a výsledku.
- `tests/` — testy skenu, přehledu, plánu a provedení s podvrženým
  výstupem exiftoolu.
- `README.md` — oddíl Import (a zmínka v Poškozené soubory nebo
  vlastní odstavec).
- Pracovní plocha akce a export se nemění; soubory, které už v archivu
  jsou, se zpětně nekontrolují.
