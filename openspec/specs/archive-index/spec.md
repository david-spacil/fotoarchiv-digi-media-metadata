# archive-index Specification

## Purpose

Generovat z `_metadata.json` čitelný přehled všech akcí archivu pro
lidi, kteří archiv procházejí v Průzkumníku, místo ručně vedeného
`_metadata.xlsx`.

## Requirements

### Requirement: Soubory indexu
Aplikace SHALL generovat dva soubory indexu: `_INDEX.html`
a `_INDEX.md`. Oba SHALL obsahovat všechny složky akcí první úrovně
(vzor `YYYY-MM-DD název`) seřazené podle data sestupně, včetně akcí
bez `_metadata.json`. Údaje akce SHALL pocházet jen z `_metadata.json`
a ze souborů v kořeni složky akce; jiný zdroj (zejména
`_metadata.xlsx`) MUST NOT být čten.

#### Scenario: Zpracovaná i nezpracovaná akce
- **WHEN** archiv obsahuje akci `2026-09-14 Vzorová letní škola 2026`
  s `_metadata.json` a akci `2026-06-19 stará fara u Vzorné`
  bez něj
- **THEN** oba indexy obsahují obě akce, Vzorová letní škola první

#### Scenario: Akce bez metadat
- **WHEN** akce nemá `_metadata.json`
- **THEN** index u ní uvádí datum a název ze jména složky a počty
  fotek a videí, ostatní údaje zůstanou prázdné

### Requirement: Obsah indexu Markdown
`_INDEX.md` SHALL začínat nadpisem a upozorněním, že soubor je
generovaný automaticky, ruční úpravy se při dalším generování přepíšou
a údaje se opravují v aplikaci. Pod ním SHALL být jediná tabulka
v rámečku z čar (styl `fancy_grid`) se sloupci Datum, Akce, Místa,
Fotili, Foto, Video, jeden řádek na akci. Místa SHALL být jen místa
akce (`akce.mista`), bez míst jednotlivých souborů. Fotili SHALL
obsahovat zkrácená jména (`Příjmení J.`).

#### Scenario: Řádek akce
- **WHEN** akce `Konference Příkladné metody` od 8. 9. 2026 má místa
  akce `Markušovce` a `Spišská Nová Ves`, 108 fotek a 1 video
  a soubory s místem `Poprad`
- **THEN** její řádek má datum `2026-09-08`, místa `Markušovce;
  Spišská Nová Ves` bez `Poprad`, Foto 108 a Video 1

### Requirement: Obsah indexu HTML
`_INDEX.html` SHALL být jediný soubor bez odkazů na externí zdroje
a SHALL mít u každé akce kartu s titulní fotkou, datem, názvem,
stavem (*nezpracováno*, *rozpracováno*, *hotovo*), místy akce
i souborů, fotografy, účastníky, pojmenovanými osobami na fotkách
s počtem výskytů, počty fotek a videí a přístroji. Název a fotka SHALL
odkazovat na složku akce na disku, u skryté akce včetně přípony
`.ignored` (viz `event-visibility`); název akce SHALL být bez přípony.
Titulní fotkou SHALL být náhled prvního JPEG souboru v kořeni akce
podle abecedy; bez JPEG SHALL karta ukázat zástupný prvek. Bez
JavaScriptu MUST být všechny karty viditelné; s JavaScriptem SHALL
stránka nabídnout hledání nezávislé na diakritice a velikosti písmen
a filtry podle roku a stavu. HTML nemá viditelné upozornění na
generování; upozornění SHALL být jen v komentáři zdrojového kódu.

#### Scenario: Hledání bez diakritiky
- **WHEN** uživatel do hledání napíše `spisska`
- **THEN** zůstane viditelná karta akce s místem `Spišská Nová Ves`

#### Scenario: Bez JavaScriptu
- **WHEN** prohlížeč nespustí JavaScript
- **THEN** stránka ukazuje všechny karty akcí

#### Scenario: Odkaz na skrytou akci
- **WHEN** akce `2026-04-28 kontrola Naučné stezky` má složku s příponou
  `.ignored`
- **THEN** karta ukazuje název bez přípony a odkazuje na
  `./2026-04-28 kontrola Naučné stezky.ignored/`

### Requirement: Řazení autorů
Fotografové akce SHALL být v obou indexech seřazeni sestupně podle
počtu souborů akce, u kterých jsou ve výsledných (zděděných) autorech;
při shodě podle jména. Soubor s více autory SHALL započítat každému
z nich. Autor bez souboru MUST NOT být uveden.

#### Scenario: Autor s více fotkami první
- **WHEN** skupina se 100 soubory má autora `Příkladný, Daniel` a 5 souborů
  má přepsaného autora `Modelová, Zuzana`
- **THEN** index uvádí `Příkladný D.; Modelová Z.`

### Requirement: Okamžiky generování
Aplikace SHALL index přegenerovat po provedení importu, po exportu XMP
z aplikace (dokončení akce), po smazání akce do koše, jejím obnovení
a trvalém smazání (viz `event-trash`) a jednou na konci příkazu
`exportovat`. Uložení `_metadata.json` a kontrola exportu
nanečisto MUST NOT index generovat. Soubor indexu SHALL být zapsán
atomicky a jen tehdy, když chybí nebo se jeho obsah liší; obsah MUST
NOT obsahovat čas generování. Selhání zápisu indexu MUST NOT způsobit
selhání exportu ani importu; aplikace ho SHALL ohlásit jako varování.

#### Scenario: Import do nové akce
- **WHEN** import vytvoří akci `2026-10-06 nová akce` a zkopíruje do ní
  fotky
- **THEN** oba indexy obsahují akci `nová akce` jako *rozpracováno*
  s údaji akce a autory z importu a s počtem fotek z importu

#### Scenario: Smazání akce
- **WHEN** admin smaže akci `2026-10-06 nová akce` do koše
- **THEN** oba indexy ji už neobsahují

#### Scenario: Bez změny se nezapisuje
- **WHEN** se export spustí znovu bez změny metadat a souborů
- **THEN** soubory indexu zůstanou nezměněné včetně času změny

#### Scenario: Uložení akce
- **WHEN** uživatel uloží rozpracovanou akci bez exportu
- **THEN** index se nezmění

#### Scenario: Index nejde zapsat
- **WHEN** zápis `_INDEX.html` selže a sidecary se zapsaly
- **THEN** export skončí úspěšně s varováním o indexu


### Requirement: Umístění podle režimu
V produkčním režimu SHALL být index zapsán do kořene archivu a odkazy
na složky akcí SHALL být relativní. Ve vývojovém režimu SHALL být index
zapsán do pracovního adresáře `index/` a odkazy SHALL vést absolutně
do archivu. Soubor `_metadata.xlsx` MUST zůstat beze změny.

#### Scenario: Vývojový režim
- **WHEN** server běží bez `--zapis-do-archivu` a proběhne export
- **THEN** vznikne `.work/index/_INDEX.html` a kořen archivu se nezmění
