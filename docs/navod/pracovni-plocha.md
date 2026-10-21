[← Dokumentace](../README.md)

# Pracovní plocha

**Pracovní plocha** (po průvodci akcí a při každém dalším otevření): vlevo
navigátor akce, uprostřed mřížka náhledů po skupinách, vpravo
formulář podle výběru — nic vybráno = akce, skupina vybraná
v navigátoru = skupina, vybrané soubory = soubory. Zděděné
hodnoty jsou ve formuláři vidět a jdou přepsat. Každé pole má
barevný proužek a štítek zdroje hodnoty: „z akce“, „ze skupiny“,
„z místa“, „rozdílné“ (různé hodnoty ve výběru) nebo „zadáno“.
Zadaná hodnota skupiny nebo souborů má tlačítko „vrátit na
zděděné“; to hodnotu z dané úrovně smaže, stejně jako vyprázdnění
pole.

Našeptávání a kontrola jmen viz [Jména osob](../navrh/jmena-osob.md).

## Navigátor akce

   **Navigátor akce** (sloupec vlevo, posouvá se sám) má nahoře řádek
Akce a pod ním řádek pro každý oddíl mřížky (skupinu, nebo den)
v pořadí mřížky; soubory bez skupiny jsou posledním oddílem „Bez
skupiny“, soubory bez data „Bez data“. Řádek oddílu ukazuje název,
počet souborů, pruh autorů v poměru jejich souborů (nejvýš tři
barevně, ostatní šedě, bez autorů šrafovaně; titulek uvádí jména
a počty) a ikonky chybějících údajů s počtem: soubory bez autorů,
bez data, bez místa (jen má-li akce víc míst) a podle data i bez
skupiny; skupina bez autorů má místo počtu zvýrazněné „bez autorů“.
Řádek Akce ukazuje chybějící název či data akce a místa, o jejichž
souřadnicích není rozhodnuto, a ikonu osoby s počtem nepojmenovaných
osob podle posledního zjištění („2 nepojmenované osoby“); klik na
něj otevře archiváři a adminovi nástroj pojmenování osob, ostatním
údaj jen ukazuje. Soubory k vyřazení se nepočítají.
Klik na řádek Akce zruší výběr, na skupinu vybere skupinu, na den
(„Bez data“, „Bez skupiny“) jeho soubory, a mřížka na oddíl skočí
i s předělem nad ním. Klik na chybějící údaj vybere dotčené soubory
(u místa navíc otevře volbu souřadnic), funguje i jen ke čtení.
Oddíly, které jsou v mřížce vidět, mají v navigátoru okraj.
Dlaždici (nebo celý výběr, je-li dlaždice vybraná) jde **přetáhnout
na řádek skupiny** a přesunout tak do skupiny; ostatní řádky tažení
nepřijmou, bez zámku akce tažení nejde.

## Lišta akce

   Lišta akce pod hlavičkou nese název akce, přepínače mřížka/lupa
(ikony) a zobrazení, velikost náhledů, Importovat a Dokončit akci,
nálezy kontroly akce a počet souborů k vyřazení. Nevejdou-li se,
zalomí se na další řádek lišty. Posuvník **Náhledy** mění velikost
dlaždic mřížky (80–300 px, pamatuje si ho prohlížeč). Panel formuláře jde
**sbalit** úchytem na jeho levém okraji nebo klávesou `P` (mimo
textové pole); mřížka nebo lupa pak zabere celou šířku, stav si
pamatuje prohlížeč. Na širokém monitoru má panel nejvýš 420 px
a šířku využije mřížka.

