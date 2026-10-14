## Why

Ve velké akci (stovky fotek, desítky skupin) se plocha prochází
posouváním mřížky: hlavičky skupin jsou mezi dlaždicemi a co kde
chybí, ukazuje jen souhrn v liště. Formulář ukazuje jen jednu úroveň
(akce, skupina, nebo výběr), takže oprava autora skupiny při práci se
soubory znamená přepnout výběr. Navazuje na archivovanou změnu
`graficky-overhaul` (tokeny, jedna lišta akce, skládací panel).

## What Changes

Odsouhlasený směr (varianty A a B z porovnání 2026-10-13, s dlaždicemi
s překryvem):

- **A – navigátor akce:** vlevo úzký sloupec oddílů akce (skupiny,
  nebo dny podle přepínače zobrazení) s počtem souborů, barvami
  autorů a tím, co v oddílu chybí. Klik skočí na oddíl a vybere ho.
  Hlavičky skupin z mřížky ubudou; stav chybějících údajů se přesune
  k oddílům. Přesun vybraných souborů do skupiny tažením na oddíl.
- **B – formulář jako kaskáda dědění:** panel ukazuje pod sebou
  vrstvy akce → skupina → výběr; vrstvy nad výběrem sbalené na
  souhrn, upravitelné na místě. U pole je vidět, ze které vrstvy
  hodnota teče.
- **Dlaždice s překryvem:** bez popisků pod náhledem; stav, autoři
  a vyřazení jako překryv v rohu, název a datum při najetí. Hustší
  mřížka.
- Sada ikon (inline SVG) místo části textových tlačítek.

## Capabilities

### New Capabilities

(upřesní se se specifikací)

### Modified Capabilities

- `metadata-workspace`: rozvržení plochy, lišta chybějících údajů,
  formulář podle výběru, mřížka a výběr, značka autorů na dlaždici.
- `loupe-view`: navigátor a kaskáda i v lupě (upřesní se).

## Impact

- `fotoarchiv/static/app.js`, `style.css` (plocha, mřížka, panel).
- `README.md`, oddíl Aplikace.
- Server a datový model beze změny.

## Otevřené otázky (před specifikací)

Podle domluvy se nejdřív odsouhlasí informační architektura a data
navigátoru, pak vzhled; varianty jako funkční prototyp s reálnými
daty.

- Co přesně nese řádek oddílu v navigátoru (počty, chybějící údaje,
  autoři, náhled) a jak se chová v zobrazení podle data.
- Zůstane lišta chybějících údajů vedle navigátoru (souhrn akce), nebo
  zanikne?
- Kaskáda: které vrstvy jsou při výběru souborů rozbalené a jak se
  zobrazí výběr ze dvou skupin.
- Pořadí: B (kaskáda) může jít samostatnou změnou po A.
- Navazuje na `import-a-popis` (sdílený krok skupiny a autoři);
  implementovat až po něm.
