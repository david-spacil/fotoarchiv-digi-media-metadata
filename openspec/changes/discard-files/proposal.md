## Why

Akce obsahují nepovedené fotky a duplicity, které do Immiche nepatří.
Smazat je nechceme (originály se nemění a nic se nemaže), ale z kořene
akce musí zmizet, aby je Immich nenačetl.

## What Changes

- Na pracovní ploše jde vybrané soubory (mřížka i lupa, včetně
  hromadného výběru) klávesou Del nebo tlačítkem označit k vyřazení
  a označení zase zrušit. Označení se ukládá do `_metadata.json`
  (`"vyradit": true` u souboru).
- Označené soubory jsou v mřížce i pásu lupy vizuálně odlišené
  a nepočítají se do lišty chybějících údajů.
- Úklid (průvodce i nově spustitelný z pracovní plochy) naplánuje
  přesun označených souborů do `k_odstraneni.ignored/` v kořeni akce se
  stejnými pravidly jako ostatní přesuny (nic se nepřepíše, kolize se
  blokuje, výsledek se ukáže). Ve vývojovém režimu se plán jen zobrazí.
- Po úspěšném přesunu se záznam souboru z `_metadata.json` odstraní;
  `.ignored` zůstává jediným záznamem o vyřazení.
- Údaje vyřazeného souboru se před odstraněním záznamu zapíšou do XMP
  sidecaru vedle souboru ve `k_odstraneni.ignored/`. Tag o vyřazení se
  nepíše; vyřazení značí jen složka.

## Capabilities

### New Capabilities

<!-- žádné -->

### Modified Capabilities

- `metadata-workspace`: označení souborů k vyřazení, jeho zobrazení
  a vynechání z lišty chybějících údajů.
- `event-cleanup`: přesun označených souborů do `k_odstraneni.ignored`,
  odstranění jejich záznamů a spuštění úklidu z pracovní plochy.

## Impact

- `fotoarchiv/cleanup.py` (plán a provedení), `fotoarchiv/app.py`
  (endpointy úklidu, úprava `_metadata.json` po provedení).
- `fotoarchiv/static/app.js` (Del, tlačítko, zobrazení, dialog úklidu),
  `static/inherit.js` (`missing` — lišta chybějících údajů, jen v JS).
- `README.md` (Podsložky a RAW, Datový model, Tok práce).
- `fotoarchiv/xmp.py` (sidecar vyřazeného souboru; export soubory
  s `vyradit` už vynechává).
