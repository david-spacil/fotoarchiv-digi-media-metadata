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
- Vlastní barvy osob nastavitelné uživatelem a legenda barev.
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
- **Přepínač jako druhá dvojice tlačítek ve stylu `.views`.** Přepnutí
  zavolá `renderGrid()` (ten překreslí i pás) a zachová `state.sel`
  i `state.current`. Aktuální soubor se pak posune do viditelné oblasti.
  Vybraná hlavička skupiny (`state.group`) se při přepnutí na Podle
  data zruší a formulář přejde na akci. Hlavička skupiny tam totiž
  není vidět.
- **Značka autorů v obou zobrazeních, ne značka skupiny.** Po skupinách
  je příslušnost ke skupině vidět z oddílu. Podle data skupina (obvykle
  přístroj) při prohlížení nic nepřidá, autoři ano. Jedna značka v obou
  zobrazeních je také jednodušší kód i výklad. Alternativa: podle data
  značka skupiny (první verze změny) se ukázala jako zbytečná.
- **Značka jako pseudoelement s proměnnou `--stops`.** Rámeček
  (`border`) má jen jednu barvu na hranu, pruh autorů jich potřebuje
  víc. Dlaždice se značkou dostane třídu `mark` a inline proměnnou
  `--stops` (zarážky `linear-gradient`). V mřížce je pruh `::before`
  v levém 6px okraji (svisle dělený), v pásu `::after` 4px pod
  dlaždicí (vodorovně). Soubor bez autorů má
  třídu `noauth` se šrafováním (`repeating-linear-gradient`).
  Alternativa: `border-image` s gradientem. Ten se ale vztahuje na
  všechny hrany a kolidoval by s rámečkem výběru.
- **Paleta v CSS (`--p0`…`--p7`), barvu osoby určí pořadí.** Osoby
  jsou všichni výslední autoři souborů akce, sjednocení podle
  `nameKey()` (stejné porovnání jmen jako na serveru) a seřazení podle
  klíče. Index určuje barvu modulo 8. Barvy jsou tak v rámci akce
  stabilní, ale přidání nové osoby může barvy ostatních posunout. To
  u prohlížení nevadí. Alternativa: hash jména, ten dává častější
  kolize u akcí se 2–4 autory.
- **Čisté funkce v `sections.js`:** `personIndex(names, keyOf)` (klíč →
  index) a `stripeStops(colors, max = 3)` (zarážky pro rovnoměrné
  úseky; nad `max` jeden šedý úsek). Testují se v Node.
- **Překreslení po změně autorů.** Úprava pole `autori` na kterékoli
  úrovni překreslí mřížku i pás jako dosud úprava data, protože se
  dědí na všechny soubory pod ní.

## Risks / Trade-offs

- [Akce bez dat, např. ještě nezpracovaná] → Celá mřížka je jeden oddíl
  „Bez data“. Je to správné chování a zároveň připomínka, co chybí.
- [Hodně autorů v 6px pruhu → nečitelné proužky] → Nejvýš tři barevné
  úseky, zbytek šedý; popisek uvede `+N` a titulek dlaždice všechna
  jména.
- [8 barev a víc osob v akci] → Barvy se opakují. Rozliší je popisek
  s příjmením.
- [Přepnutí uprostřed výběru skupiny] → Výběr skupiny se změní na
  „nic“ (formulář akce). Uživatel to vidí hned v panelu, data se
  nemění.
