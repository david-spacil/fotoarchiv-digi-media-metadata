## Context

`misto` je řetězec na úrovni akce (`mista`, výčet), skupiny a souboru;
`gps` je `[lat, lon]` ze skenu EXIF, uložené u souboru. Dědění počítají
`model.resolve` a `static/inherit.js` proti společným fixturám. Export
XMP zatím není; tato změna připraví výsledné GPS, ze kterého bude čerpat.

Ověřeno 5. 10. 2026: Nominatim pro `Zkušebná` vrací 7 kandidátů (CZ, SK),
pro `Vzorkov` jednoho. Podmínky provozu
(operations.osmfoundation.org/policies/nominatim): max 1 dotaz/s,
identifikující User-Agent, povinná cache, zákaz našeptávání, atribuce.

## Goals / Non-Goals

**Goals:**
- Každý název se na službu pošle jednou za celý server.
- Rozhodnutí o kandidátovi je data (v `_metadata.json`), ne cache.

**Non-Goals:**
- Mapa a klik do mapy (možné rozšíření).
- Zápis XMP (samostatná změna exportu).
- Vlastní instance Nominatimu.

## Decisions

### Cache ≠ rozhodnutí
Cache (`work/cache/geokodovani.json`, klíč = normalizovaný dotaz →
kandidáti + čas) je čistě odpověď služby, smazatelná bez ztráty dat.
Volba kandidáta je v `souradnice_mist` dokumentu akce. Ukládat volbu do
cache by ji sdílelo napříč akcemi — „Zkušebná“ jsou v různých akcích
různé obce.
*Alternativa:* globální číselník míst v archivu — porušuje „zdroj pravdy
je `_metadata.json` ve složce akce“.

### `souradnice_mist` na nejvyšší úrovni dokumentu
`{"Zkušebná": {"gps": [49.15, 16.45], "popis": "Zkušebná, okres
Ukázkový, …", "osm": "relation/…"}, "X": null}`. Klíč je přesný řetězec
`misto` (bez normalizace, ať se místa nepletou). Přejmenování místa
rozhodnutí nepřenese — přijatelné, lišta ho ukáže znovu.
*Alternativa:* uvnitř `akce` — `akce` se dědí, tohle ne.

### Výsledné GPS v dědění
`resolve` po sestavení polí: chybí-li `gps` a `souradnice_mist[misto]`
má `gps`, doplní `{"hodnota": gps, "uroven": "misto"}`. Formulář
ukáže GPS jako zděděné z místa (odlišeně). Stejně v `inherit.js`, nové
fixtury.

### Klient Nominatimu na serveru
`geocode.py`: `urllib.request` (bez nové závislosti), globální zámek
+ min. 1,1 s mezi dotazy, timeout 10 s, `format=jsonv2&limit=10`,
`accept-language=cs`. User-Agent
`fotoarchiv-digi-media-metadata (<kontakt>)`, kontakt z volby
`--kontakt`; bez ní endpoint vrací 503 „geokódování vypnuto“. Endpoint
`GET /api/geokodovani?q=` vrací kandidáty a příznak `z_cache`.
Prohlížeč se na Nominatim neptá přímo (cache by nebyla sdílená).

### Kdy se ptát
Dotaz jen pro výsledné místo souboru bez GPS, které nemá rozhodnutí,
a až když uživatel otevře volbu souřadnic (z formuláře nebo z lišty) —
ne při psaní ani hromadně při otevření akce.

### Předvýběr
Nejbližší kandidát (haversine) k těžišti GPS souborů akce, které GPS
mají; bez nich první kandidát v pořadí služby. Vždy jen předvýběr.

## Risks / Trade-offs

- [Server bez přístupu ven] → ruční souřadnice a „bez souřadnic“
  fungují; ověřit přístup při nasazení.
- [Blokace IP při porušení podmínek] → cache, zámek a interval; žádné
  hromadné dotazy.
- [Souřadnice obce se tváří jako přesné místo] → v Immichi nerozlišitelné;
  v aplikaci odlišené úrovní `misto`. Přijatelné, stejné jako centroidy
  v `archiv-immich`.
- [Volný text místa, např. „u rybníka“] → služba nic nenajde, uživatel
  zvolí ručně nebo „bez souřadnic“.
