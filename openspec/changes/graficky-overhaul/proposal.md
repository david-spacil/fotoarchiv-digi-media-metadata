## Why

Klient má zatím jen funkční rozvržení (`style.css` to přímo říká):
barvy jsou natvrdo ve ~60 hexech, bez společných proměnných a tmavého
režimu. Nad plochou se vrší tři lišty. Mřížka je světlá, lupa tmavá,
dlaždice mají pevnou velikost. Dědění hodnot (hlavní informace
formuláře) rozlišují jen jemné odstíny pozadí. Aplikace se používá na
velkých monitorech i na noteboocích, kde se plocha s panelem 400 px
a třemi lištami tísní. Issue #26.

## What Changes

- **Design tokeny:** všechny barvy, odstupy, zaoblení a typografie
  jako proměnné na `:root`; žádný hex mimo definici tokenů. Jednotná
  tlačítka, štítky, čipy, formulářová pole, dialogy a kroky průvodce.
  Tmavý režim podle systému.
- **Varianty vzhledu k výběru (prototyp):** nad společnými tokeny dvě
  sady hodnot: **B – Temná pracovna** (neutrálně tmavá mřížka i lupa,
  ve stylu Lightroomu) a **C – Katalogová karta** (světlé teplé
  pozadí, výraznější typografie, formulář jako archivní karta).
  Přepíná je parametr `?vzhled=` a prohlížeč si volbu pamatuje.
  Po výběru se nevybraná varianta odstraní (úkol na konci změny).
- **Jedna lišta akce:** řádek akce (zpět, název, přepínače, Importovat,
  Dokončit) a lišta chybějících údajů se sloučí do jedné lišty;
  chybějící údaje jsou v ní čipy, na úzkém okně se zalomí pod ni.
- **Velikost dlaždic:** posuvník velikosti náhledů v mřížce, pamatuje
  si ho prohlížeč.
- **Skládací panel formuláře:** panel jde sbalit (tlačítko a klávesa),
  mřížka nebo lupa pak zabere celou šířku; volba se pamatuje. Na
  užším okně je panel užší.
- **Zdroj hodnoty u pole:** zděděné, rozdílné a vlastní hodnoty mají
  výrazný proužek a štítek zdroje („z akce“, „ze skupiny“, „z místa“,
  „rozdílné“). Vlastní hodnota u skupiny nebo souboru má tlačítko
  „vrátit na zděděné“ (dnes jen smazáním pole).
- **Podporovaná šířka:** plocha je použitelná od 1280 × 720 CSS px
  (notebook se škálováním) po široké monitory.

Mimo rozsah: změna toku práce, datového modelu, API a klávesových
zkratek (kromě nové klávesy pro panel); build krok nebo CSS framework.

## Capabilities

### New Capabilities
- `app-appearance`: vizuální systém klienta — tokeny, tmavý režim,
  varianty vzhledu a jejich přepínání, podporované šířky okna.

### Modified Capabilities
- `metadata-workspace`: sloučená lišta akce s chybějícími údaji,
  velikost dlaždic, skládací panel, zdroj hodnoty a vrácení na zděděné
  ve formuláři.

## Impact

- `fotoarchiv/static/style.css` — přepsání na tokeny a komponenty,
  soubory variant.
- `fotoarchiv/static/app.js` — rozvržení plochy (`renderWorkspace`,
  `header`, `renderBar`), formulář (pole s děděním), posuvník, panel,
  přepínání vzhledu.
- `fotoarchiv/static/prihlaseni.html`, `heslo.html` — tytéž tokeny.
- `README.md`, oddíl Aplikace.
- Server, API, `_metadata.json`, XMP: beze změny. Bez nových závislostí.
