[← Dokumentace](../README.md)

# Import

Průvodce importem se spouští ze seznamu akcí (bez cíle) nebo z plochy
akce (s ní jako předvybraným cílem). Kroky: soubory → přehled → cíl →
plán → skupiny a autoři → výsledek. Plán je před popisem, aby se
popisovalo jen to, co se opravdu přenese.

- **Soubory:** jednotlivé soubory i celá složka, výběrem nebo
  přetažením; soubory z podsložek se berou, jako by ležely v jedné
  úrovni. Nahrávají se po jednom (2–3 souběžně, s průběhem) do
  `.work/import/<id>/`, ne do archivu; zavření stránky archiv nezmění.
  Adresa `#/import/<id>` přežije reload. Limit 20 GB na soubor, server
  před nahráním kontroluje volné místo. Import patří jménu uživatele
  (porovnání jako u návrhů jmen; s přihlášením z relace, jméno
  v požadavku server ignoruje), ne záložce: seznam akcí ukazuje
  „Moje rozpracované importy“ (založeno, počet a velikost souborů,
  zamýšlený cíl, poslední aktivita) s tlačítky Pokračovat a Zahodit.
  Cizí import není vidět a jeho adresa hlásí „nenalezen“.

  Admin a archivář mohou místo nahrání zvolit **složku
  v `přetřídit`** („ze složky přetřídit“, nebo ze stránky *Přetřídit*,
  viz [Import ze složky přetřídit](import-z-pretridit.md)). Nic se
  nenahrává, průvodce rovnou ukáže přehled. Jednotkou je celá složka
  první úrovně; její podsložky se berou jako u nahrané složky
  (zploštění, skupiny podle podsložek, RAWy do `RAW.ignored/`),
  podsložky `*.ignored` se i s obsahem přeskočí. Seznam souborů se
  sestavuje pokaždé z aktuálního obsahu složky. Opakované zvolení
  téže složky otevře rozpracovaný import uživatele.
- **Přehled:** počty fotek, videí a RAWů, rozsah dat z EXIF (WhatsApp
  z názvu), přístroje, nepodporované soubory. Přijímají se média
  aplikace (jpg, jpeg, png, mp4, mov) a RAWy; `Thumbs.db` se tiše
  přeskočí, ostatní se vypíšou a nepřenesou.

  Po zobrazení přehledu se soubory **zkontrolují** (viz [Poškozené
  soubory](../navrh/poskozene-soubory.md)): stream s průběhem po souborech
  a bajtech, výsledky z cache hned; Pokračovat jde až po doběhnutí.
  Přehled vypíše podezřelé a nečitelné soubory s důvodem. Nečitelný se
  nepřenese nikdy, podezřelý jen se zaškrtnutým „přesto importovat“
  (volba se uloží k importu). Oba jde po potvrzení dialogem (jméno
  a důvod) **smazat**: nahraný z pracovního adresáře, soubor zdroje
  v `přetřídit` jen v produkčním režimu, pod zámkem zdroje (jako
  provedení). Smazat jde jen soubor, který kontrola označila jako
  poškozený a který se od ní nezměnil; smazání se zapíše do logu
  serveru.

  Samostatně se chovají fotky s **odebranou polohou**: Android při
  předání fotky prohlížeči nebo mailem vynuluje GPS blok (ověřeno na
  Pixel 8a, Android 17, 2026-10-09, v Chrome i Firefoxu — `exiftool`
  pak vrátí `GPSVersionID 0 0 0 0` a prázdné souřadnice). Poloha je
  pro archiv zásadní, taková fotka se nepřinese žádnou cestou
  importu, volba „přesto importovat“ se pro ni nenabízí a povolení
  podezřelých ji neuvolní. Přehled ji vypíše v bloku „Odebraná
  poloha“ bez tlačítka Smazat, plán a výsledek ji uvedou mezi
  nepřenesenými s důvodem „telefon odebral polohu“ (originál zůstane
  v pracovním adresáři nebo ve zdroji `přetřídit`). Uživatel má
  předat originál jinou cestou — kabelem nebo FileSenderem
  z počítače. Videa se zatím neřeší (chování Androidu
  u MP4/MOV není změřené). Pokračovat zůstává dostupné, pokud zbývá
  aspoň jedno přenositelné médium.
