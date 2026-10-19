[← Dokumentace](../README.md)

# Dokončení akce

**Dokončení akce:** tlačítko Dokončit akci na ploše uloží změny
a otevře **kontrolní stránku** (`#/akce/<název>/dokonceni`, jde
otevřít i odkazem). Ta ukáže kontroly se stavem v pořádku /
k vyřešení: údaje akce, chybějící údaje souborů (skupiny a soubory
bez autorů, soubory bez data, bez skupiny, bez místa, místa bez
souřadnic), nálezy kontroly akce, poškozené soubory bez rozhodnutí,
soubory k vyřazení ještě v kořeni a stav exportu (kontrola
nanečisto; ve vývojovém režimu i kam jdou sidecary). Každá kontrola
k vyřešení má odkaz „Opravit na ploše“: otevře plochu a vybere
dotčené soubory nebo skupinu, otevře volbu souřadnic, výpis názvů
nebo Uklidit…; zpět vede tlačítko Dokončit akci. Při kontrolách
k vyřešení nese tlačítko stránky text „Přesto dokončit“ (to je
výslovné potvrzení), jinak „Dokončit“. Stránka sdílí s plochou
stav akce i zámek (přechod zámek neuvolní); bez zámku je jen ke
čtení s uvedeným držitelem a tlačítko je neaktivní. Nezpracovanou
akci přesměruje na průvodce. Dokončení zapíše sidecary, v produkčním
režimu odebere složce akce příponu `.ignored` (zveřejní ji pro
Immich, který ji tak poprvé uvidí rovnou se sidecary) a nastaví
`dokonceno`. Selže-li zápis některého sidecaru nebo přejmenování
složky (např. soubor v ní drží jiný počítač), akce dokončená
není a kontrolní stránka chybu ukáže. Po dokončení stránka ukáže
počty zapsaných, nezměněných a selhaných sidecarů, chyby po souborech
a odkaz zpět na seznam akcí. Dokončit akci je jediný zápis sidecarů
z plochy: po úpravě dokončené akce se dokončí znovu. `dokonceno` je
datum prvního dokončení, opakované dokončení ho nemění; selže-li
přitom export, akce zůstane dokončená a stránka chybu ukáže. U
tlačítka plocha ukazuje, kolik sidecarů je neaktuálních, a po úpravě
„neexportované změny“; seznam akcí u dokončené akce upravené po
exportu uvede „změněno po exportu“. U dokončené akce je Dokončit
akci neaktivní, dokud není co dokončovat (neuložené či neexportované
změny, neaktuální sidecary, selhaný export).
