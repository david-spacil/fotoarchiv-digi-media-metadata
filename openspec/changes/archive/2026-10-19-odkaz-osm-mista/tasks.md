# Tasks

## 1. Server: `osm` jen u úplného objektu

- [x] 1.1 V `fotoarchiv/geocode.py` `candidate` přidat klíč `osm` jen
  při neprázdném `osm_type` i `osm_id` (viz design). Do
  `tests/test_geocode.py` přidat test kandidáta bez `osm_type`/`osm_id`
  (bez klíče `osm`) a ověřit, že stávající test s `relation/439179`
  dál projde: `.venv/bin/python -m pytest -q tests/test_geocode.py`.

## 2. Klient: odkaz na objekt OSM

- [x] 2.1 Vytvořit `fotoarchiv/static/osm.js` s `osmUrl(osm)`
  (regex `^(node|way|relation)/[1-9]\d*$`, jinak `null`) a hlavičkovým
  komentářem jako u `fronta.js`. Test `tests/js/osm.test.mjs`: tři
  platné typy, `None/None`, `undefined`, `null`, číslo, `relation/0`,
  `relation/12a`, `relation/../x`, cizí typ (`area/1`).
  Ověřit: `node --test tests/js/*.test.mjs`.
- [x] 2.2 V `placeBlock` (`app.js`) přidat za `popis` odkaz „OSM“
  z `osmUrl(decision.osm)` (`target="_blank"`, `rel="noopener
  noreferrer"`, `title` s hodnotou). Ruční a „bez souřadnic“ bez odkazu.
- [x] 2.3 V `placeChooser` přidat stejný odkaz na konec textu každého
  kandidáta z `osmUrl(k.osm)`. Kandidát bez platného `osm` bez odkazu.
- [x] 2.4 Pokud odkaz v `p.meta` nebo `.candidate` nevypadá jako
  odkaz v obou režimech vzhledu, doplnit pravidlo do `style.css`
  (jinak beze změny). Ověřit, že `contrast.test.mjs` dál projde.
- [x] 2.5 README, odstavec o souřadnicích míst (ř. ~195–207): účel
  klíče `osm` (traceback zdroje souřadnic, jen u kandidáta z Nominatimu,
  nikam se neexportuje) a odkaz na OSM v panelu i u kandidátů. Ověřit,
  že příklad JSONu (ř. ~145) odpovídá tvaru `relation/<id>`.

## 3. Ověření

- [x] 3.1 Celé testy před změnou a po ní:
  `.venv/bin/python -m pytest -q` a `node --test tests/js/*.test.mjs`
  (počty testů ve výpisu).
- [x] 3.2 Ve vývojovém režimu se smyšleným archivem ve scratch adresáři
  (žádná reálná data) a `.work/cache/geokodovani.json` s ručně
  vloženými kandidáty pro `Vysočany` (dva kandidáti s `osm`, jeden
  s `None/None`; bez dotazu na Nominatim) projít scénáře specifikace
  v headless prohlížeči: odkaz u uloženého místa, žádný odkaz u ručního
  a „bez souřadnic“, odkazy u kandidátů, klik na odkaz kandidáta
  nezmění zaškrtnutý radio a otevře novou kartu, `None/None` bez odkazu.
  Snímky panelu a volby v obou režimech vzhledu.
