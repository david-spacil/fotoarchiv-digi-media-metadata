## ADDED Requirements

### Requirement: Velikost v koši
Každá položka koše SHALL mít velikost počítanou stejně jako velikost
akce (viz `archive-browsing`), uloženou v pracovním adresáři, ne
v záznamu `_smazano.json`. Smazání akce do koše SHALL přenést její
údaj k položce koše bez nového průchodu složkou; obnovení SHALL údaj
vrátit akci a akci přepočítat; vysypání SHALL položku odebrat.
Položka bez údaje SHALL být dopočítána na pozadí a denní přepočet
SHALL zahrnout i koš. Velikost koše je součet jeho položek.

#### Scenario: Smazání přenese velikost
- **WHEN** admin smaže akci s údajem 3 GB do prázdného koše
- **THEN** součet akcí klesne o 3 GB a koš uvádí 3 GB, aniž by se
  složka v koši znovu procházela

#### Scenario: Obnovení vrátí velikost
- **WHEN** admin obnoví akci s 3 GB z koše
- **THEN** koš ji už nepočítá a akce má údaj 3 GB i po přepočtu

#### Scenario: Vysypání
- **WHEN** vysypání trvale smaže položku koše s 3 GB
- **THEN** součet koše klesne o 3 GB

#### Scenario: Složka v koši bez údaje
- **WHEN** v koši je složka, o které pracovní adresář nemá údaj
- **THEN** její velikost se dopočítá na pozadí a pak se započte do
  součtu koše

## MODIFIED Requirements

### Requirement: Stránka Koš
Aplikace SHALL adminovi nabídnout stránku Koš se smazanými akcemi
seřazenými podle času smazání sestupně. U každé SHALL uvádět název
akce, kdo a kdy ji smazal, důvod, počet souborů, velikost (viz Velikost
v koši; bez údaje nic) a datum trvalého smazání. Ostatním uživatelům
MUST server stránku i její data odepřít. Složka v koši bez platného
záznamu SHALL být uvedena jako neznámá.

#### Scenario: Výpis koše
- **WHEN** admin `Novák, Jan` před 2 dny smazal akci
  `2026-04-28 kontrola Naučné stezky` o velikosti 3 GB
- **THEN** stránka Koš ji uvádí s jeho jménem, důvodem, velikostí
  3 GB a trvalým smazáním za 5 dní

#### Scenario: Složka bez záznamu
- **WHEN** v `_kos.ignored` je složka bez `_smazano.json`
- **THEN** stránka ji uvede jako neznámou bez možnosti obnovení
