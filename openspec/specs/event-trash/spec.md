# event-trash Specification

## Purpose

Umožnit adminovi odstranit akci z archivu bezpečně: smazaná akce
nejdřív 7 dní leží v koši, odkud ji jde obnovit, a teprve potom se
aplikace postará o trvalé smazání složky i alba v Immichi.

## Requirements

### Requirement: Smazání akce do koše
Admin SHALL moci na ploše akce akci smazat. Smazání SHALL přesunout
celou složku akce (s příponou `.ignored` i bez ní, včetně
`_metadata.json` a podsložek) do složky koše `_kos.ignored` v kořeni
archivu pod nový unikátní název (ID) a MUST NOT nic mazat. Akce SHALL
tím zmizet ze seznamu akcí a otevírat se jako neexistující.

#### Scenario: Smazání akce
- **WHEN** admin v produkčním režimu smaže akci
  `2026-04-28 kontrola Stezky`
- **THEN** složka `2026-04-28 kontrola Stezky` v kořeni archivu
  neexistuje, její obsah je beze změny v `_kos.ignored/<ID>/` a seznam
  akcí akci neuvádí

#### Scenario: Smazání skryté akce
- **WHEN** admin smaže nedokončenou akci se složkou
  `2026-04-28 kontrola Stezky.ignored`
- **THEN** složka se přesune do koše stejně jako bez přípony

#### Scenario: Stejný název smazán dvakrát
- **WHEN** admin smaže akci `2026-04-28 kontrola Stezky`, pak vznikne
  nová akce stejného názvu a admin smaže i ji
- **THEN** koš obsahuje obě akce pod různými ID a žádný soubor se
  nepřepsal

### Requirement: Potvrzení smazání
Smazání SHALL vyžadovat potvrzení dialogem, ve kterém admin opíše název
akce a uvede neprázdný důvod. Server MUST smazání odmítnout, pokud
opsaný název neodpovídá akci nebo chybí důvod. Smazání SHALL být
zapsáno do logu serveru (akce, ID v koši, kdo, důvod).

#### Scenario: Špatně opsaný název
- **WHEN** admin v dialogu opíše název jinak, než se akce jmenuje
- **THEN** server smazání odmítne a složka akce zůstane na místě

#### Scenario: Bez důvodu
- **WHEN** admin opíše název správně, ale důvod nechá prázdný
- **THEN** smazání se neprovede

### Requirement: Záznam o smazání
Smazání SHALL do složky akce v koši zapsat záznam `_smazano.json`
s názvem akce, původním názvem složky (včetně případné přípony
`.ignored`), jménem admina z relace, časem smazání, důvodem a stavem
akce z pracovního adresáře (vazba na album, stav v Immichi, počty osob,
záznam exportu, odložené osoby). Ten se z pracovního adresáře SHALL
odebrat. Záznam MUST vzniknout před přesunem; nepovede-li se přesun,
akce i pracovní adresář MUST zůstat beze změny. Jméno MUST pocházet
z relace, ne z požadavku.

#### Scenario: Obsah záznamu
- **WHEN** admin `Novák, Jan` smaže akci se složkou
  `2026-04-28 kontrola Stezky.ignored` s důvodem `duplicita`
- **THEN** `_smazano.json` v koši uvádí název
  `2026-04-28 kontrola Stezky`, složku
  `2026-04-28 kontrola Stezky.ignored`, `Novák, Jan`, čas a `duplicita`

#### Scenario: Stav akce přejde do záznamu
- **WHEN** admin smaže dokončenou akci s albem v Immichi a pak import
  vytvoří novou akci stejného názvu
- **THEN** nová akce nemá vazbu na album ani stav v Immichi a záznam
  v koši vazbu na původní album drží

#### Scenario: Jméno v požadavku
- **WHEN** požadavek na smazání obsahuje jiné jméno, než má relace
- **THEN** záznam uvádí jméno z relace

### Requirement: Podmínky smazání
Smazání MUST server povolit jen adminovi; ostatním SHALL vrátit 403
a klient jim tlačítko SHALL nezobrazit. Smazat MUST NOT jít akci, kterou
drží zámkem jiná relace, ani akci v kolizi přípony (viz
`event-visibility`). Po dobu přesunu SHALL smazání držet zámek akce.

