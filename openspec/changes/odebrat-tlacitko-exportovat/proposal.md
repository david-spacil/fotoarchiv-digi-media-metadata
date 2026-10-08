## Why

Tlačítko Exportovat na pracovní ploše je od skrytí nedokončených akcí
před Immichem zbytečné: export rozpracované akce Immich nevidí a
u dokončené akce po úpravě stačí znovu Dokončit akci (issue #20).
Opakované dokončení ale dnes není bezpečnou náhradou exportu — přepíše
datum dokončení a při selhání exportu vrátí `dokonceno` na `null`,
přestože složka akce už je pro Immich zveřejněná.

## What Changes

- **BREAKING (UI, API):** pracovní plocha už nemá tlačítko Exportovat;
  endpoint `POST /api/akce/<akce>/export` se odebírá. Příkaz
  `python -m fotoarchiv exportovat` (dávka, `--obliceje`) zůstává.
- Opakované dokončení dokončené akce nemění `dokonceno`: hodnota je
  datum prvního dokončení.
- Selže-li při opakovaném dokončení zápis sidecaru, akce zůstane
  dokončená (`dokonceno` se nevrací) a plocha chybu ukáže; tlačítko
  Dokončit akci zůstane aktivní, dokud export neprojde. Při prvním
  dokončení se chování nemění (selhání = akce není dokončená).
- Stav exportu (kontrola nanečisto, „neexportované změny“, výsledek
  exportu, upozornění na vývojový režim) se ukazuje u tlačítka Dokončit
  akci.
- README a hlavní specifikace přestanou tlačítko Exportovat zmiňovat.

## Capabilities

### New Capabilities

Žádné.

### Modified Capabilities

- `metadata-workspace`: Dokončení akce (datum prvního dokončení,
  selhání u dokončené akce), Stav exportu na ploše (u tlačítka Dokončit
  akci); odebírá se Export z plochy.
- `archive-index`: Okamžiky generování (bez tlačítka Exportovat).

## Impact

- `fotoarchiv/app.py` (endpointy `/export` a `/dokoncit`),
  `fotoarchiv/static/app.js` (lišta plochy, `runExport`),
  `tests/test_app.py`, README (Tok práce, Výstupy, index).
- `_metadata.json`: formát se nemění; význam `dokonceno` se upřesňuje
  na datum prvního dokončení.
- Mimo rozsah: historie dokončení a verzování `_metadata.json` (#21).
