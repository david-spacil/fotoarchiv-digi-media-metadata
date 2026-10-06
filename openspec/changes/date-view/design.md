## Context

Mřížku i filmový pás skládá klient z jednoho seznamu oddílů
(`sections()` v `static/app.js`). Každý oddíl má hlavičku a soubory
seřazené podle zděděného data. Z oddílů vzniká `state.order`, ze kterého
čtou šipky v lupě, Shift-výběr i rozsah. Hlavička oddílu nese
`data-group`. Prázdná hodnota znamená „Bez skupiny“ a klik na ni vybere
soubory oddílu. Datum pořízení je řetězec `RRRR-MM-DD` nebo
`RRRR-MM-DDTHH:MM[:SS]` (viz `static/datetime.js`).

## Goals / Non-Goals

**Goals:**
- Zobrazení podle data jen jako jiné sestavení oddílů. Výběr, lupa,
  formulář a klávesy zůstanou beze změny.
- Rozdělení po dnech jako čistá funkce testovaná přes `node --test`.

**Non-Goals:**
- Ukládání volby na server nebo do `_metadata.json`.
- Vlastní barvy skupin nastavitelné uživatelem a legenda barev.
- Změny průvodce, lišty chybějících údajů a exportu.

## Decisions

- **Volba zobrazení v `state.layout` (`skupiny` | `datum`) a
  v `localStorage`.** Volba je osobní preference prohlížení, ne údaj
  o akci. Proto se ukládá do prohlížeče stejně jako jméno uživatele
  (`localStorage.jmeno`). Alternativa: hash v URL. Ta by přežila
  sdílení odkazu, ale komplikuje směrování a issue sdílení nežádá.
- **`sections()` vrací podle volby oddíly skupin, nebo dnů.** Oddíl
  dne má `gid: null` a nový klíč `day`. Hlavička dostane `data-day`.
  Klik na hlavičku bez skupiny vybere soubory oddílu podle jeho klíče.
  Dnes se hledá „první oddíl bez `gid`“, to se zobecní na vyhledání
  podle klíče oddílu. V průvodci (`state.mode !== "workspace"`) se
  použijí vždy skupiny.
- **Nový modul `static/sections.js`.** Bude exportovat čisté funkce
  `byDay(files, dateOf)` (oddíly `{ day, files }`, soubory bez data
  na konci s `day: null`, uvnitř dne řazení podle hodnoty a názvu)
  a `dayLabel(day)` (`út 28. 4. 2026`). Dny v týdnu budou pevné pole,
  ne `Intl`, aby výsledek nezávisel na ICU v Node ani v prohlížeči.
  Alternativa: přidat funkce do `datetime.js`. Ten ale řeší úpravu
  hodnoty pole, ne rozvržení plochy.
- **Barva skupiny podle pořadí skupiny v `groupIds()`.** Index určuje
  barvu z pevné palety (8 dobře odlišitelných odstínů) přes CSS
  proměnnou `--gc` na dlaždici. Proužek je levý okraj dlaždice v mřížce
  a spodní okraj v pásu. Barva je tak v rámci akce stabilní
  a nezávislá na názvu. Alternativa: hash názvu. Ten dá stabilitu mezi
  akcemi, ale častěji kolize u akcí s 2–3 skupinami.
- **Přepínač jako druhá dvojice tlačítek ve stylu `.views`.** Přepnutí
  zavolá `renderGrid()` (ten překreslí i pás) a zachová `state.sel`
  i `state.current`. Aktuální soubor se pak posune do viditelné oblasti.
  Vybraná hlavička skupiny (`state.group`) se při přepnutí na Podle
  data zruší a formulář přejde na akci. Hlavička skupiny tam totiž
  není vidět.

## Risks / Trade-offs

- [Víc než 8 skupin → opakované barvy] → Název skupiny v popisku
  dlaždice v mřížce rozliší skupinu vždy. V pásu se spoléhá na tooltip
  s názvem souboru a skupiny.
- [Akce bez dat, např. ještě nezpracovaná] → Celá mřížka je jeden oddíl
  „Bez data“. Je to správné chování a zároveň připomínka, co chybí.
- [Přepnutí uprostřed výběru skupiny] → Výběr skupiny se změní na
  „nic“ (formulář akce). Uživatel to vidí hned v panelu, data se
  nemění.
