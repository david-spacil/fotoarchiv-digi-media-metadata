# Proposal

## Why

Volba kandidáta z Nominatimu ukládá k místu akce vedle `gps` a `popis`
i odkaz na objekt OSM (`osm`, např. `relation/435541`), ale nic ho
nečte. Zdroj uložených souřadnic tak nejde ověřit a při volbě mezi
stejnojmennými místy (Vysočany u Blanska, u Znojma, v Praze) vidí
uživatel jen text popisu (#46).

## What Changes

- U místa akce s uloženými souřadnicemi z Nominatimu SHALL panel
  souřadnic ukázat odkaz na objekt na openstreetmap.org
  (`https://www.openstreetmap.org/<typ>/<id>`), který se otevře
  v nové kartě. Místa ručně zadaná nebo bez souřadnic odkaz nemají.
- Ve volbě souřadnic SHALL mít odkaz na OSM i každý kandidát, aby šlo
  stejnojmenná místa porovnat ještě před potvrzením.
- Odkaz se SHALL ukázat jen u hodnoty `osm` ve tvaru
  `node|way|relation/<číslo>`; jiná hodnota (např. `None/None`
  ze staré cache) odkaz nemá a nic nerozbije.
- Server SHALL u kandidáta bez typu či id objektu klíč `osm` vynechat
  místo ukládání `None/None`.
- Specifikace a README SHALL popsat klíč `osm` a jeho účel (traceback
  zdroje souřadnic). Volba kandidáta ho dál ukládá jako dosud.
- XMP export, index ani dědění se nemění; `osm` dál nikam nevstupuje.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `place-geocoding`: požadavek Volba souřadnic místa doplní klíč `osm`
  u kandidáta z Nominatimu; nový požadavek Odkaz na objekt OSM (panel
  místa i kandidáti ve volbě, tvar hodnoty, bez odkazu u ručních
  souřadnic).

## Impact

- `fotoarchiv/static/app.js`: `placeBlock` (rozhodnuté místo)
  a `placeChooser` (kandidáti) přidají odkaz.
- Nový modul `fotoarchiv/static/osm.js` (čistá funkce hodnota → URL
  nebo `null`) s testem `tests/js/osm.test.mjs`.
- `fotoarchiv/geocode.py` `candidate`: bez `osm_type`/`osm_id` bez
  klíče `osm`; test v `tests/test_geocode.py`.
- `README.md`: odstavec o souřadnicích míst (účel `osm`).
- Data v archivu se nemigrují; stávajících 16 míst s `osm` odkaz
  dostane bez zásahu. API ani schéma `_metadata.json` se nemění.
