## Context

Krok „Skupiny a autoři“ sdílí průvodce prvním otevřením akce
(`state.mode === "wizard"`) a import (`"import"`). Mřížku a výběr má
z pracovní plochy, ale lupu ne: obsluha kláves i dvojklik otevírají
lupu jen při `state.mode === "workspace"` a rozvržení kroku nemá
kontejner `#loupe`. Spec `metadata-workspace` to říká výslovně
(„krok nemá lupu ani skládací panel“).

Lupa plochy (`renderBig`) nejde v kroku použít beze změn:

| Část lupy plochy | Problém v kroku |
|---|---|
| `state.present` | import ho nemá → „Soubor chybí v kořeni akce“ |
| video přes `/api/akce/…/soubor/` | import nemá endpoint na originál |
| filmový pás, formulář, navigátor | v kroku je panel skupin, pás nic nepřidá |
| `setView("loupe")` | přepíná `#grid`/`#loupe`, krok `#loupe` nemá |

Náhledy jdou v obou režimech přes `thumbUrl(f, LARGE)` (import:
`/api/import/<id>/nahled/<cesta>?velikost=1600`, průvodce:
`/api/akce/<nazev>/nahled/…`). Vzor modálního zvětšení už existuje
v kroku Úklid (`folderSamples` → `zoom`, `dialog.sample`).

## Goals / Non-Goals

**Goals:**
- Zvětšit soubor v kroku a projít jím další soubory bez zavírání.
- Rozhodnout o vyloučení z importu přímo ve zvětšení.
- Fungovat na dotyku (tlačítka, ne jen klávesy a dvojklik).

**Non-Goals:**
- Přehrávání videa v kroku (nový endpoint importu na originál).
- Filmový pás, formulář, rámečky obličejů, přiblížení nad 1600 px.
- Změny lupy pracovní plochy, serveru a API.

## Decisions

### Modální `<dialog>`, ne lupa plochy
Okno je `<dialog class="steploupe">` otevřené `showModal()`, vložené
do `body` a po zavření odstraněné (jako `zoom` v Úklidu). Mřížka pod
ním zůstane, výběr se jen aktualizuje.
*Alternativa:* zobecnit `renderBig`/`setView` pro krok — vyžaduje
`#loupe` v rozvržení kroku, náhradu `state.present` a endpoint videa
(varianta 3 v issue); dražší a pás vedle panelu skupin nic nepřidá.
*Alternativa:* prosté zvětšení bez pohybu (varianta 1) — k další
fotce by se šlo přes zavření a šipku, při procházení desítek fotek
zbytečně pomalé.

### Vlastní obsluha kláves v okně
Globální obsluha kláves při otevřeném dialogu nic nedělá
(`dialog[open]`), takže okno má vlastní `keydown`: ←/→ ±1 v
`state.order` (bez přetečení), Home/End kraje, Del jen v importu,
Esc nativně zavře. Shift, Ctrl+A, ↑/↓ a PageUp/PageDown okno
ignoruje: výběr v lupě je vždy jen zobrazený soubor (jako lupa plochy
bez Shiftu) a řádky mřížky nejsou vidět. Cíl pohybu počítá čistá
funkce `vLupeKroku(order, current, klavesa)` v `pohyb.js` s testem.
Je-li nad oknem otevřený jiný dialog (dotaz na RAWy), obsluha nic
nedělá.

### Otevření
Enter (aktuální soubor; bez aktuálního nic), dvojklik na dlaždici
(ten soubor) a tlačítko „Lupa“ s ikonou `lupa` v panelu „Skupina (N
souborů)“ (aktuální soubor, není-li ve výběru, tak první vybraný
v pořadí mřížky). Tlačítko je v panelu, ne na dlaždici: na dotyku je
panel dosažitelný a dlaždice nemá kam ikonu dát bez kolize s ikonou
vyloučení.

### Zobrazení
Nejdřív se ukáže malý náhled (z cache prohlížeče), po načtení se
vymění za 1600 px; sousedé ±1 se přednačtou (jako `renderBig`).
Popisek: název souboru · „i / N“ · u videa „video“ · u vyloučeného
„vyloučeno z importu“. Vyloučený soubor je zašedlý jako dlaždice.
Okno je tmavé v obou režimech (jako lupa plochy).

### Vyloučení v okně
Del a tlačítko „Vyloučit z importu“ / „Vrátit do importu“ volají
stávající `toggleExcluded()` nad výběrem (= zobrazený soubor), takže
platí dotaz na RAWy i uložení k importu beze změny. Po návratu okno
překreslí stav zobrazeného souboru.

### Zavření
Esc, tlačítko × a klik na pozadí mimo fotku. Po zavření je aktuální
a jediný vybraný naposledy zobrazený soubor a mřížka je k němu
posunutá (`revealCurrent`), takže šipky v mřížce navazují.

## Risks / Trade-offs

- [Otevřená změna `mobilni-verze` říká, že krok skupin lupu nemá
  a ťuknutí jen vybírá] → tato změna ji nemění; kdo bude implementovat
  `mobilni-verze` po sloučení této, upraví požadavek „Dotykový výběr
  souborů“ (ťuknutí v kroku může otevřít lehkou lupu). Uvést v PR.
- [1600 px nestačí na posouzení ostrosti detailu] → stejná mez jako
  lupa plochy; přiblížení je mimo rozsah.
- [Video nejde přehrát] → záměr (volba uživatele); náhled a označení
  „video“ stačí k rozhodnutí o vyloučení duplicit a zjevně
  nepovedených záběrů.

## Open Questions

Žádné.
