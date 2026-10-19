## Purpose

Umožnit práci s aplikací na telefonu s Androidem: doplňování metadat
na pracovní ploše a průvodce importem dotykem, bez myši a klávesnice.

## ADDED Requirements

### Requirement: Rozvržení na úzké obrazovce
Na obrazovce užší než 700 CSS px SHALL každá obrazovka aplikace
(seznam akcí, Přetřídit, průvodce importem, průvodce akce, pracovní
plocha, nastavení, přihlášení) zobrazit obsah bez vodorovného posouvání
stránky. Seznam akcí SHALL zobrazit akce jako karty (název, datum,
stav, počet souborů, odznaky). Hlavička SHALL vynechat cesty k archivu
a pracovnímu adresáři. Ovládací prvky SHALL mít dotykovou plochu
aspoň 40 × 40 CSS px.

#### Scenario: Seznam akcí na telefonu
- **WHEN** uživatel otevře seznam akcí na displeji širokém 412 px
- **THEN** akce jsou karty pod sebou a stránka nejde posunout do strany

#### Scenario: Plocha na telefonu
- **WHEN** uživatel otevře akci na displeji širokém 412 px
- **THEN** mřížka zabírá celou šířku a formulář vedle ní není

### Requirement: Desktop beze změny
Na obrazovce široké aspoň 700 CSS px a při ovládání myší MUST aplikace
vypadat a chovat se jako dosud (rozvržení, klik, Ctrl/Shift+klik,
výběr tažením, klávesy).

#### Scenario: Klik myší na širokém okně
- **WHEN** uživatel na ploše v okně širokém 1400 px klikne myší
  na dlaždici
- **THEN** soubor se vybere a formulář vedle mřížky ukáže jeho údaje,
  lupa se neotevře

### Requirement: Kroky importu na úzké obrazovce
Na úzké obrazovce SHALL přehled, cíl, plán i výsledek importu ukázat
nejdřív souhrn (počty, data, přístroje, cíl, co se přenese, přeskočí
a zablokuje) a seznamy souborů SHALL být sbalené. Poškozené soubory
SHALL přehled ukázat jako karty se jménem, stavem, důvodem, volbou
„přesto importovat“ (u podezřelých) a tlačítkem Smazat. Navigace
průvodce (zpět, zahodit, pokračovat) SHALL být připnutá ve spodní
části obrazovky a viditelná bez posouvání.

#### Scenario: Pokračovat bez posouvání
- **WHEN** přehled importu ze složky v `přetřídit` se 300 soubory je
  na telefonu otevřený a kontrola doběhla
- **THEN** tlačítko Pokračovat je vidět dole bez posouvání stránky

### Requirement: Dotykový výběr souborů
Při ovládání dotykem (na ploše i v kroku skupin průvodce akce) SHALL
ťuknutí na dlaždici otevřít lupu s tímto souborem jako aktuálním
a jediným vybraným; v kroku skupin průvodce, který lupu nemá, SHALL
ťuknutí vybrat jen tento soubor. Dlouhý stisk dlaždice (aspoň 0,5 s
bez pohybu) SHALL zapnout režim výběru s tímto souborem vybraným.
V režimu výběru SHALL ťuknutí soubor do výběru přidat, nebo z něj
odebrat, a ťuknutí na hlavičku oddílu SHALL vybrat soubory oddílu
(u skupiny skupinu jako dosud). Režim výběru SHALL ukazovat počet
vybraných a tlačítko Zrušit výběr; zrušení nebo vyprázdnění výběru
režim ukončí. Posouvání mřížky prstem MUST NOT měnit výběr.

#### Scenario: Ťuknutí otevře lupu
- **WHEN** uživatel mimo režim výběru ťukne na `P1503720.JPG`
- **THEN** otevře se lupa s touto fotkou a vybraná je jen ona

#### Scenario: Výběr několika souborů
- **WHEN** uživatel dlouze stiskne `P1503720.JPG` a pak ťukne
  na `P1503721.JPG` a `P1503725.JPG`
- **THEN** jsou vybrané tři soubory, lišta ukazuje „3 vybrané“
  a lupa se neotevřela

#### Scenario: Posouvání nevybírá
- **WHEN** uživatel položí prst na dlaždici a táhne mřížkou nahoru
- **THEN** mřížka se posune a výběr se nezmění

### Requirement: Formulář jako spodní list
Na úzké obrazovce SHALL být formulář (akce, skupina, soubory) skrytý
ve spodním listu. Plocha SHALL ukazovat tlačítko „Upravit“ s tím, co se
upravuje („Upravit akci“, „Upravit skupinu“, „Upravit (N)“); ťuknutí
list otevře přes část obrazovky a list SHALL jít zavřít. Změny ve
formuláři SHALL se ukládat stejně jako na desktopu. Lišta chybějících
údajů SHALL po ťuknutí na položku vybrat totéž co na desktopu a otevřít
list.

#### Scenario: Autoři tří souborů
- **WHEN** uživatel má vybrané tři soubory a ťukne na „Upravit (3)“
- **THEN** otevře se list s formulářem tří souborů a zadané autory
  aplikace uloží

### Requirement: Dotyková lupa
Při ovládání dotykem SHALL přejetí prstem doleva/doprava po velké fotce
přejít na další/předchozí soubor jako šipka (mimo režim výběru vybere
jen jej, v režimu výběru ho přidá k výběru jako Shift+šipka). Ťuknutí
na dlaždici pásu SHALL vybírat stejně jako ťuknutí v mřížce, ale
lupu MUST NOT opouštět. Lupa SHALL mít viditelné tlačítko zpět do
mřížky. Přejetí po přehrávaném videu MUST NOT bránit ovládání
přehrávače.

#### Scenario: Prohlížení přejetím
- **WHEN** v lupě je aktuální `P1503720.JPG` a uživatel přejede prstem
  doleva
- **THEN** aktuální a jediný vybraný je další soubor v pořadí pásu

### Requirement: Ovládání bez klávesnice
Každá akce plochy dostupná klávesou SHALL jít na dotykovém zařízení
provést ťuknutím: Vyřadit (Del) v liště režimu výběru i v listu
formuláře, Zrušit výběr (Esc v mřížce), zpět do mřížky (Esc v lupě).
Na úzké obrazovce SHALL lišta akce ukázat zpět, název akce, přepínač
mřížka/lupa a Dokončit akci; ostatní (Po skupinách / Podle data,
Importovat…, stav exportu) SHALL být v menu „⋯“.

#### Scenario: Vyřazení dotykem
- **WHEN** uživatel v režimu výběru vybere dva soubory a ťukne
  na Vyřadit
- **THEN** oba soubory se označí k vyřazení jako po stisku Del
