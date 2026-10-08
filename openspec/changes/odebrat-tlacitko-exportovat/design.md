## Context

Plocha má dvě tlačítka, obě volají tentýž export (`xmp.export`) a po
něm přegenerují index:

- **Exportovat** (`POST /api/akce/<akce>/export`): uloží změny,
  exportuje, `dokonceno` nemění, nekontroluje úplnost.
- **Dokončit akci** (`POST /api/akce/<akce>/dokoncit`): uloží změny,
  ukáže chybějící údaje a nálezy kontroly akce k potvrzení, nastaví
  `dokonceno` na dnešek, exportuje a v produkci odebere složce
  příponu `.ignored`. Selže-li export nebo přejmenování, nastaví
  `dokonceno` zpět na `null`.

U dokončené akce beze změn je Dokončit akci neaktivní; aktivní je, když
jsou neuložené či neexportované změny, neaktuální sidecary (kontrola
nanečisto při otevření) nebo selhal poslední export. Tím pokrývá
všechny případy, kdy dnes dává smysl Exportovat.

Dokončená akce příponu `.ignored` už nemá (`event-visibility`), takže
opakované dokončení ji nepřejmenovává; selhat může jen zápis
sidecarů. Dnešní kód při tom `dokonceno` vynuluje, ačkoli složka
zůstává zveřejněná — akce je pak vedená jako rozpracovaná a Immich ji
vidí.

## Goals / Non-Goals

**Goals:**

- Jedno tlačítko pro zápis sidecarů z plochy (Dokončit akci).
- Opakované dokončení je bezpečné: neztratí datum prvního dokončení
  a selhání exportu nezmění stav akce.

**Non-Goals:**

- Historie dat dokončení nebo verzování `_metadata.json` (#21).
- Změna příkazu `exportovat` v CLI.
- Datum posledního exportu na ploše.

## Decisions

### Odebrat i endpoint `/export`

Klient ho po odebrání tlačítka nevolá a jiný konzument není (CLI
exportuje přímo přes `xmp.export`). Ponechaný endpoint by byl
netestovaná cesta k zápisu do archivu mimo dokončení.
*Alternativa:* nechat endpoint pro skripty — zamítnuto, žádné
takové skripty nejsou a server je jen pro aplikaci.

### `dokonceno` = datum prvního dokončení

Opakované dokončení hodnotu zachová. Datum se používá jen jako stav
(*hotovo*) a údaj „Dokončeno …“ na ploše; do sidecarů ani indexu
nejde.
*Alternativy:* přepsat dnešním datem (dnešní chování; ztrácí datum,
kdy akce poprvé šla do Immiche); seznam všech dat dokončení (změna
datového modelu bez konzumenta, patří k #21).

### Vrácení `dokonceno` jen při prvním dokončení

Selže-li export nebo zveřejnění u akce, která `dokonceno` před
požadavkem neměla, chování zůstává (akce není dokončená). U akce, která
ho měla, zůstane hodnota beze změny a odpověď nese chyby jako dnes;
plocha je ukáže a tlačítko zůstane aktivní (`exportStale`).
Rozhodující je stav před požadavkem, ne přípona složky — pravidlo
platí stejně ve vývojovém režimu i pro dokončenou akci, které by
přípona omylem zůstala (pak selhání přejmenování také `dokonceno`
nevrátí a plocha ho ukáže).
*Alternativa:* rozhodovat podle přípony `.ignored` — zamítnuto, ve
vývojovém režimu se archiv nepřejmenovává a pravidlo by se lišilo
podle režimu.

### Stav exportu u tlačítka Dokončit akci

Text stavu (`#export-status`) zůstává, kde je; tooltip s cílem
sidecarů (archiv vs. `.work/xmp`) se přesune na Dokončit akci.

## Risks / Trade-offs

- [Export bez potvrzovacího dialogu zmizí] → u akce s chybějícími údaji
  nebo nálezy se opakované dokončení vždy ptá. Potvrzení je jedno
  kliknutí a upozorní na nevyřešené nálezy; přijatelné.
- [Rozpracovanou akci nejde exportovat bez dokončení] → export
  rozpracované akce je skrytý před Immichem a nikdo ho nečte; chyby
  zápisu ukáže neúspěšné první dokončení.
- [Skripty volající `/export`] → žádné nejsou známé; endpoint vrátí 404.
