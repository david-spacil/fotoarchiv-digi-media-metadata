## Why

Ostrý test v produkčním režimu (6. 10. 2026) ukázal tři drobnosti na
pracovní ploše: hlavička při přepnutí stavu ukládání poskočí, datum
pořízení jde zadat jen psaním a tlačítko Dokončit akci vypadá u hotové
akce stejně, i když není co dokončovat.

## What Changes

- Hlavička (`<header>`) drží stálou výšku bez ohledu na text stavu
  ukládání (`Uloženo` / `Neuloženo` / `Ukládám…` / `Neuloženo – konflikt`).
- Pole Datum pořízení u souboru dostane vedle textového vstupu výběr
  z kalendáře. Zvolený den nahradí datum a zachová případný čas; datum
  bez času (WhatsApp) zůstane bez času.
- Tlačítko Dokončit akci je u dokončené akce neaktivní, dokud nejsou
  neuložené nebo neexportované změny či neaktuální sidecary. Text
  tlačítka ani stav u něj (`Dokončeno …`) se nemění.

## Capabilities

### New Capabilities

### Modified Capabilities
- `metadata-workspace`: dokončení akce jen při změnách; kalendář u data
  pořízení; stálá výška hlavičky.

## Impact

- `fotoarchiv/static/app.js` (stav ukládání, pole typu `datetime`,
  tlačítko Dokončit akci, stav exportu), `fotoarchiv/static/*.css`.
- Server, `_metadata.json` ani sidecary se nemění.
