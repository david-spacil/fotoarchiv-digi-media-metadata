## Context

Editor typu `datetime` (`editor()` v `app.js`) je textový vstup
s kontrolou formátu a tlačítkem 📅, které přes `showPicker()` otevře
skrytý `<input type="date">`; zvolený den zapíše `pickDay` v
`fieldRow()` každému cíli zvlášť. Ostatní pole jdou přes `update()`,
které zapíše jednu hodnotu všem cílům. Pole `datum` existuje jen
u souboru a nedědí se.

## Goals / Non-Goals

**Goals:**
- Nativní výběr dne i času bez psaní formátu.
- Logika skládání hodnoty testovatelná v `node --test`.

**Non-Goals:**
- Vlastní kalendářový nebo časový widget.
- Změna `datum_od` / `datum_do` (už jsou `type="date"`).
- Validace na serveru (formát se nemění).

## Decisions

**Dva vstupy místo `datetime-local`.** `datetime-local` vynucuje čas,
takže by hodnotu bez času (WhatsApp) neuměl zobrazit ani uložit.
`date` + `time step="1"` hodnotu rozdělí na dvě nezávislé části;
prázdný `time` = jen datum. Sekundy (`step="1"`) jsou nutné, EXIF je
má.

**Zápis po částech, ne přes `update()`.** Oba vstupy zapisují každému
cíli zvlášť (zobecnění dnešního `pickDay`): den nahradí prvních 10
znaků, čas část za `T`. Prázdný den smaže klíč, prázdný čas zkrátí
hodnotu na 10 znaků. Čas se zapíše jen cílům, které mají den; vstup
času je vypnutý, pokud žádný cíl den nemá.

**Čisté funkce v novém modulu `static/datetime.js`.** Funkce
`withDay(value, day)`, `withTime(value, time)` a `parts(values)`
(společný den / čas výběru, nebo prázdno) bez DOM, aby šly testovat
v `tests/js/datetime.test.mjs` jako `inherit.js`. Alternativa
nechat je v `app.js` testovat nejde — `app.js` sahá na DOM při
importu.

**Rozdílné hodnoty.** Každý vstup ukazuje svou část, pokud je
u všech cílů stejná. Text vedle vstupů jako `ph-text` u `date`;
třída `mixed` a poznámka nad polem zůstávají z `fieldRow()`.

**Úklid.** Tlačítko 📅, skrytý `.picker`, fallback bez `showPicker()`
a jejich CSS se odstraní.

## Risks / Trade-offs

- [Chrome vrací čas bez sekund, když jsou nulové (`12:00`)] → formát
  `HH:MM` je platný, export ho zvládá; neopravovat.
- [Nativní vstupy zobrazují formát podle jazyka prohlížeče] →
  přijatelné, uložená hodnota je vždy ISO.
- [Rychlé psaní: `input` u `date` hlásí prázdno během rozepsaného
  data] → zapisovat na `change`, ne na `input`, aby rozepsaný den
  nesmazal hodnotu.
