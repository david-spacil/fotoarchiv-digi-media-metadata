## Context

Hlavička (`header()` v `app.js`) je flex řádek: značka, `.paths`
s `flex: 1`, stav ukládání `#save-status` a jméno uživatele. Cesta
k archivu je dlouhá a `.paths` se smí zalomit; `#save-status` nemá
pevnou šířku.

Datum pořízení je pole typu `datetime`: textový vstup s kontrolou
`RRRR-MM-DD` nebo `RRRR-MM-DDTHH:MM[:SS]`.

Stav exportu drží `state.exportNote` (text) a `state.exportVersion`;
třída `pending` u `#export-status` se dnes odvozuje regulárním výrazem
z textu. Tlačítko Dokončit akci je vypnuté jen bez zámku.

## Goals / Non-Goals

**Goals:**
- Odstranit poskakování hlavičky bez změny jejího obsahu.
- Kalendář jako doplněk psaní, ne náhrada.

**Non-Goals:**
- Výběr času v kalendáři; čas se dál píše ručně.
- Kalendář u `datum_od` / `datum_do` (už jsou `type="date"`).
- Změna textů stavu ukládání nebo exportu.

## Decisions

**Hlavička.** Předpoklad: delší text stavu („Neuloženo“ oproti
„Uloženo“) zúží `.paths` a dlouhá cesta se zalomí na druhý řádek.
Ověřit v prohlížeči před opravou. Oprava: `#save-status` dostane
`white-space: nowrap` a `min-width` podle nejdelšího běžného textu,
`.paths` `min-width: 0`, `white-space: nowrap`, `overflow: hidden`
a `text-overflow: ellipsis` (celá cesta v `title`). Alternativa „jen
min-width u stavu“ nestačí na úzkém okně; ořez cesty řeší obojí.
Pokud se příčina ukáže jinde, oprava se upraví, požadavek ve
specifikaci platí.

**Kalendář.** Vedle textového vstupu tlačítko 📅, které otevře skrytý
`<input type="date">` přes `showPicker()`. Zvolený den nahradí prvních
10 znaků hodnoty (nebo ji vytvoří), čas zůstane. Alternativa
`type="datetime-local"` neumí hodnotu bez času (WhatsApp) a vynucovala
by čas; vlastní kalendářový widget je zbytečná práce. U výběru
s rozdílnými hodnotami se den přepíše každému souboru zvlášť, se
zachováním jeho času — jde mimo běžné `update()` jedné hodnoty.

**Dokončit akci.** Zavést explicitní příznak „je co exportovat“ místo
regulárního výrazu nad textem: pravda, když je `state.dirty`, verze
`_metadata.json` se liší od `exportVersion`, kontrola nanečisto hlásí
neaktuální sidecary, nebo poslední export selhal. Tlačítko je vypnuté,
když je akce dokončená a příznak je nepravdivý (nebo bez zámku).
Příznak použije i třída `pending` u `#export-status`. Přepočet při
`setStatus()` / `renderExportStatus()`, aby reagoval na první změnu.

## Risks / Trade-offs

- [`showPicker()` nemusí být v každém prohlížeči] → fallback: tlačítko
  zaostří skrytý vstup; Chrome a Firefox ho podporují.
- [Ořez cesty v hlavičce skryje její konec] → plná cesta v `title`.
- [Kontrola nanečisto chybí (např. selhala)] → považovat za „je co
  exportovat“, tlačítko zůstane aktivní.