#### Scenario: Archivář
- **WHEN** archivář bez role admin pošle požadavek na smazání akce
- **THEN** server vrátí 403 a akce zůstane beze změny

#### Scenario: Akce otevřená jiným uživatelem
- **WHEN** admin maže akci, kterou má otevřenou se zámkem jiný uživatel
- **THEN** smazání se odmítne s uvedením držitele zámku

#### Scenario: Kolize přípony
- **WHEN** archiv obsahuje složku akce s příponou `.ignored` i bez ní
- **THEN** smazání se odmítne a obě složky zůstanou beze změny

### Requirement: Smazání ve vývojovém režimu
Ve vývojovém režimu SHALL dialog smazání jen ukázat, co by se stalo
(cílová složka v koši a datum trvalého smazání), a archiv MUST zůstat
beze změny.

#### Scenario: Vývojový režim
- **WHEN** admin ve vývojovém režimu potvrdí smazání akce
- **THEN** aplikace ukáže plán a složka akce zůstane v archivu

### Requirement: Akce v koši
Složka `_kos.ignored` a její obsah MUST NOT se objevit v seznamu akcí,
v indexu, v návrzích jmen, v kontrolách ani v synchronizaci obličejů
a Immich ji MUST vyloučit vzorem `**/*.ignored/**`. Název nové akce
MUST NOT být blokován akcí v koši.

#### Scenario: Návrhy jmen
- **WHEN** jméno `Vzorný, Tomáš` je jen v `_metadata.json` akce v koši
- **THEN** seznam návrhů jmen ho neobsahuje

#### Scenario: Nová akce stejného názvu
- **WHEN** akce `2026-04-28 kontrola Stezky` je v koši a import vytvoří
  akci stejného názvu
- **THEN** import proběhne jako u nové akce

### Requirement: Stránka Koš
Aplikace SHALL adminovi nabídnout stránku Koš se smazanými akcemi
seřazenými podle času smazání sestupně. U každé SHALL uvádět název
akce, kdo a kdy ji smazal, důvod, počet souborů a datum trvalého
smazání. Ostatním uživatelům MUST server stránku i její data odepřít.
Složka v koši bez platného záznamu SHALL být uvedena jako neznámá.

#### Scenario: Výpis koše
- **WHEN** admin `Novák, Jan` před 2 dny smazal akci
  `2026-04-28 kontrola Stezky`
- **THEN** stránka Koš ji uvádí s jeho jménem, důvodem a trvalým
  smazáním za 5 dní

#### Scenario: Složka bez záznamu
- **WHEN** v `_kos.ignored` je složka bez `_smazano.json`
- **THEN** stránka ji uvede jako neznámou bez možnosti obnovení

### Requirement: Obnovení akce
Admin SHALL moci akci z koše obnovit: složka se přesune zpět do kořene
archivu pod původní název složky ze záznamu (s příponou `.ignored`
nebo bez ní), stav akce ze záznamu se vrátí do pracovního adresáře
a záznam `_smazano.json` se odstraní. Existuje-li v kořeni
akce stejného názvu (s příponou i bez ní), MUST obnovení odmítnout
a nic nepřesunout. Obnovení SHALL být zapsáno do logu serveru.

#### Scenario: Obnovení
- **WHEN** admin obnoví akci `2026-04-28 kontrola Stezky` smazanou
  ze složky `2026-04-28 kontrola Stezky.ignored`
- **THEN** archiv obsahuje `2026-04-28 kontrola Stezky.ignored`
  s původním obsahem a `_metadata.json` a seznam akcí ji uvádí

#### Scenario: Obnovení dokončené akce
- **WHEN** admin obnoví dokončenou akci s albem v Immichi
- **THEN** akce má znovu vazbu na album, stav v Immichi a záznam
  exportu jako před smazáním

#### Scenario: Název je obsazený
- **WHEN** admin obnovuje akci `2026-04-28 kontrola Stezky` a v archivu
  mezitím vznikla akce stejného názvu
- **THEN** obnovení se odmítne a obě složky zůstanou beze změny

