# Design

## Context

Klávesy plochy obsluhuje jediný handler na `document` (`app.js:450`).
Vrátí se hned, když není `state.mode === "workspace"`, když je fokus
v `input/textarea/select` nebo když je otevřený `<dialog>`. Šipky
vlevo/vpravo volají jen v lupě `step(dir, extend)` (`app.js:2234`).
Ta pracuje nad `state.order`, tj. pořadím souborů mřížky
(`renderGrid`, `app.js:1469`), stejným na ploše, v průvodci i v importu.

Mřížka je flex se zalamováním (`.tiles`, `style.css:563`), každý oddíl
má vlastní `.tiles`. Dlaždice jedné řady flexu mají stejný `top`,
výšku mají danou proměnnou `--tile`, poslední řada oddílu bývá
neúplná. Počet sloupců závisí na šířce okna, panelu a velikosti
dlaždic, takže sousedy nahoru/dolů nejde spočítat z pořadí.

Zbytek stavu, o který se změna opírá:

| Místo | Dnes |
|---|---|
| `tile()` (`app.js:1420`) | `tabindex` jen na ploše, třída `selected`, žádná `current` |
| `select()` (`app.js:1539`) | `current` přepíná jen u `#film .ftile` |
| `clickFile()` | nastaví `state.current` a kotvu |
| `setView("loupe")` | aktuální = `state.current`, jinak první vybraný/první |
| `renderGroupsStep()` (`app.js:3843`) | průvodce i import, `#grid` s hlavičkami `h3.ghead`, nuluje `current` |
| `:focus-visible` (`style.css:156`) | obrys `--focus`, na ploše ukáže překryv `.ov` |
| `tests/js/contrast.test.mjs` | kontrast dvojic tokenů pro oba režimy |

## Goals / Non-Goals

**Goals:**
- Pohyb a výběr klávesnicí v mřížce plochy a kroku „Skupiny a autoři“.
- Jeden pojem aktuálního souboru, vyznačený v mřížce i v pásu lupy.
- Nahoru/dolů, Home/End, PageUp/PageDown a Ctrl+A i v lupě.

**Non-Goals:**
- Klávesy v navigátoru akce, v nástroji pojmenování a v našeptávání.
- Dotykové ovládání.
- Delete, Enter a P v kroku skupin.

## Decisions

### Jeden handler, rozšířený o krok skupin

Stávající handler se jen rozšíří: kromě plochy reaguje
i v `state.mode` `wizard` a `import`, když stránka má `#grid` (ta
existuje jen v kroku „Skupiny a autoři“). Pohybové klávesy, Ctrl+A
a Esc (zruší výběr) platí všude. Delete, P a Enter zůstávají jen na
ploše. Kontroly polí formuláře a otevřeného dialogu zůstanou, takže
Ctrl+A v poli dál označí text a zkratky nástroje pojmenování se
nemíchají.

*Alternativa:* vlastní `keydown` na `#grid`. Zamítnuto: handler by
reagoval jen při fokusu v mřížce, ne po kliknutí na lištu nebo do
prázdna, a kontroly by se psaly dvakrát.

### Cíl pohybu jako čisté funkce v `static/pohyb.js`

Nový modul bez DOM, testovaný v `tests/js/pohyb.test.mjs`:

- `klavesa(e)` → `{ druh, smer }` nebo `null`. Druhy: `vodorovne`
  (←/→), `svisle` (↑/↓), `stranka` (PageUp/PageDown), `kraj`
  (Home/End), `vse` (Ctrl+A, na Macu Cmd+A). Alt, Ctrl a Meta
  u pohybových kláves vrátí `null`, aby nepřebíraly zkratky prohlížeče.
- `radek(rects, i, smer)`: obdélníky dlaždic v pořadí `state.order`.
  Řádky se rozliší podle `top` (tolerance 1 px na subpixely). Cílový
  řádek je nejbližší nad/pod, v něm dlaždice s nejbližším vodorovným
  středem (při shodě levější). Bez řádku vrátí `i`. Protože pracuje
  s polohou všech dlaždic, přechod přes předěl oddílu ani hlavičky
  průvodce nepotřebuje zvláštní případ.
- `stranka(rects, i, smer, vyska)`: první řádek, jehož `top` je aspoň
  o `vyska` (výška `#grid`) dál, jinak poslední/první řádek; v něm
  nejbližší sloupec.
