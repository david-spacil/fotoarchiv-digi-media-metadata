# event-lock Specification

## Purpose

Zabránit tomu, aby dva lidé současně upravovali stejnou akci na sdíleném
serveru, a přitom nenechat akci zamčenou po zavřeném prohlížeči.

## Requirements

### Requirement: Získání zámku
Při otevření akce SHALL klient požádat o zámek akce. Zámek SHALL nést
jméno uživatele, identifikátor relace prohlížeče a čas získání. Je-li
akce volná, server zámek přidělí. Jedna relace MUST držet nejvýš jeden
zámek; otevření jiné akce zámek předchozí akce uvolní.

#### Scenario: Volná akce
- **WHEN** uživatel otevře akci, kterou nikdo nedrží
- **THEN** dostane zámek a akci může upravovat

#### Scenario: Přechod na jinou akci
- **WHEN** držitel zámku akce A otevře akci B
- **THEN** zámek akce A se uvolní

### Requirement: Obsazená akce
Drží-li akci jiná relace, server zámek nepřidělí a vrátí jméno držitele
a čas posledního heartbeatu. Klient SHALL akci otevřít jen ke čtení
s upozorněním, kdo ji upravuje.

#### Scenario: Druhý uživatel
- **WHEN** Kopáčová otevře akci, kterou drží Spáčil
- **THEN** vidí akci jen ke čtení a upozornění „Akci upravuje Spáčil,
  David“

### Requirement: Heartbeat a uvolnění
Klient SHALL zámek obnovovat zhruba každou minutu, dokud je akce
otevřená. Při zavření akce nebo stránky SHALL zámek uvolnit. Zámek bez
heartbeatu déle než 5 minut je opuštěný: server ho MUST považovat za
volný a přidělit dalšímu žadateli.

#### Scenario: Zavřený prohlížeč
- **WHEN** držitel zavře prohlížeč bez uvolnění a uplyne 5 minut
- **THEN** další uživatel při otevření akce zámek dostane

#### Scenario: Ztracený zámek
- **WHEN** heartbeat relace dorazí poté, co zámek získal někdo jiný
- **THEN** server ho odmítne a klient přepne akci jen ke čtení
  s upozorněním

### Requirement: Zápis jen s zámkem
Uložení `_metadata.json` a provedení úklidu MUST server odmítnout, pokud
žádající relace nedrží zámek akce. Kontrola verze dokumentu při uložení
SHALL platit i pro držitele zámku.

#### Scenario: Uložení bez zámku
- **WHEN** relace bez zámku pošle uložení metadat
- **THEN** server uložení odmítne a archiv zůstane beze změny

### Requirement: Jméno uživatele
Do zavedení přihlašování SHALL klient před prvním otevřením akce
vyžádat jméno uživatele v kanonickém tvaru `Příjmení, Jméno` s návrhy
ze známých jmen a pamatovat si ho v prohlížeči.

#### Scenario: První návštěva
- **WHEN** uživatel bez uloženého jména otevře akci
- **THEN** aplikace se zeptá na jméno a teprve pak požádá o zámek