- **Cíl:** stávající akce, nebo nová — datum se předvyplní nejstarším
  dnem z EXIF, název doplní uživatel; složka `YYYY-MM-DD název` bez
  `/` a `\`, nekončí na `.ignored` a nesmí existovat s příponou
  `.ignored` ani bez ní (bez ohledu na velikost písmen; jinak průvodce
  nabídne zvolit ji jako stávající). Nová akce vznikne skrytá před
  Immichem (`název.ignored`, viz [Archiv](../navrh/archiv.md)). U dokončené akce
  upozorní, že Immich nové soubory uvidí hned a skupiny a autoři
  z importu se do sidecarů dostanou až novým dokončením akce.

  U nové akce krok sbírá i **údaje akce**: název (předvyplněný názvem
  složky bez data a jdoucí s ním, dokud ho uživatel nezmění), datum
  od–do (nejstarší a nejnovější den médií z přehledu), popis, místa
  a účastníky. Pokračovat jde jen s názvem a datem od.
- **Plán:** média do kořene, RAWy do `RAW.ignored/`. Poškozené
  soubory (nečitelné a nepovolené podezřelé) se nepřenesou a plán je
  uvede zvlášť s důvodem; vyloučená média dostanou stav operace
  `vylouceny` („vyloučeno z importu“) — vyloučení nemění, co je
  duplicita nebo blokované; soubor změněný od kontroly se zkontroluje
  znovu. Jméno, které v cíli existuje nebo ho má víc souborů výběru,
  se blokuje.
  Duplicita (stejný sha256 jako soubor v kořeni cílové akce nebo jiný
  soubor výběru) se přeskočí; hashe akce se počítají jen u souborů
  shodné velikosti a cachují se v `.work/cache/sha256/`. Na SMB to
  může trvat minuty, proto server posílá průběh porovnání (stream
  NDJSON, po souboru a u velkých po 64 MB; hashe z cache jsou hned
  hotové) a tlačítko je do konce výpočtu zablokované. Zvolený cíl se
  uloží k importu a po návratu se předvyplní. Plán skupiny neukazuje;
  nabízí jen pokračování ke skupinám a autorům.
- **Skupiny a autoři:** mřížka náhledů přenášených fotek a videí
  (náhledy nahraných souborů i souborů zdroje v `přetřídit`, nic se
  nezapisuje) a panel jako v průvodci akce. Mřížka kroku se ovládá
  klávesnicí jako na ploše, Esc ruší výběr souborů i skupiny; Enter a
  P nic nedělají a **Del** (stejně jako tlačítko v panelu) přepíná
  **vyloučení z importu**: jsou-li všechna vybraná média vyloučená,
  vrátí je do importu, jinak všechna vybraná vyloučí; popisek tlačítka
  je podle výběru „Vyloučit z importu“ resp. „Vrátit do
  importu“. Vyloučené médium zůstane v mřížce ve své skupině,
  zašedlé s ikonou; nepočítá se do „Importovat (N)“ ani do upozornění na
  skupiny bez autorů — vyloučí-li se vše, Importovat je vypnuté. Panel
  uvádí „Vyloučeno: N médií, M RAWů“. Má-li vylučovaná fotka RAW
  stejného jména bez přípony ve stejné složce výběru (porovnání bez
  ohledu na velikost písmen), průvodce se v dialogu zeptá, zda vyloučit
  i RAWy („Vyloučit i RAWy“ / „Jen fotky“, Esc zruší celé
  vyloučení); vrácení fotky vrací i její RAW bez dotazu. Nahoře **výchozí
  rozdělení** (RAWy skupinu nedostanou): *podle podsložek* (jen má-li
  výběr podsložky; skupina = podsložka první úrovně pod nejdelší
  společnou složkou výběru, soubory přímo v ní dostanou skupinu
  pojmenovanou po ní), *jedna nová skupina* (název předvyplněný
  kořenem výběru, jinak `Import YYYY-MM-DD`), *automaticky* (přístroj
  a vzor názvu jako u nové akce), *bez skupiny*, nebo *zařadit do
  skupiny …* (jen akce, jejíž `_metadata.json` skupiny má).
  Předvolba: podsložky → podle podsložek; jinak nová akce a akce bez
  `_metadata.json` → automaticky, ostatní → jedna nová skupina.
  Výchozí rozdělení počítá server z posledního plánu bez nového
  porovnání; změna po ručních úpravách nebo autorech skupin se ptá.
  Pod tím úpravy skupin (přejmenovat, sloučit, nová skupina z výběru,
  přesun) a u každé skupiny náhledy a autoři. Na autory celé akce se
  krok neptá, ani při doimportu do stávající akce.
  Nové skupiny se s existujícími (v `_metadata.json` nebo návrhu)
  samy nesloučí ani při shodě: název nové dostane případně pořadové
  číslo a u každé jde zvolit „nová skupina“ nebo „připojit ke skupině
  …“, existující se shodným názvem (bez diakritiky a velikosti písmen)
  nebo přístrojem nahoře jako shoda; připojená ukazuje autory
  existující skupiny. Existující skupiny cíle jsou jen ke čtení.
  Importujícího aplikace jako autora nepředvyplňuje.

  Údaje akce, volba rozdělení, skupiny, přiřazení, připojení a autoři
  (**popis importu**) se průběžně ukládají do `import.json` (ne do
  archivu) a po návratu se předvyplní. Seznam vyloučených (cesty ve
  výběru) se ukládá k importu do `.work/import/<id>/import.json` (klíč
  `vyloucene`), ne do archivu, i ve vývojovém režimu; přežije Pokračovat
  i změnu výchozího rozdělení. Po novém plánu média, která se
  už nepřenesou, ze skupin vypadnou, nově přenášená dostanou skupinu
  z výchozího rozdělení a ruční úpravy ostatních zůstanou. Má-li
  některá skupina po zdědění prázdné autory, tlačítko importu na to
  upozorní a import provede až druhé kliknutí; jinak druhé kliknutí
  jen potvrzuje zápis do archivu. „Co by se zapsalo“ ukáže souhrn
  popisu (ve vývojovém režimu místo provedení); vyloučená média v něm
  chybí.
- **Provedení** (jen produkční režim, ve vývojovém se plán a krok
  skupin jen ukážou):
  plán se sestaví znovu, soubor se zkopíruje do dočasného
  `.import-*.tmp` v cílové složce, dostane čas změny originálu
  a přejmenuje se, jen pokud cíl pořád neexistuje. Selhání jednoho
  souboru ostatní nezastaví. Import do stávající akce vyžaduje zámek
  akce; nová akce vznikne jen, pokud složka mezitím nevznikla, a zámek
  na ni dostane relace importu. Průběh jde streamem (NDJSON) po
  souborech a u velkých po 64 MB; ukazatel se posouvá podle bajtů.
  Přenesený soubor zmizí z pracovního adresáře hned. Vyloučený soubor se
  nepřenese a v pracovním adresáři importu zůstane, import proto zůstává
  mezi rozpracovanými. Zavření stránky
  kopírování zastaví nejpozději po dalších 64 MB: rozkopírovaný
  dočasný soubor se smaže, přenesené zůstanou v archivu, zbytek
  v pracovním adresáři. Když dočasný soubor smazat nejde (výpadek
  SMB), smaže ho další import do téže akce: před kopírováním odstraní
  `.import-*.tmp` starší než hodinu v kořeni a v `RAW.ignored/`
  a uvede je ve výsledku. Po přenosu (kopii i přesunu) server porovná
  velikost souboru v cíli s originálem; nesoulad je chyba souboru ve
  výsledku a soubor zůstane v archivu. Obsah se zpětně nečte: kopie
  porovnává sha256 přenášených dat a SMB/TCP přenos hlídá sám; vada
  z issue #10 (vynulované bloky) vzniká na kartě, ne přenosem.

  Po přenosu server zapíše popis z `import.json` jen pro skutečně
  přenesená média; blokované, duplicitní, selhané a vyloučené záznam
  nedostanou (vyloučený ani do návrhu skupin) a skupina bez přeneseného
  souboru nevznikne. **Nová akce:**
  `_metadata.json` vznikne rovnou s údaji akce z kroku cíl,
  skupinami a přenesenými soubory s technickými
  údaji; akce je *rozpracovaná* a otevře se rovnou plocha. **Akce
  s `_metadata.json`:** přenesené soubory (s technickými údaji, jako
  při otevření akce), nové skupiny s autory, připojení a přiřazení
  jdou do `_metadata.json` pod zámkem importu; údaje akce, stávající
  záznamy a skupiny se nemění. **Akce bez něj:** `_metadata.json`
  nevznikne, skupiny s autory a přiřazení jdou do návrhu
  `.work/navrhy-skupin/<akce>.json` (i v produkčním režimu; další
  import ho doplní) a použije ho průvodce akce. Když zápis selže
  (např. `_metadata.json` mezitím upravený mimo aplikaci), soubory
  zůstanou v archivu a výsledek uvede, že jsou bez skupiny a autorů.
- **Výsledek:** přenesené, blokované, duplicitní, poškozené, selhané
  a vyloučené soubory — vyloučené uvede mezi nepřenesenými jako
  „vyloučeno“; přenesené zmizí z pracovního adresáře, ostatní tam
  zůstanou, dokud uživatel import nezahodí. Importy neaktivní přes 7 dní server smaže
  při startu. Průvodce nabídne otevřít akci; nové soubory jsou mezi
  „novými od posledního otevření“, metadata se doplňují běžně.
