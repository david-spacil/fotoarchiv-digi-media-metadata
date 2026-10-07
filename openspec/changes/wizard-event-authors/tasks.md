# Tasks

## 1. Příprava

- [ ] 1.1 Vytvořit venv (`uv venv .venv && uv pip install -p
      .venv/bin/python -r requirements.txt`) a spustit výchozí testy
      (`.venv/bin/python -m pytest -q`, `node --test
      tests/js/*.test.mjs`); ověřit, že počty testů v souhrnu jsou
      nenulové a vše prochází

## 2. Dědění autorů z akce v testech

- [ ] 2.1 Přidat fixture `tests/fixtures/inheritance/autori-jen-u-akce.json`
      (akce s `autori`, skupina bez autorů dědí, druhá skupina je
      přepisuje, soubor bez skupiny dědí z akce); ověřit, že ho projde
      Python i JS test fixtures
- [ ] 2.2 Test JS `missing()`: skupina se zděděnými autory akce není
      v `skupinyBezAutoru`; test Pythonu `incomplete()`: akce s autory
      jen u akce není nekompletní kvůli autorům; ověřit, že oba testy
      prochází (bez změny kódu dědění)

## 3. Pole autorů celé akce v průvodci

- [ ] 3.1 V `renderAuthorsStep` přidat nad skupiny `fieldset` „Celá
      akce“ s `fieldRow(targetsFor("akce", []), "autori", …)`
      a nápovědou, že se dědí na skupiny bez vlastních autorů; ověřit
      v prohlížeči, že pole ukazuje dříve zadané autory akce
- [ ] 3.2 Při změně autorů akce nahradit řádky autorů skupin novými
      (`replaceWith`) a zrušit rozpracované potvrzení „Přesto dokončit“
      i text varování; ověřit v prohlížeči, že skupina bez autorů ukáže
      „zděděno z akce“, fokus v poli akce zůstane a skupina s vlastními
      autory je ponechá
- [ ] 3.3 Ověřit v prohlížeči scénáře ze specifikace na vygenerované
      testovací akci mimo repo (scratch): autoři jen u akce → dokončení
      bez upozornění, `_metadata.json` má `akce.autori` a skupiny bez
      `autori`; skupina s vlastními autory si je ponechá
- [ ] 3.4 README (Aplikace, Tok práce, bod 2): v kroku autoři skupin
      jde zadat i autory celé akce, které skupiny bez vlastních dědí

## 4. Kontrola

- [ ] 4.1 Spustit celé testy Pythonu i JS a `openspec validate
      wizard-event-authors --strict`; ověřit, že vše prochází
