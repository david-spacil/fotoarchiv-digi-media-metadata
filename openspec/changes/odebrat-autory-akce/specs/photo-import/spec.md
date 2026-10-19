## MODIFIED Requirements

### Requirement: Skupiny a autoři v importu
Krok skupiny a autoři SHALL ukázat náhledy přenášených médií (fotky
a videa, ne RAWy) rozdělené do skupin podle výchozího rozdělení (viz
Volba skupin). Uživatel SHALL moci skupinu přejmenovat, sloučit
s jinou, vytvořit novou z vybraných médií a přesunout do ní vybraná
média, a každé skupině zadat autory. Autory celé akce krok MUST NOT
nabízet, ani u nové, ani u stávající akce. Jména autorů SHALL mít
kanonický tvar a návrhy jako jinde v aplikaci.

Má-li některá skupina přenášených médií prázdné autory, SHALL import
na to před provedením upozornit a provést se až po druhém potvrzení
(jako dokončení průvodce akce).

Údaje akce, skupiny, přiřazení a autory SHALL průvodce průběžně ukládat
k importu (ne do archivu) a po návratu k rozpracovanému importu je
předvyplnit. Změní-li se plán, média, která se už nepřenesou, MUST
ze skupin vypadnout a nově přenášená média SHALL dostat skupinu podle
výchozího rozdělení; ruční úpravy ostatních médií MUST zůstat.

#### Scenario: Ruční úprava automatické skupiny
- **WHEN** automatické rozdělení dá do jedné skupiny fotky dvou
  fotografů se stejným modelem telefonu a uživatel vybere fotky
  jednoho z nich a vytvoří z nich novou skupinu
- **THEN** krok ukáže dvě skupiny a každé jde zadat jiné autory

#### Scenario: Autoři celé akce
- **WHEN** uživatel importuje další fotky do akce, jejíž skupiny mají
  autory, a nové skupině zadá autorku `Modelová, Zuzana`
- **THEN** krok se na autory celé akce neptá, import se provede bez
  upozornění a autoři existujících skupin se nezmění

#### Scenario: Skupina bez autorů
- **WHEN** jedna nová skupina nemá autory a uživatel klikne na import
- **THEN** průvodce upozorní na skupinu bez autorů a import provede až
  po druhém kliknutí

#### Scenario: Návrat k rozpracovanému importu
- **WHEN** uživatel zadá autory dvou skupin, zavře stránku a import
  později otevře přes Pokračovat
- **THEN** krok skupiny a autoři ukáže tytéž skupiny s týmiž autory

### Requirement: Zápis skupin při provedení
Po provedení importu SHALL server zapsat skupiny, přiřazení a autory
skupin z kroku skupiny a autoři pro skutečně přenesená média;
blokované, duplicitní a selhané soubory MUST NOT dostat záznam.
Skupina, které po provedení nezůstal žádný přenesený soubor, MUST NOT
vzniknout. Autory celé akce MUST NOT zapsat (ani ze staršího
rozpracovaného importu).

- **Nová akce:** server SHALL založit `_metadata.json` s údaji akce
  z kroku cíl, skupinami a přenesenými soubory včetně technických
  údajů, jako by je přidalo otevření akce. Akce je pak *rozpracovaná*.
- **Akce s `_metadata.json`:** server SHALL zapsat nové skupiny s autory
  a přiřazení přenesených souborů. Stávající záznamy souborů a údaje
  akce a existujících skupin MUST zůstat beze změny.
- **Existující akce bez `_metadata.json`:** server MUST `_metadata.json`
  nevytvořit; SHALL uložit návrh skupin (skupiny s autory a přiřazení)
  do pracovního adresáře k akci (další import do téže akce návrh
  doplní).

Zápis do `_metadata.json` (nová akce i akce s ním) SHALL do `upravili`
doplnit jméno uživatele, který import provedl (viz `metadata-model`).

Nepodaří-li se popis zapsat, přenesené soubory MUST zůstat v archivu
a výsledek SHALL uvést, že soubory jsou bez skupiny a autorů.

#### Scenario: Import do rozpracované akce
- **WHEN** uživatel v produkčním režimu importuje 30 fotek jako jednu
  novou skupinu `Workshop` s autorem `Modelová, Zuzana` do akce ve
  stavu *rozpracováno*
- **THEN** po otevření akce je na ploše skupina `Workshop` se 30
  fotkami a autorkou `Modelová, Zuzana` a navigátor je neuvádí jako soubory
  bez skupiny ani skupinu bez autorů

#### Scenario: Blokovaný soubor bez skupiny
- **WHEN** jeden soubor importu je blokovaný kolizí jména
- **THEN** `_metadata.json` o něm nemá záznam a existující soubor
  stejného jména si ponechá svou skupinu

#### Scenario: Import do nové akce
- **WHEN** uživatel v produkčním režimu importuje složku `DOD 2015`
  s podsložkami do nové akce a zadá údaje akce a autory skupin
- **THEN** akce má `_metadata.json` s těmito údaji, bez `akce.autori`
  a se jménem uživatele v `upravili`, je v seznamu jako *rozpracováno*
  a její otevření vede rovnou na pracovní plochu

#### Scenario: Druhý import do neotevřené akce
- **WHEN** uživatel importuje do akce bez `_metadata.json`, ke které už
  je návrh skupin, a nic nepřipojí
- **THEN** návrh obsahuje dřívější i nové skupiny vedle sebe, každou se
  svými autory

#### Scenario: Rozpracovaný import s autory akce
- **WHEN** rozpracovaný import z doby před změnou má uložené autory
  celé akce a uživatel ho provede do akce s `_metadata.json`
- **THEN** `akce` v `_metadata.json` se nezmění