### Requirement: Sken knihovny po přesunu dokončené akce
Smazání dokončené akce (složka bez přípony `.ignored`) do koše
i její obnovení SHALL v produkčním režimu spustit na pozadí sken
knihovny vybrané v nastavení Immiche, aby Immich assety akce hned
označil offline, resp. je vrátil. Na Immich MUST NOT čekat a chyba
Immiche MUST NOT smazání ani obnovení zabránit. Smazání SHALL ukončit
běžící hlídání akce po dokončení. Obnovení SHALL spustit hlídání jako
dokončení akce (sken, udržení alba, rozpoznávání). Nedokončená akce
sken MUST NOT spustit; bez nastaveného Immiche nebo vybrané knihovny
se sken vynechá.

#### Scenario: Smazání dokončené akce
- **WHEN** admin smaže dokončenou akci a Immich má vybranou knihovnu
- **THEN** smazání odpoví hned a na pozadí proběhne sken knihovny

#### Scenario: Smazání nedokončené akce
- **WHEN** admin smaže akci, jejíž složka má příponu `.ignored`
- **THEN** sken knihovny se nespustí

#### Scenario: Obnovení dokončené akce spustí sken
- **WHEN** admin obnoví dokončenou akci
- **THEN** na pozadí proběhne sken knihovny a album akce se udržuje
  jako po dokončení

#### Scenario: Immich nedostupný při smazání
- **WHEN** admin smaže dokončenou akci a Immich neodpovídá
- **THEN** akce je v koši a chyba skenu je jen v logu

### Requirement: Automatické vysypání koše
Server SHALL při startu a pak jednou denně trvale smazat každou akci
v koši, jejíž záznam o smazání je starší než 7 dní. Bez platného
záznamu MUST NOT složku smazat. Ve vývojovém režimu MUST NOT nic mazat.
Trvalé smazání SHALL být zapsáno do logu serveru. Okamžité trvalé
smazání MUST NOT být nabízeno.

#### Scenario: Po 7 dnech
- **WHEN** akce je v koši 8 dní a server běží
- **THEN** její složka z koše zmizí a log uvádí její název a ID

#### Scenario: Před uplynutím lhůty
- **WHEN** akce je v koši 6 dní a proběhne vysypání
- **THEN** zůstane v koši

#### Scenario: Složka bez záznamu
- **WHEN** v `_kos.ignored` je 30 dní stará složka bez `_smazano.json`
- **THEN** vysypání ji nechá beze změny

### Requirement: Příkaz vysypat
Příkaz `python -m fotoarchiv vysypat` SHALL vypsat akce v koši s datem
trvalého smazání a s přepínačem `--zapis-do-archivu` SHALL trvale
smazat ty, kterým uplynula lhůta, stejně jako server. Bez přepínače
MUST archiv nechat beze změny.

#### Scenario: Výpis bez zápisu
- **WHEN** příkaz běží bez `--zapis-do-archivu` a v koši je akce
  starší 7 dní
- **THEN** příkaz ji vypíše a složka zůstane v koši

### Requirement: Úklid po vysypání
Trvalé smazání akce SHALL odstranit i její album v Immichi (viz
`immich-people`) podle vazby ze záznamu a náhledy jejích souborů
v cache. Selže-li smazání alba, SHALL složka přesto zmizet, chyba
SHALL být v logu a album SHALL zůstat v pracovním adresáři ke
smazání při dalším vysypání. Stav akce stejného názvu v archivu MUST
NOT vysypání měnit.

#### Scenario: Akce s albem
- **WHEN** vysypání trvale smaže dokončenou akci s albem v Immichi
- **THEN** album v Immichi neexistuje a pracovní adresář o akci nic
  nevede

#### Scenario: Immich nedostupný
- **WHEN** při vysypání nejde album smazat
- **THEN** složka z koše zmizí, log uvádí chybu a příští vysypání
  smazání alba zopakuje

#### Scenario: Nová akce stejného názvu
- **WHEN** vysypání trvale smaže akci `2026-04-28 kontrola Stezky`
  a v archivu mezitím vznikla nová akce stejného názvu
- **THEN** cache, stav alba a export nové akce zůstanou beze změny
