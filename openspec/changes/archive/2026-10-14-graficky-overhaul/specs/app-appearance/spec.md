## Purpose

Dát klientovi jednotný vizuální systém (barvy, typografie, komponenty)
s tmavým a světlým režimem, čitelný na noteboocích i velkých
monitorech.

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
Text a ovládací prvky SHALL mít v obou režimech (tmavý, světlý)
kontrast vůči pozadí aspoň 4,5 : 1 (běžný
text) a 3 : 1 (velký text, okraje polí, ikony). Barvy osob v pruhu
autorů MUST zůstat navzájem rozlišitelné i na tmavém pozadí.

#### Scenario: Zděděná hodnota v tmavém režimu
- **WHEN** formulář v tmavém režimu ukazuje zděděný popis jako
  zástupný text
- **THEN** text má vůči poli kontrast aspoň 4,5 : 1

### Requirement: Tmavý a světlý režim
Klient SHALL mít výchozí tmavý režim (neutrálně tmavé lišty, mřížka
i formulář) a světlý režim. Přepínač v hlavičce aplikace SHALL režim
přepnout hned, bez ztráty rozepsaných údajů, a prohlížeč si volbu SHALL
pamatovat pro všechny stránky klienta i po obnovení. Lupa MUST zůstat
tmavá v obou režimech. Náhledy fotek MUST se nebarvit ani neinvertovat.
Režim MUST NOT měnit rozvržení, chování ani klávesové zkratky.

#### Scenario: Výchozí režim
- **WHEN** uživatel otevře aplikaci poprvé
- **THEN** seznam akcí je v tmavém režimu

#### Scenario: Přepnutí
- **WHEN** uživatel na ploše akce klikne v hlavičce na přepínač
- **THEN** plocha je ve světlém režimu, lupa zůstane tmavá a náhledy
  fotek jsou beze změny

#### Scenario: Volba přetrvá
- **WHEN** uživatel přepnul do světlého režimu, zavře prohlížeč a znovu
  otevře přihlášení
- **THEN** stránka přihlášení je ve světlém režimu

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
