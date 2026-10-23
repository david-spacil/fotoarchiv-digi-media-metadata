## Why

V kroku „Skupiny a autoři“ (import i průvodce prvním otevřením akce)
jsou vidět jen náhledy v mřížce. Kdo před importem prochází fotky
a rozhoduje, které vyloučit (neostré, duplicitní, soukromé), si je
nemůže zvětšit; krok podle specifikace lupu nemá. Issue #67.

## What Changes

- **Lehká lupa** v kroku „Skupiny a autoři“: modální okno přes stránku
  s velkým náhledem aktuálního souboru (1600 px), názvem a pořadím
  „i / N“. Otevře ji Enter, dvojklik na dlaždici a tlačítko „Lupa“
  v panelu u výběru (kvůli dotyku).
- V lehké lupě šipka vpravo/vlevo (a tlačítka ‹ ›) přejde na
  další/předchozí soubor v pořadí mřížky, Home/End na první/poslední;
  zobrazený soubor je aktuální a jediný vybraný. Esc, tlačítko ×
  a klik mimo fotku lupu zavřou; mřížka zůstane posunutá k aktuálnímu
  souboru.
- V kroku importu Del (a tlačítko v lupě) přepíná vyloučení
  zobrazeného souboru z importu podle stávajících pravidel včetně
  dotazu na RAWy; vyloučený soubor lupa ukáže zašedlý s označením.
  V průvodci akce Del v lupě nic nedělá.
- Video lupa nepřehrává, ukáže jen velký náhled s označením „video“.
- P v kroku dál nic nedělá; krok nemá skládací panel.
- Lupa pracovní plochy (pás, formulář, navigátor) se nemění, server
  a API také ne.

## Capabilities

### New Capabilities
<!-- žádné -->

### Modified Capabilities
- `loupe-view`: nový požadavek na lehkou lupu v kroku skupin
  (otevření, pohyb, zavření, vyloučení, video).
- `metadata-workspace`: požadavek „Klávesy v kroku skupin“ — Enter
  a dvojklik otevírají lehkou lupu, P dál nic.

## Impact

- `fotoarchiv/static/app.js` — klávesa Enter a dvojklik v kroku,
  tlačítko „Lupa“ v `groupTools`, nová funkce okna lehké lupy.
- `fotoarchiv/static/style.css` — vzhled okna (tmavé jako lupa).
- `fotoarchiv/static/pohyb.js` — čistá funkce cíle pohybu v lehké
  lupě + test v `tests/js/pohyb.test.mjs`.
- `docs/navod/import.md`, `docs/navod/pruvodce-akce.md` — popis kroku.
- Otevřená změna `mobilni-verze` počítá s tím, že krok skupin lupu
  nemá (ťuknutí jen vybere); po sloučení této změny ji bude potřeba
  upravit (viz design.md).
