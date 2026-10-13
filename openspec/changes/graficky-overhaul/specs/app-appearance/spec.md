## Purpose

Dát klientovi jednotný vizuální systém (barvy, typografie, komponenty)
čitelný ve světlém i tmavém prostředí, na noteboocích i velkých
monitorech, a umožnit porovnat varianty vzhledu v běžící aplikaci.

## ADDED Requirements

### Requirement: Jednotný vizuální systém
Všechny stránky klienta (seznam akcí, průvodce, pracovní plocha, lupa,
import, přetřídit, nastavení, přihlášení a změna hesla) SHALL používat
jednu sadu barev, typografie a komponent: tlačítka, štítky stavu, čipy,
formulářová pole, dialogy, upozornění a kroky průvodce. Stejný význam
(např. chyba, varování, hotovo, vybráno) MUST mít na všech stránkách
stejnou barvu.

#### Scenario: Štítek stavu
- **WHEN** seznam akcí ukazuje akci *hotovo* a plocha ukazuje úspěšné
  dokončení
- **THEN** oba používají tutéž barvu pro „hotovo“

#### Scenario: Přihlášení
- **WHEN** uživatel otevře stránku přihlášení
- **THEN** tlačítko, pole a upozornění vypadají stejně jako v aplikaci

### Requirement: Kontrast textu
Text a ovládací prvky SHALL mít ve všech variantách vzhledu a v obou
režimech (světlý, tmavý) kontrast vůči pozadí aspoň 4,5 : 1 (běžný
text) a 3 : 1 (velký text, okraje polí, ikony). Barvy osob v pruhu
autorů MUST zůstat navzájem rozlišitelné i na tmavém pozadí.

#### Scenario: Zděděná hodnota v tmavém režimu
- **WHEN** formulář v tmavém režimu ukazuje zděděný popis jako
  zástupný text
- **THEN** text má vůči poli kontrast aspoň 4,5 : 1

### Requirement: Tmavý režim podle systému
Klient SHALL ve výchozím vzhledu respektovat nastavení světlého nebo
tmavého režimu operačního systému. Náhledy fotek MUST se nebarvit ani
neinvertovat.

#### Scenario: Systém v tmavém režimu
- **WHEN** operační systém má zapnutý tmavý režim a uživatel otevře
  seznam akcí
- **THEN** stránka je tmavá a čitelná, náhledy fotek beze změny

### Requirement: Varianty vzhledu k porovnání
Klient SHALL nabízet kromě výchozího vzhledu varianty `b` (Temná
pracovna: neutrálně tmavá mřížka, lupa i lišty) a `c` (Katalogová
karta: světlé teplé pozadí, výraznější typografie). Parametr adresy
`?vzhled=b` nebo `?vzhled=c` SHALL variantu zapnout a prohlížeč si ji
SHALL pamatovat i pro další stránky a po obnovení; `?vzhled=a` SHALL
vrátit výchozí vzhled. Neznámá hodnota MUST se ignorovat. Varianta
MUST NOT měnit rozvržení, chování ani klávesové zkratky — jen vzhled.

#### Scenario: Zapnutí varianty
- **WHEN** uživatel otevře `/?vzhled=b` a pak přejde na plochu akce
- **THEN** seznam akcí i plocha jsou ve variantě Temná pracovna

#### Scenario: Volba přetrvá
- **WHEN** uživatel zvolil variantu `c`, zavře prohlížeč a znovu otevře
  aplikaci bez parametru
- **THEN** aplikace je ve variantě Katalogová karta

#### Scenario: Návrat na výchozí
- **WHEN** uživatel otevře `/?vzhled=a`
- **THEN** aplikace je ve výchozím vzhledu a zůstane v něm

#### Scenario: Neznámá hodnota
- **WHEN** uživatel otevře `/?vzhled=x`
- **THEN** vzhled zůstane, jaký byl

### Requirement: Podporovaná šířka okna
Pracovní plocha SHALL být použitelná bez vodorovného posouvání stránky
v okně od 1280 × 720 CSS px (notebook se škálováním) po široké
monitory: mřížka, formulář i lišta akce MUST být vidět a ovladatelné.
Na širokém monitoru SHALL mřížka využít šířku (víc dlaždic na řádek),
ne roztáhnout formulář.

#### Scenario: Notebook
- **WHEN** okno má 1280 × 720 CSS px a otevřená je plocha akce
- **THEN** stránka nemá vodorovný posuvník, tlačítko Dokončit akci je
  vidět a formulář jde vyplnit

#### Scenario: Široký monitor
- **WHEN** okno má 2560 CSS px na šířku
- **THEN** formulář má stejnou šířku jako na 1920 px a mřížka ukazuje
  víc dlaždic na řádek
