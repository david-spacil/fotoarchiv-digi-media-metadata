## Context

Repo zatím nemá kód. Archiv leží na SMB (`/mnt/x`, symlink
`~/archiv/x/…`), jedna akce má až ~7 GB (převážně RAW a video, které
se nenačítají). Na Fedoře je k dispozici Python 3.14, `exiftool`
a `ffmpeg`; Flask a Pillow chybí. Kolegové na Windows jsou žádoucí, ale
ne podmínkou. Požadavky viz `specs/`, motivace viz proposal.md.

## Goals / Non-Goals

**Goals:**

- Ověřit tok průvodce → plocha nad reálnou akcí s minimem kódu.
- Struktura, na kterou půjde navázat exportem XMP a zámkem bez
  přepisování.

**Non-Goals:**

- `sha256` souborů (pole z README) — až se změnou pro export, kde má
  smysl; v prototypu by znamenalo číst gigabajty po SMB.
- Vzhled, přístupnost, mobilní zobrazení.
- Víc uživatelů najednou na jednom serveru; aplikace běží lokálně pro
  jednoho uživatele.

## Decisions

### Stack: Flask + čistý JS, jedna stránka

Server v Pythonu vystavuje JSON API a statické soubory; klient je jedna
HTML stránka s ES moduly bez build kroku. Na Windows stačí Python
a `pip install -r requirements.txt`.
*Alternativy:* stdlib `http.server` (ruční routování, nestojí to za
ušetřenou závislost); Node/Vite (build krok a další runtime).

### Stav drží klient, server je bezstavový

Klient načte celý dokument `_metadata.json` spolu s výsledkem skenu,
upravuje ho v paměti a ukládá celý (PUT). Dědění se počítá v klientu
pro zobrazení; server ho počítat nepotřebuje (bude až u exportu XMP —
proto je výpočet popsaný jednoznačně ve spec `metadata-model` a v JS
i později v Pythonu ho jde ověřit stejnými případy).
*Alternativa:* patch po polích — složitější, pro jednoho uživatele bez
přínosu.

### Ochrana proti souběžné změně: verze = hash obsahu

`GET` vrací spolu s dokumentem `version` = sha256 bajtů souboru. `PUT`
posílá `version`; server přečte aktuální soubor, porovná hash a při
neshodě vrátí 409. Zápis jde do dočasného souboru ve stejném adresáři
a `os.replace` — atomický i na SMB, kam to pozdější změna přesune.
*Alternativa:* `mtime` — na SMB s rozdílnými hodinami nespolehlivé.

### Pracovní adresář a cache: `.work/` v repu

Výchozí `--work .work` (v `.gitignore`):
`.work/metadata/<název akce>/_metadata.json` a `.work/cache/thumbs/`.
Cesta archivu i pracovního adresáře jde přepsat parametry spuštění.
Přepnutí na zápis přímo do archivu bude jen změna kořene pro
`_metadata.json`, proto jde čtení/zápis přes jednu funkci, která cestu
skládá.

### Sken: jedno volání `exiftool` na akci

`exiftool -json -n -api QuickTimeUTC` se seznamem souborů kořene
a výběrem tagů (`DateTimeOriginal`, `CreateDate`, `Make`, `Model`,
`GPSLatitude`, `GPSLongitude`). Jeden proces místo stovek je po SMB
rozdíl minut. `QuickTimeUTC` převede UTC data z mp4 na místní čas, aby
se videa řadila s fotkami. Výsledek se cachuje v `.work/cache/` podle
(název, velikost, mtime).
*Alternativa:* Pillow/EXIF knihovna v Pythonu — neumí mp4.

### Skupiny: přístroj + vzor názvu

Vzory: `P\d{7}` (Panasonic), `\d{8}_\d{6}` (Samsung), `IMG-\d{8}-WA\d+`
(WhatsApp), `IMG_\d{4}`, jinak „ostatní“. Klíč skupiny = (model, vzor);
id je slug modelu nebo vzoru (`dc-g9`, `sm-a528b`, `whatsapp`).

### Náhledy: Pillow s `draft`, video přes `ffmpeg`

JPEG se dekóduje se `Image.draft()` (zmenšení už při dekódování, řádově
rychlejší), zmenšení na 320 px, EXIF orientace se aplikuje. Video: snímek
z 1. sekundy přes `ffmpeg`; bez `ffmpeg` zástupná ikona. Klíč cache =
hash (cesta, velikost, mtime). Generuje se líně při požadavku na náhled,
prohlížeč si je stahuje paralelně.

### Plán úklidu se počítá na serveru

Funkce vrací seznam operací (`move`, `rename`, `delete`) s příznakem
`blocked` a důvodem. V prototypu se jen zobrazí; pozdější změna doplní
provedení nad stejným plánem. Tím je logika (většina RAWů, kolize)
testovatelná bez UI.

### Jména: porovnání na serveru

Normalizace: NFKD, odstranění diakritiky, malá písmena, rozdělení na
slova, seřazení. Endpoint vrací našeptávání i „Mysleli jste“. Jedna
implementace, testovatelná v pytestu. Seznam se skládá z
`_metadata.json` v pracovním adresáři i v archivu.

### Stav „hotovo“

Kořenové pole `dokonceno` (datum a čas, nebo `null`). Prototyp ho
nenastavuje — patří ke změně s exportem — ale seznam akcí ho už čte.

### Testy

`pytest` pro čistou logiku: dědění, plán úklidu, skupiny, WhatsApp
datum, jména, uložení s 409. Dědění má implementaci v Pythonu (pro
pozdější export) i v JS (pro zobrazení); obě se ověřují proti stejným
fixturám v `tests/fixtures/inheritance/*.json` — Python v pytestu, JS
přes `node --test` bez npm závislostí (jen vývojářský nástroj, aplikace
Node nepotřebuje). UI se ověřuje ručně nad reálnou akcí.

## Risks / Trade-offs

- [Pomalé SMB při prvním skenu a náhledech] → jedno volání `exiftool`,
  líné náhledy s cache, průběh skenu v UI.
- [Názvy s diakritikou v NFD/NFC na SMB] → porovnávat názvy souborů po
  normalizaci NFC, ukládat původní tvar z disku.
- [Datum z videí v UTC] → `-api QuickTimeUTC`; ověřit na videu
  z akce 2026-04-28.
- [Dědění v JS a později v Pythonu se rozejde] → sdílené fixtury
  s očekávanými výsledky.
- [Prototyp ukládá mimo archiv, uživatel to zapomene] → cesta
  k pracovnímu adresáři je vidět v hlavičce aplikace.

## Open Questions

- Velikost náhledu a hustota mřížky — doladit nad reálnými daty.
- Jestli `IMG_####.jpg` mají EXIF — ukáže první sken; na návrh skupin
  to nemá vliv.
