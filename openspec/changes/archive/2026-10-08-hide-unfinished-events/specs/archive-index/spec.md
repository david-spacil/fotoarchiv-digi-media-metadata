## MODIFIED Requirements

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
- **WHEN** akce `2026-04-28 kontrola Stezky` má složku s příponou
  `.ignored`
- **THEN** karta ukazuje název bez přípony a odkazuje na
  `./2026-04-28 kontrola Stezky.ignored/`
