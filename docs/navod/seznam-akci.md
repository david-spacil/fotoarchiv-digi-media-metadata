[← Dokumentace](../README.md)

# Seznam akcí

**Seznam akcí** je fronta práce: karta akce nese datum, název
(odkaz na plochu), počet souborů, stav (nezpracováno / rozpracováno
/ hotovo) a štítky, pruh až 4 náhledů rovnoměrně z celé akce (bez
souborů k vyřazení; načítají se líně, až je karta vidět), hotovost
a kdo akci drží („upravuje …“, vlastní zámek „otevřeno u vás“)
a naposledy upravoval (`upravili`). **Hotovost** = u každého pole
autoři, datum, místo počet souborů kořene (bez označených
k vyřazení), které ho mají po zdědění vyplněné, z jejich počtu;
počítá ji server při výpisu z `_metadata.json` a výpisu složky.
Má-li akce zjištěné osoby a stav *obličeje rozpoznány*, hotovost
uvádí i osoby: pojmenované ze všech neskrytých (`osoby 4/6`); při
nepojmenovaných karta nabídne archiváři a adminovi odkaz na nástroj
pojmenování osob (otevře plochu akce rovnou s nástrojem).
Nezpracovaná akce místo hotovosti nabízí zahájení zpracování.
Dokončená akce, jejímž souborům chybí autoři, datum nebo místo,
nebo která má podle posledního zjištění nepojmenované osoby, má
štítek „nekompletní“, upravená po exportu „změněno po exportu“;
akce s nálezem kontroly
(viz [Kontrola akce](../navrh/podslozky-a-raw.md#kontrola-akce)) „k vyřešení“.
Karty jsou **dlaždice** (náhledy 2 × 2, souhrnný pruh hotovosti)
nebo **řádky** (pruh hotovosti pro každé pole); přepínač si pamatuje
prohlížeč. **Filtry** s počty: Vše, Moje rozpracované (rozpracovaná,
nebo dokončená se změnami po exportu, kterou uživatel ukládal nebo
drží jeho zámek), K dokončení (rozpracovaná bez chybějících údajů
a dokončená se změnami po exportu), Nezpracované. **Hledání**
v názvu ignoruje diakritiku, velikost písmen a koncové samohlásky
slov („stezky naucna“ najde „Naučné stezky Vzorov“). **Řazení**
podle data akce (výchozí, sestupně), hotovosti (nejméně hotové
nahoře, nezpracované na konci) nebo poslední úpravy (bez záznamu na
konci). Filtr, hledání a řazení jsou v adrese seznamu
(`#/?filtr=…&hledat=…&razeni=…`), takže přežijí návrat z plochy
a jdou poslat odkazem. Nové fotky a videa se do archivu dostanou
**importem** (viz [Import](import.md)) do nové nebo stávající akce.

**Ikona stažení** (mráček se šipkou) na kartě stáhne celou akci jako
ZIP `<název akce>.zip` a plochu neotevře: média z kořene akce kromě
označených k vyřazení, bez podsložek (`RAW.ignored` aj.), k nim
`_metadata.json` a XMP sidecary médií se záznamem. Obsah ZIPu
a oprávnění viz [Stažení originálů](pracovni-plocha.md#stažení-originálů).