- `oddil(order, secOf, i, smer)`: pro lupu, začátek aktuálního nebo
  předchozího oddílu, začátek dalšího oddílu.
- `naPas(sirkaPasu, sirkaDlazdice)`: počet souborů na šířku pásu,
  nejméně 1.

*Alternativa (rozhodnutí 2b v #37):* nahoru/dolů o počet sloupců
v pořadí. Zamítnuto: u neúplného posledního řádku oddílu skáče do
jiného sloupce a počet sloupců stejně musí zjistit z DOM.

### `moveTo(f, extend)` místo `step`

`step` se zobecní na cílový soubor: bez Shiftu výběr jen na `f`
a kotva `f`, se Shiftem `range(kotva, f)` a kotva zůstane (bez platné
kotvy se jí stane výchozí soubor). Vodorovný pohyb, řádek, stránka,
kraj i oddíl jen spočítají `f` a volají `moveTo`.

Výchozí soubor je `state.current`, i když je mimo obrazovku.
`getBoundingClientRect` dá polohu i dlaždicím mimo viditelnou část
mřížky, takže výpočet nezávisí na posunu. Když `state.current` není
v `state.order`, šipky a stránka skončí na prvním souboru, Home/End na
prvním/posledním.

### Vyznačení aktuálního souboru třídou `current`

`tile()` a `select()` přidají `current` i dlaždicím `#grid .tile`,
stejně jako dnes v pásu. Třída se odvozuje ze `state.current`, takže
zůstane i při fokusu ve formuláři. Vzhled: vnitřní stín
`box-shadow: inset 0 0 0 2px var(--current)`, který nekoliduje s okrajem
výběru (`border-color`) ani s obrysem poškození (`outline`). Nový token
`--current` pro oba režimy se přidá do `contrast.test.mjs` proti
`--tile-surface`, `--selected` a `--stage` (grafika 3 : 1).

*Alternativa (3a v #37):* jen fokus prohlížeče. Zamítnuto: kliknutím do
formuláře značka zmizí a po kliknutí myší prohlížeč `:focus-visible`
neukáže, takže by nebylo vidět, kde Shift+šipka začne.

### Fokus a posun

Po pohybu v mřížce dostane aktuální dlaždice
`focus({ preventScroll: true })` a pak
`scrollIntoView({ block: "nearest" })`. Fokus z klávesnice ukáže
`:focus-visible` a na ploše překryv s názvem. V lupě se fokus nemění,
pás posune `revealCurrent` jako dnes.

`focusin` na `#grid` udělá fokusovanou dlaždici aktuální bez změny
výběru a jen přepne třídy `current` (bez `renderPanel`). Tabulátor tak
nezruší výběr, když uživatel přechází z lišty do mřížky, a Enter otevře
lupu na fokusované dlaždici. Při kliknutí přijde `focusin` před
`click`; `clickFile` pak nastaví totéž, takže se nic nemění.

V kroku skupin dostanou dlaždice `tabindex="0"` stejně jako na ploše.

### Ctrl+A a Esc

Ctrl+A vybere `state.order`, skupinu zruší (`select(set, null)`),
aktuální soubor ani kotvu nemění a zabrání výchozímu označení textu
stránky. Esc v kroku skupin volá totéž co Esc v mřížce plochy:
`select(new Set(), null)`.

## Risks / Trade-offs

- **Šipky, PageUp/PageDown a Home/End už mřížku nativně neposouvají.**
  Mřížka se posouvá jen s aktuálním souborem; posun bez změny výběru
  zůstává kolečku a posuvníku.
- **Velká akce:** `radek` a `stranka` čtou obdélníky všech dlaždic
  (stovky `getBoundingClientRect` na stisk). Měřit se bude
  v prohlížeči na akci s ~500 soubory. Kdyby byl stisk znatelně pomalý,
  přejde se na čtení jen oddílu aktuálního a sousedních oddílů.
- **Fokus na videu v lupě:** handler přebírá i Home/End/PageUp/PageDown
  při fokusu na přehrávači, jako dnes šipky. Ovládání videa zůstává
  myší.
- **Tab a výběr:** po tabulátoru může být aktuální soubor mimo výběr,
  takže lupa ukáže jiný soubor, než upravuje formulář. Stejná situace
  už dnes vzniká po Ctrl+kliku; vyznačení `current` a `selected` je
  rozlišuje.
