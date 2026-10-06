## 1. Skládání hodnoty

- [x] 1.1 Přidat `fotoarchiv/static/datetime.js` s `withDay`,
      `withTime` a `parts`; ověřit testem
      `tests/js/datetime.test.mjs` pokrývajícím scénáře ze
      specifikace (`node --test tests/js`)

## 2. Editor

- [x] 2.1 V `app.js` nahradit editor typu `datetime` vstupy `date`
      a `time step="1"` se zápisem po cílech přes funkce z 1.1;
      odstranit `pickDay`, tlačítko 📅 a skrytý picker; ověřit
      v prohlížeči u jedné fotky s časem, WhatsApp fotky a fotky bez
      data (čas vypnutý)
- [x] 2.2 Rozdílné hodnoty: společná část ve vstupu, text „rozdílné
      hodnoty – zápisem přepíšete vše“ vedle vstupů; ověřit
      v prohlížeči výběrem fotek se stejným dnem a různými časy a
      zadáním nového času
- [x] 2.3 Odstranit CSS `.datetime .picker`, `.calendar` a upravit
      rozložení dvou vstupů; ověřit, že se pole vejde do formuláře
      bez zalomení

## 3. Dokumentace

- [x] 3.1 Upravit popis zadání data v `README.md` (Aplikace → Tok
      práce); ověřit `openspec validate date-time-pickers --strict`
