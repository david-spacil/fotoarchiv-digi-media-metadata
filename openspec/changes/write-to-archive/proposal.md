## Why

Prototyp ukládá `_metadata.json` mimo archiv a úklid jen ukazuje, takže
na ostrých akcích se nedá pracovat. Aplikace poběží jako jeden sdílený
server ve firemní síti; přesuny a přejmenování musí proběhnout dřív, než
se archiv napojí do Immiche (změna cesty = nový asset).

## What Changes

- **BREAKING:** v produkčním režimu se `_metadata.json` čte a ukládá ve
  složce akce v archivu. Pracovní adresář zůstává jen pro cache
  a vývojový režim (bez přepínače se do archivu dál nezapisuje).
- Zámek otevřené akce drží server v paměti (jediný zapisující proces):
  držitel s heartbeatem z prohlížeče, uvolnění při zavření akce,
  opuštěný zámek po ~5 min bez heartbeatu jde převzít. Kdo nemá zámek,
  vidí akci jen ke čtení. Uložení a úklid bez zámku server odmítne.
- „Kdo“ u zámku je zatím jméno zadané v prohlížeči; přihlašování řeší
  samostatná změna `add-login`.
- Úklid se po potvrzení opravdu provede: přesuny, přejmenování na
  `.ignored`, smazání vyprázdněných podsložek. Blokované operace se
  přeskočí, nic se nepřepíše.
- Převzetí rozpracovaných `_metadata.json` z pracovního adresáře
  prototypu do archivu (jen kde v archivu ještě nejsou).
- Odpadá souborový zámek `_metadata.lock` z README (nahrazen zámkem
  v serveru).

## Capabilities

### New Capabilities
- `event-lock`: zámek akce v serveru, heartbeat, převzetí opuštěného
  zámku, režim jen pro čtení.

### Modified Capabilities
- `archive-browsing`: požadavek „Archiv jen pro čtení“ nahrazuje zápis
  `_metadata.json` do složky akce (s vývojovým režimem do pracovního
  adresáře).
- `event-cleanup`: „Úklid nasucho“ nahrazuje provedení úklidu.

## Impact

- `fotoarchiv/archive.py` (kořen metadat, převzetí z `.work`),
  `fotoarchiv/cleanup.py` (provedení plánu), `fotoarchiv/app.py`
  (API zámku, kontrola zámku u zápisů), nový `fotoarchiv/lock.py`,
  `fotoarchiv/__main__.py` (přepínač režimu, příkaz převzetí).
- Klient `static/app.js`: jméno uživatele, heartbeat, režim jen pro
  čtení, krok úklidu s provedením a výsledkem.
- Server musí běžet jako **jeden proces** (zámek je v paměti).
- Proces serveru potřebuje zápis do archivu (SMB/NFS na Debianu).
- README: Stav, Souběh, Ukládání; AGENTS.md: Stav.