## Po skupinách / Podle data

   Přepínač **Po skupinách / Podle data** (pamatuje si ho prohlížeč,
platí pro mřížku i lupu) ukáže místo skupin všechny soubory akce
v jednom pořadí podle data pořízení, s předěly po dnech
(„út 28. 4. 2026“ v navigátoru) a soubory bez data na konci.
Mřížka plochy nemá hlavičky oddílů, jen předěly. Dlaždice nemá
popisek: dole nese pruh podle výsledných autorů (každá osoba akce
má svou barvu, pruh se dělí na úseky v barvách autorů, nejvýš tři,
další jako šedý úsek; bez autorů šrafovaný, k vyřazení žádný),
v rohu ikonu bez data, bez místa, nebo k vyřazení, a název, datum
a příjmení autorů (u víc než tří „+N“) ukáže překryv při najetí myší
nebo fokusu z klávesnice. Průvodce je vždy po skupinách, s hlavičkami
a popisky a bez značek.

## Datum pořízení

   Datum pořízení má dva vstupy s nativním výběrem prohlížeče: den
a čas (se sekundami). Prázdný čas = hodnota jen s datem (WhatsApp);
smazání času ponechá den, smazání dne smaže celé datum, čas bez dne
zadat nejde. U výběru změna dne přepíše každému souboru den a jeho
čas zůstane, změna času přepíše čas a den zůstane; rozdílnou část
vstup neukazuje a vedle stojí „rozdílné hodnoty“.

## Klávesnice

   Mřížku ovládá klávesnice: ←/→ přejdou na předchozí a další soubor
v pořadí, ↑/↓ na vodorovně nejbližší dlaždici v řádku nad/pod
(i přes předěl oddílů), Home/End na první a poslední soubor
a PageUp/PageDown o výšku mřížky. Bez Shiftu vyberou jen cílový
soubor, se Shiftem rozsah od kotvy; Ctrl+A (na Macu Cmd+A) vybere
vše. Klávesy nepůsobí, když je kurzor v poli formuláře. Šipky už
mřížku nativně neposouvají; posun obstarává pohyb aktuálního
souboru, kolečko a posuvník zůstávají.

Aktuální soubor je v mřížce vyznačený vnitřním rámečkem odlišně od
výběru, i když je fokus ve formuláři. Pohyb klávesou dlaždici dá
fokus a posune k ní mřížku; Tab na dlaždici ji udělá aktuální bez
změny výběru a Enter pak na ní otevře lupu. Pohyb vychází
z aktuálního souboru, i když je mimo obrazovku; bez aktuálního
souboru vede první šipka na první soubor akce.

## Lupa

   Místo mřížky jde přepnout na **lupu** (Enter, dvojklik na dlaždici
nebo přepínač; zpět Esc): velká fotka nebo přehrávač videa a pod ní
filmový pás celé akce s oddíly (skupinami, nebo dny) oddělenými
předělem. Lupa ukáže aktuální soubor — naposledy kliknutý, vybraný
nebo klávesnicí fokusovaný; klik do pásu vybírá jako v mřížce.
Klávesy ←/→, Shift, Home/End, PageUp/PageDown a Ctrl+A platí
i tady; navíc ↑ skočí na první soubor oddílu (na jeho začátku
na předchozí oddíl), ↓ na první soubor dalšího oddílu
a PageUp/PageDown se posouvají o tolik souborů, kolik se vejde
do pásu. Výběr i formulář jsou s mřížkou společné. Navigátor
v lupě slouží ke skoku: klik na oddíl udělá jeho první soubor
aktuálním a jediným vybraným; okraj má oddíl aktuálního souboru.

   **Rámečky obličejů:** při kurzoru nad velkou fotkou ukáže lupa
rámečky kolem pojmenovaných obličejů z Immiche (`obliceje`
v `_metadata.json`); jinak je fotka čistá. Najetí na rámeček ukáže
u něj jméno a zvýrazní ho v poli „Osoby na fotce“; najetí na jméno
v poli naopak ukáže jen rámečky té osoby. Při výběru víc souborů
jsou v poli ztlumená jména, která na aktuální fotce nejsou. Rámečky
se obnoví až po synchronizaci a znovunačtení akce.
