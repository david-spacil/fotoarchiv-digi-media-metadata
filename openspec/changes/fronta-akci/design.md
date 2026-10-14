## Context

Seznam akcí kreslí `showList()` v `fotoarchiv/static/app.js` jako
tabulku z `GET /api/akce` (`Workspace.list_events()`
v `fotoarchiv/archive.py`). Výpis už u každé akce dělá `scandir`
kořene a načte `_metadata.json`; chybějící pole (`model.incomplete`)
ale počítá jen u *hotovo*. Zámky jsou v paměti serveru
(`lock.Locks`, `holder()` vrací jméno a čas, ne relaci); výpis o nich
neví. Náhledy servíruje `GET /api/akce/<název>/nahled/<soubor>` s cache
v `.work/cache` podle (cesta, velikost, mtime).

Dokončení je `finishEvent()`: `flushSave()`, `missingItems()` →
`confirmDialog`, pak `POST /api/akce/<název>/dokoncit`; výsledek kreslí
`renderExportStatus()` na ploše. Směrování je `route()` nad
`location.hash`. Uložení je `PUT /api/akce/<název>/metadata`
(`akce_save`), které už přebírá `obliceje` z uložené verze
(`model.keep_faces`).

## Goals / Non-Goals

**Goals:**
- Jeden výpis `GET /api/akce` nese vše pro kartu i filtry; klient
  filtruje, hledá a řadí bez dalších dotazů.
- Kontrolní stránka sdílí výpočty s plochou (`missing()`, nálezy,
  poškozené, kontrola nanečisto) — žádná druhá implementace.

**Non-Goals:**
- Stránkování výpisu nebo cache výpisu na serveru.
- Úpravy metadat na kontrolní stránce (jen odkazy na plochu).
- Hromadné dokončení více akcí.
- Zpětné doplnění `upravili` u existujících akcí.

## Decisions

**Hotovost v Pythonu vedle `incomplete`.** Nová čistá funkce
`model.completeness(doc, present)` vrátí
`{"autori": [vyplneno, celkem], "datum": …, "misto": …}` přes stejné
`resolve()`; `incomplete()` se z ní dá odvodit a zůstane kvůli
stávajícím volajícím. JS verze se nedělá — hotovost potřebuje jen
seznam a ten ji dostane ze serveru. Fixtury dědění se nemění.
Alternativa — počítat v klientu z celých `_metadata.json` — by
znamenala posílat stovky dokumentů.

**Rozšíření položky výpisu** (klíče přibývají, stávající zůstávají):
`hotovost` (výše, `null` u *nezpracováno*), `ukazky` (≤ 4 názvy
souborů rovnoměrně z seřazených `present` bez `vyradit`),
`upravili` (objekt z dokumentu nebo `{}`), `drzitel`
(`{"jmeno", "vase"}` nebo `null`). `chybi` se dál počítá jen
u *hotovo* (štítek „nekompletní“), ale nově z `completeness`.
`drzitel` doplňuje `app.py` (Workspace o zámcích neví); `vase` určí
porovnáním s relací, kterou klient pošle v `?relace=` — relace sama
se do odpovědi nedostane.

**`upravili` zapisuje server v `akce_save` a `akce_finish`** stejně
jako `keep_faces`: vezme `upravili` z uložené verze, přepíše položku
jména z `g.user` (stejné jméno jako u zámku) na
`datetime.now().isoformat(timespec="seconds")` a uloží. Funkce
`model.touch(doc, stored, jmeno, cas)` je čistá a testuje se
v `test_model.py`. `xmp.py` i `index.py` pole nečtou, takže se do
výstupů nedostane bez dalšího kódu; ověří se testem. Alternativa —
záznam v `.work` — zamítnuta uživatelem (údaj má přežít přesun
serveru).

