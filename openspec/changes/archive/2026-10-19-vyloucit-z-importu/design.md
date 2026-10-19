## Context

Viz proposal.md. Stav kódu (origin/main `f806e53`):

- V kroku „Skupiny a autoři“ importu ještě nic není v archivu: soubory
  leží v `.work/import/<id>/soubory/`, nebo ve zdroji `přetřídit/…`.
  Přenos spouští až Importovat (`executeImport` → `/api/import/<id>/
  provest` → `Imports.execute`), které plán sestaví znovu.
- Nepřenositelné soubory určuje jediné místo `Imports._blocked`
  (poškozené bez povolení, odebraná poloha); `iter_plan` jim dá stav
  `poskozeny`. Volí se v plánu i v provedení.
- `Imports.plan` ukládá `plan_ok` (cesty se stavem `ok`); z něj
  `defaults` skládá `soubory` mřížky a `reconcile` (`importdesc.js`)
  ze skupin vyhodí média, která v nich nejsou.
- Povolení podezřelých je vzor pro uložení volby k importu:
  `set_allowed` + `POST /api/import/<id>/poskozene`, klíč
  `povolene_poskozene` v `import.json`, odmítnutí během provádění
  (`check_idle`).
- Klávesnice: jediný `keydown` v `app.js`; větev `!ws` (krok skupin)
  dnes Delete ignoruje. Na ploše `toggleDiscard` přepíná `vyradit`
  nad výběrem (všechny označené → zrušit, jinak označit), dlaždice
  má třídu `discard`.
- RAWy v mřížce nejsou (jen fotky a videa); párování RAW s fotkou
  v kódu dosud neexistuje.

## Goals / Non-Goals

**Goals:**
- Vyloučit média z importu bez zápisu do archivu, vratně.
- Jedna serverová cesta pro plán i provedení (vyloučení nesmí jít
  obejít klientem).

**Non-Goals:**
- Mazání vyloučených souborů (ze stagingu ani ze zdroje).
- Vylučování v průvodci prvním otevřením akce (soubory už jsou
  v archivu, tam slouží označení k vyřazení na ploše).
- Vylučování v kroku přehled nebo plán, samostatný výpis RAWů
  v mřížce.

## Decisions

### Seznam vyloučených cest v `import.json`, vlastní endpoint

Klíč `vyloucene` (cesty ve výběru, seřazené, bez duplicit), endpoint
`POST /api/import/<id>/vyloucene` `{jmeno, vyloucene: [cesta…]}` →
`{vyloucene}`, server ho uloží jen pro cesty z výběru importu, během
provádění odmítne (`probiha`, 409), neplatný tvar 400. Vlastník
z relace (`owner()`), cizí import „nenalezen“ — jako u `poskozene`.

Alternativa: příznak `vyloucit` v `popis.soubory[název]`. Zamítnuto:
popis je klíčovaný názvem a obsahuje jen média mřížky, RAW by v něm
neměl kde být; provedení by muselo převádět názvy na cesty
a `check_description` bere popis jako data klienta, ne pravidlo
přenosu.

### Nový stav plánu `vylouceny`, `plan_ok` vyloučené dál obsahuje

`iter_plan` dostane množinu vyloučených cest a operaci, která by měla
stav `ok`, převede na `vylouceny` (blocked, důvod „vyloučeno
z importu“) až po určení duplicit a kolizí jmen. Tím vyloučení nemění,
co je duplicita nebo blokované (vyloučená kopie dál „zabírá“ obsah
i jméno, plán je stejný jako bez vyloučení, jen se jeden soubor
nepřenese). `plan_ok` se ukládá ze stavů `ok` i `vylouceny`, takže
`defaults` a `reconcile` vyloučená média v mřížce ponechají a jde je
vrátit.

Alternativa: vyloučené přidat do `_blocked` (stav `poskozeny`).
Zamítnuto: přepočet plánu by je vyřadil z `plan_ok`, `reconcile` by
je vyhodil ze skupin a vyloučení by v kroku nešlo zrušit; výsledek by
je navíc hlásil jako poškozené.

### Klient: Del i tlačítko, logika v malém modulu

Del ve větvi kroku importu (`!ws` a import) a tlačítko v `groupTools`
(aktivní s výběrem, `title: "Del"`) jsou jeden přepínač nad výběrem
jako `toggleDiscard`: všechna vybraná vyloučená → vrátit, jinak
vyloučit. Popisek tlačítka podle výběru „Vrátit do importu“, jinak
„Vyloučit z importu“. Čistá
logika — přepnutí množiny, páry fotka–RAW, počet pro Importovat —
v novém modulu `static/vylouceni.js` s testem
`tests/js/vylouceni.test.mjs`; `app.js` jen volá a ukládá (debounce
jako popis). Dlaždice: třída `excluded` (vzhled jako `discard`,
přeškrtnutý název, zašedlý náhled) a ikona v rohu s titulkem
„vyloučeno z importu“. Panel: řádek „Vyloučeno: N médií, M RAWů“.

### Párování RAW: stejné jméno bez přípony ve stejné složce výběru

Klíč páru = `cesta` bez přípony, porovnání bez ohledu na velikost
písmen (`DSC/P1503712.JPG` ↔ `DSC/P1503712.RW2`). Kandidáti jsou jen
RAWy, které by se přenesly (stav `ok` nebo `vylouceny` v posledním
plánu); `defaults` k tomu vrátí seznam RAWů plánu. Dotaz je potvrzovací
dialog s počtem RAWů a dvěma tlačítky „Vyloučit i RAWy“ / „Jen
fotky“; Esc = zrušit celé vyloučení. Zrušení vyloučení fotky vrací
i její vyloučený RAW bez dotazu (rozhodnutí agenta: vrácení je
bezpečný směr a druhý dialog by jen zdržoval).

Alternativa: RAW vylučovat vždy, nebo nikdy. Uživatel zvolil dotaz.

### Vyloučené soubory po provedení zůstávají

Jako nepřenesené poškozené: nahraný soubor zůstane ve stagingu
(`_moved` ho neodebere, import tedy není `zahozeno`), zdrojový zůstane
v `přetřídit` (počítá se do `zdroj_zbyva`, import se nezruší).
Uklidí je zahození importu nebo smazání neaktivního importu po 7 dnech.

## Risks / Trade-offs

- [Import zůstane mezi rozpracovanými jen kvůli vyloučeným souborům]
  → Výsledek vyloučené uvede zvlášť; import jde zahodit ze seznamu
  rozpracovaných a staré importy maže start serveru po 7 dnech.
- [Vyloučený soubor nahrané složky zabírá místo ve `.work/`] → stejné
  jako u poškozených; přijato.
- [Fotka a RAW v jiné podsložce výběru se nespárují] → přijato, párování
  podle složky odpovídá tomu, jak fotoaparát soubory ukládá; jinde
  uživatel RAW nevyloučí (není v mřížce) — zapsáno v Non-Goals.
- [Klient pošle seznam se smyšlenými cestami] → server je odfiltruje
  proti výběru importu.
