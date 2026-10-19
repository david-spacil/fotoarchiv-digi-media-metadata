[← Dokumentace](../README.md)

# Vyřazení a úklid

   **Vyřazení:** klávesa Del nebo tlačítko „Vyřadit“ v panelu označí
vybrané soubory k vyřazení (jsou-li už všechny označené, označení
zruší). Označené dlaždice zůstávají na místě, zašedlé a přeškrtnuté.
Lišta ukazuje počet souborů k vyřazení a nálezy kontroly akce.
Tlačítko **Uklidit…** (je-li co vyřadit nebo napravit, včetně
poškozených souborů) uloží změny
a ukáže plán: označené do `k_odstraneni.ignored`, ostatní soubory do
`ostatni.ignored`, RAWy do `RAW.ignored` a u podsložek volbu
přesunout/ponechat jako v průvodci — podsložka bez volby zůstane.
Sekce **Poškozené soubory** je tabulka poškozených souborů kořene
(náhled, stav a důvod) se dvěma výlučnými sloupci: **Vyřadit**
(přesune se spolu s ostatními do `k_odstraneni.ignored`) a **V
pořádku** (`overeno`, kontrola se mýlí); hlavička sloupce označí
všechny. Výchozí je uložený stav, soubor bez volby zůstane, jak je.
Volby se zapíší až tlačítkem; bez přesunů jen „Uložit“. Soubor už
označený k vyřazení je šedý (zrušit jde na dlaždici); ve vývojovém
režimu je sloupec Vyřadit vypnutý.
V produkčním režimu plán po potvrzení provede
(viz [Podsložky a RAW](../navrh/podslozky-a-raw.md)),
ve vývojovém ho jen ukáže.
