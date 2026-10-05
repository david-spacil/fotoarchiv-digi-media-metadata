## Context

Prototyp (archivovaná změna `add-prototype-workspace`) má plochu
s mřížkou, výběrem (`state.sel`, `state.anchor`, `state.order`)
a formulářem v `fotoarchiv/static/app.js`. Náhledy 320 px vytváří
`fotoarchiv/thumbs.py` do `.work/cache/thumbs/` s klíčem podle (cesta,
velikost, mtime). Archiv leží na SMB; fotka G9 má ~9 MB, video až
stovky MB. Flask `send_file` umí podmíněné odpovědi a HTTP Range.

## Goals / Non-Goals

**Goals:**

- Lupa jako druhý režim plochy nad stejným stavem výběru a formulářem —
  žádný druhý model výběru.
- Plynulé přepínání šipkami i po SMB.

**Non-Goals:**

- Přiblížení 1:1, posun, porovnání fotek, hodnocení.
- Překódování videí, která prohlížeč neumí (HEVC apod.).
- Úpravy vzhledu mřížky.

## Decisions

### Režim jako stav klienta, jeden výběr

`state.view = "grid" | "loupe"` a nový `state.current` (aktuální
soubor). Výběr, kotva a pořadí (`state.order`) zůstávají společné;
lupa i pás jen jinak vykreslují stejný stav, takže formulář a ukládání
se nemění. Kliknutí v pásu i v mřížce jde přes jednu funkci výběru
(klik / Ctrl / Shift), která navíc nastaví `state.current`.
*Alternativa:* samostatná obrazovka lupy s vlastním výběrem — dva
modely výběru by se rozcházely.

### Rozvržení

Mřížka a lupa sdílí levý sloupec plochy; vpravo zůstává formulář.
Lupa = velká fotka (flex, `object-fit: contain`) nad pásem pevné výšky
(~110 px) s vodorovným posunem. Skupiny v pásu oddělí svislý předěl
s názvem skupiny; klik na název vybere skupinu (jako hlavička v mřížce).
Pás se při změně aktuálního souboru posune (`scrollIntoView` s
`inline: "nearest"`).

### Klávesy

Globální obsluha `keydown` reaguje jen na pracovní ploše a jen když fokus
není v `input`, `textarea` ani `select` (stejná ochrana jako dnešní Esc).
Šipky přepínají soubory jen v lupě, i když je fokus na přehrávači videa
(šipkami se tedy video nepřetáčí). Enter v mřížce otevře lupu na
aktuálním souboru (naposledy kliknutém), ne na kotvě výběru — po
Shift+kliku se liší a spec chce aktuální naposledy kliknutý. Bez
aktuálního souboru lupa ukáže první vybraný, jinak první soubor akce.
Esc v lupě vrací do mřížky (výběr nemaže); Esc v mřížce maže výběr jako
dosud.

### Velké náhledy: parametr velikosti

`thumbnail(src, cache_dir, size=SIZE)`; velikost je součástí klíče cache
a jména souboru (`<hash>-<velikost>.jpg`), takže 320 a 1600 px vedle sebe
nekolidují. Stávající 320px náhledy (`<hash>.jpg`) se tím jednou
přegenerují; staré soubory zůstanou v cache do ručního smazání. Endpoint
`/api/akce/<n>/nahled/<soubor>?velikost=1600` (povolené hodnoty 320
a 1600, jiné odmítnout). JPEG se dekóduje s `draft` na nejbližší větší
měřítko, kvalita 85. Pro video stačí stávající snímek přes `ffmpeg`
ve velikosti 1600 (náhled před spuštěním a záloha, když video nejde
přehrát).
*Alternativa:* posílat originál JPEG — 9 MB po SMB na každou šipku.

### Předběžné načítání

Klient po změně aktuálního souboru vytvoří `new Image()` pro 2 další
a 1 předchozí soubor ve velikosti 1600 px; server je vygeneruje do
cache. Bez fronty na serveru — Flask běží vícevláknově a počet je malý.

### Originál videa z archivu

`/api/akce/<n>/soubor/<soubor>` vrátí originál přes
`send_file(..., conditional=True)` (Range, 206). Povolen jen soubor
v kořeni akce s příponou fotky nebo videa (stejná kontrola názvu jako
u náhledů). Soubor se otevírá jen pro čtení.

## Risks / Trade-offs

- [Prohlížeč neumí kodek videa, např. HEVC z mobilu] → událost `error`
  na `<video>` přepne na velký náhled se zprávou; překódování mimo
  rozsah.
- [První zobrazení fotky po SMB trvá ~0,3–1 s] → předběžné načítání
  sousedů; během načítání zůstane vidět náhled 320 px roztažený.
- [Cache velkých náhledů roste] → ~200–400 kB na fotku, u 180 fotek
  desítky MB; mazání cache je ruční (`.work/cache/`).
- [Šipky a fokus ve formuláři] → klávesy jen mimo pole formuláře; po
  kliknutí do pásu nebo fotky jde fokus pryč z pole.
