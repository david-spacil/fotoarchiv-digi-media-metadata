## Why

Při popisu importu v kroku „Skupiny a autoři“ uživatel teprve vidí
náhledy a narazí na nepovedené fotky, duplicity jiného jména nebo
soukromé snímky. Dnes je může jen přenést a v akci pak označit
k vyřazení, takže se nechtěné soubory dostanou do archivu (u dokončené
akce je hned uvidí Immich). Issue #42.

## What Changes

- V kroku „Skupiny a autoři“ importu je klávesa Del (a tlačítko
  v panelu) přepínač vyloučit / vrátit: jsou-li všechna vybraná média
  vyloučená, vrátí je do importu, jinak je vyloučí. Popisek tlačítka
  se mění podle výběru („Vyloučit z importu“ / „Vrátit do importu“).
- Vyloučené médium zůstane v mřížce ve své skupině, zašedlé s ikonou;
  nepočítá se do „Importovat (N)“ ani do upozornění na skupiny bez
  autorů.
- Provedení vyloučený soubor nepřenese: zůstane v pracovním adresáři
  importu, nebo ve zdroji v `přetřídit`, stejně jako nepřenesený
  poškozený soubor. Výsledek ho uvede mezi nepřenesenými jako
  „vyloučeno“.
- Má-li vylučovaná fotka ve výběru RAW stejného jména, průvodce se
  zeptá, zda vyloučit i RAW; zrušení vyloučení fotky vrátí i její RAW.
- Seznam vyloučených se ukládá k importu (ne do archivu), přežije
  návrat k rozpracovanému importu a funguje i ve vývojovém režimu.
- Průvodce prvním otevřením akce se nemění: Delete tam dál nic nedělá.

## Capabilities

### New Capabilities

(žádné)

### Modified Capabilities

- `photo-import`: nové požadavky na vyloučení média v kroku skupiny
  a autoři (přepínač Del), počty a uložení vyloučených, vyloučení RAWu
  k fotce a vyloučené soubory při provedení.
- `metadata-workspace`: požadavek „Klávesy v kroku skupin“ — Delete
  v kroku importu vylučuje, v průvodci akce dál nic nedělá.

## Impact

- `fotoarchiv/importer.py`: seznam vyloučených v `import.json`, nový
  stav operace plánu a provedení, `defaults` je dál nabízí v mřížce.
- `fotoarchiv/app.py`: endpoint pro uložení seznamu vyloučených.
- `fotoarchiv/static/app.js` (+ čistá logika v malém modulu): Del,
  tlačítko, vzhled dlaždice, počet v tlačítku Importovat, dotaz na RAW,
  vyloučené ve výsledku a plánu; `style.css`.
- Unsorted import (`přetřídit`): vyloučený soubor zůstane ve zdroji,
  stránka Přetřídit ho dál nabízí.
- README (Import, průvodce akce), testy `tests/test_import.py`,
  `tests/test_app.py`, `tests/js/`.
- Archiv, `_metadata.json`, sidecary ani Immich se nemění.
