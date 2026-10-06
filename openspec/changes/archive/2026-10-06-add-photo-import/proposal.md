## Why

Nové fotky a videa se dnes do archivu dostávají ručním kopírováním na
SMB: složka akce se pojmenuje ručně (často mimo vzor `YYYY-MM-DD
název`), soubory se přepíší nebo zdvojí a RAWy skončí v kořeni.
Aplikace už archiv zná, umí číst EXIF a hlídat kolize, takže import
přes prohlížeč odstraní ruční krok i jeho chyby a kolegům nebude stačit
přístup na SMB.

## What Changes

- Nový průvodce importem v prohlížeči (`#/import`), spustitelný ze
  seznamu akcí a z pracovní plochy akce (s předvybraným cílem).
- Kroky: výběr souborů (přetažení, výběr souborů i celé složky) →
  nahrání do pracovního adresáře serveru (`.work/import/<id>/`) →
  přehled (data z EXIF, přístroje, nepodporované soubory, kolize jmen,
  duplicity) → volba cíle → potvrzení → přesun do archivu → otevření
  akce.
- Cíl je **stávající akce**, nebo **nová akce**: aplikace navrhne datum
  z EXIF (nejstarší den) a uživatel doplní název; složka vznikne ve
  tvaru `YYYY-MM-DD název`.
- Pravidla jako u úklidu: nic se nepřepíše, kolize jména se blokuje,
  soubor se stejným obsahem (sha256) jako soubor v kořeni cílové akce
  se přeskočí a nahlásí. RAWy jdou rovnou do `RAW.ignored/`.
- Import do stávající akce vyžaduje zámek akce.
- Ve vývojovém režimu se nahraje do pracovního adresáře a ukáže se
  plán; do archivu se nic nezapíše.
- Originály se při importu nemění (obsah ani čas změny).

## Capabilities

### New Capabilities
- `photo-import`: průvodce importem fotek a videí do stávající nebo
  nové složky akce přes prohlížeč, včetně kontroly kolizí a duplicit.

### Modified Capabilities
- `event-lock`: zápis jen se zámkem platí i pro import do stávající
  akce.

## Impact

- Nový modul `fotoarchiv/importer.py` (staging, plán, provedení),
  endpointy v `fotoarchiv/app.py`, úklid starých stagingů při startu
  (`__main__.py`).
- `fotoarchiv/archive.py`: dočasné soubory importu se nepočítají mezi
  média.
- Klient: nový pohled průvodce v `fotoarchiv/static/app.js`, styly.
- `README.md` (Tok práce, nová sekce Import), `AGENTS.md` (stav).
- Bez nové závislosti; upload jde přes stávající Flask.
