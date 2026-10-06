## Why

Datum pořízení se zadává do textového pole ve tvaru
`RRRR-MM-DDTHH:MM:SS`; kalendář vybírá jen den a čas se píše ručně
s rizikem překlepu ve formátu. `datetime-local` se nepoužil, protože
neumí hodnotu bez času (WhatsApp). Dva samostatné nativní vstupy, den
a čas, tuto potíž nemají a zadání zjednoduší.

## What Changes

- Pole Datum pořízení: místo textového vstupu se skrytým kalendářem
  dva nativní vstupy — den (`date`) a čas (`time`, se sekundami).
- Prázdný čas znamená hodnotu jen s datem (WhatsApp); smazání času
  ponechá datum, smazání dne smaže celou hodnotu.
- Ve výběru více souborů: změna dne přepíše každému den a zachová jeho
  čas, změna času přepíše každému čas a zachová jeho den.
- Rozdílné hodnoty ve výběru se vyznačí textem vedle polí (nativní
  vstupy nemají placeholder).
- Formát uložené hodnoty v `_metadata.json` se nemění.

## Capabilities

### New Capabilities

### Modified Capabilities
- `metadata-workspace`: požadavek „Kalendář u data pořízení“ —
  samostatné zadání dne a času místo textu s kalendářem pro den.

## Impact

- `fotoarchiv/static/app.js` (editor typu `datetime`), `style.css`
  (styly `.datetime`, `.picker`, `.calendar`).
- Nový malý modul s čistými funkcemi pro skládání hodnoty a jeho test
  v `tests/js/`.
- `README.md`, sekce Aplikace → Tok práce (popis zadání data).
- Server, export XMP ani formát dat beze změny.
