[← Dokumentace](../README.md)

# Pojmenování osob

**Nástroj pojmenování osob** (smí admin a archivář, ostatním server
vrátí 403) prochází po jedné nepojmenované a neskryté osobě Immiche
s obličejem na fotce v albu akce, seřazené podle počtu obličejů.
Otevírá se jako překryv nad plochou akce (rozmazané pozadí) tlačítkem
v liště akce, klikem na nepojmenované osoby v navigátoru a z karty
odkazem (`#osoby` v adrese plochy); u stavu *rozpoznávání obličejů*
upozorní, že další osoby mohou přibýt. Zavření vrátí na plochu
a odstraní `#osoby` z adresy.
U každé ukáže až 3 výřezy z různých fotek (zmenšeniny proxyuje
server — klíč Immiche neopouští server) s metadaty z Immiche a po
zdědění i ze souboru archivu. Osobu lze pojmenovat (do Immiche se
zapisuje kanonický tvar `Příjmení, Jméno`, u stejnojmenné existující
osoby nabídne server sloučení), skrýt, nebo odložit; odložené osoby
jsou per uživatel a akce v `.work/pojmenovani.json`, nové kolo je
vymaže. Klávesy fungují i v poli jména: Enter uloží, nebo nabídnuté
sloučení potvrdí (ikonka Enteru je u tlačítka, které Enter stiskne),
PageDown odloží, Alt+Delete skryje, Esc zavře; další volba se
neodešle, dokud
předchozí zápis neskončil. Nástroj zapisuje jen do Immiche (`PUT
/api/people`, `POST /api/people/merge`), `_metadata.json` nemění
a nevyžaduje zámek akce. Po každé akci přepočítá počty osob
do `.work/immich-osoby.json`; zavření nástroje po změně spustí
synchronizaci, takže se jména brzy objeví v `obliceje`.
