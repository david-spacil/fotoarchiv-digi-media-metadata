## Why

Immich zahazuje název místa ze sidecaru (i u fotek bez GPS) a obec bere
jen ze souřadnic. Fotky bez GPS v EXIF (Panasonic, WhatsApp) tak v Immichi
nemají žádné místo, přestože ho v `_metadata.json` mají vyplněné.
Souřadnice místa jim ho vrátí, podobně jako centroidy katastrů v
`arubrno/archiv-immich`.

## What Changes

- Názvy míst použité u fotek se geokódují přes veřejný Nominatim (OSM):
  globálně, bez klíče. Odpovědi se cachují na serveru, každý dotaz se
  posílá nejvýš jednou.
- U nejednoznačného názvu (7× „Vysočany“) vybírá kandidáta člověk;
  předvybraný je nejbližší fotkám akce s GPS. Volba se ukládá do
  `_metadata.json` jednou na název a akci; jde zvolit i „bez souřadnic“
  nebo zadat souřadnice ručně.
- Výsledné GPS souboru: vlastní/zděděné GPS, jinak souřadnice jeho
  výsledného `misto`. Z toho bude vycházet export XMP (`exif:GPS*`).
  Tag `misto/…` se nezavádí.
- Lišta chybějících údajů ukáže místa bez rozhodnutých souřadnic.
- Atribuce „© OpenStreetMap contributors“ u výsledků.

## Capabilities

### New Capabilities
- `place-geocoding`: dotaz na Nominatim, cache, volba kandidáta,
  souřadnice míst v dokumentu.

### Modified Capabilities
- `metadata-model`: výsledné GPS souboru doplněné ze souřadnic místa.
- `metadata-workspace`: lišta chybějících údajů (místa bez souřadnic).

## Impact

- Nový `fotoarchiv/geocode.py`, endpoint v `app.py`, volba `--kontakt`
  (identifikace v User-Agent, vyžaduje ji Nominatim).
- `model.py` + `static/inherit.js` + fixtury dědění (výsledné GPS).
- Klient: výběr kandidáta ve formuláři, lišta.
- Server potřebuje odchozí HTTPS na `nominatim.openstreetmap.org`.
- Nový klíč `souradnice_mist` v `_metadata.json` (zpětně kompatibilní,
  schéma `/1` zůstává).