**Náhledy líně přes `loading="lazy"`** na `<img>` s existující URL
náhledu (malá velikost). Prohlížeč sám odloží načítání karet mimo
obrazovku; IntersectionObserver není potřeba. Výběr ukázek na serveru
(ne v klientu), protože klient seznam souborů akce nemá.

**Filtry, hledání a řazení v klientu** nad `state.events`. Stav se drží
v hash adrese seznamu (`#/?filtr=…&hledat=…&razeni=…`), takže návrat
z plochy (tlačítko ← Akce, zpět v prohlížeči) ho zachová a jde sdílet
odkazem. Normalizace hledání přes stejnou funkci bez diakritiky, jakou
používá porovnání jmen v klientu (pokud existuje; jinak
`normalize("NFD")` a odstranění diakritiky). „Moje“ = jméno
přihlášeného uživatele (`/api/ja`) v klíčích `upravili`, nebo
`drzitel.vase`.

**Kontrolní stránka jako nová route** `#/akce/<název>/dokonceni`
v `route()`. Plocha a stránka sdílejí `state` akce (detail, doc,
verze, zámek, heartbeat): přechod mezi nimi nemění `state.name`,
takže zámek ani heartbeat se neuvolní. Přímé otevření adresy načte
akci stejně jako plocha (detail + zámek) a jen vykreslí jinou
obrazovku. Odkazy nápravy přepnou hash na plochu a předají výběr
přes stávající `select()`/`scrollToSection()` po vykreslení (obdoba
dnešních položek `missingItems()`, které už `onclick` mají).
`finishEvent()` přestane volat `confirmDialog`; volá ho tlačítko
stránky a výsledek kreslí stránka místo `renderExportStatus()`
(plocha dál ukazuje stav exportu u svého tlačítka). Alternativa —
samostatný modul stránky s vlastním načítáním akce — by duplikovala
zámek a heartbeat.

**Položky kontrol z `missingItems()`** rozšířené o stav a skupinu
(údaje akce / soubory / nálezy / poškozené / k vyřazení / export),
aby navigátor, plocha i stránka čerpaly z jednoho seznamu.

**Vzhled karet nejdřív prototypem** (artifacts, reálná data z výpisu
archivu, 2–3 varianty karty a rozložení filtrů); implementace UI až po
výběru.

## Risks / Trade-offs

- [Výpis dražší: `resolve()` pro každý soubor každé akce s metadaty]
  → stovky akcí × stovky souborů jsou desítky tisíc slovníkových
  operací, řádově desítky ms; změří se na kopii archivu
  (`.work` + `--archiv`) před a po. SMB se nečte víc než dnes.
- [Studená cache náhledů: první otevření seznamu čte originály
  z SMB] → jen viditelné karty (`loading="lazy"`), 4 na kartu;
  cache pak platí i pro plochu.
- [Každé automatické uložení mění `upravili` → mění verzi
  `_metadata.json`] → verze se mění při uložení tak jako tak;
  „změněno po exportu“ porovnává verzi exportu, takže se chová jako
  dosud.
- [`upravili` obsahuje jména kolegů v archivu] → jsou to tytéž
  jména jako autoři; do sidecarů ani indexu nejdou.
- [Konflikt verzí: server mění dokument, klient drží starou verzi
  `upravili`] → klient pole neposílá ani nezobrazuje na ploše;
  server ho vždy bere z uložené verze, takže klientova kopie nevadí.
- [Odkaz na adresu kontrolní stránky u nezpracované akce] →
  přesměrování na plochu (průvodce), viz spec.

## Migration Plan

Bez migrace dat: akce bez `upravili` jsou platné, pole vznikne prvním
uložením. Nasazení běžným `docker compose up -d --build`; návrat na
předchozí verzi pole `upravili` ignoruje (klient ho posílá zpět
s dokumentem a `model.clean` neznámé klíče neořezává).

## Open Questions

- Přesné rozložení karty a filtrů — rozhodne prototyp (nemění spec).
