## 1. Prototyp vzhledu

- [ ] 1.1 Vytáhnout z výpisu `/api/akce` (kopie archivu, rozšířený
  výpis z 2.x nebo ruční JSON) reálná data ~30 akcí a postavit funkční
  prototyp seznamu (2–3 varianty karty, filtry, hledání, řazení) přes
  skill `artifacty`; hotovo, až uživatel vybere variantu

## 2. Server: data karty

- [ ] 2.1 Přidat `model.completeness(doc, present)` (vyplněno/celkem
  pro autory, datum, místo, bez `vyradit`) a odvodit z ní
  `incomplete()`; ověřit testy v `tests/test_model.py` podle scénářů
  Hotovost akce a stávajícími testy `incomplete`
- [ ] 2.2 Přidat `model.touch(doc, stored, jmeno, cas)` (`upravili`
  z uložené verze + položka jména); ověřit testy scénářů Záznam
  o úpravách (první uložení, druhý uživatel, podvržená hodnota)
- [ ] 2.3 Rozšířit `Workspace.list_events()` o `hotovost`, `ukazky`
  (≤ 4 rovnoměrně) a `upravili`; ověřit testy v `tests/test_archive.py`
  (velká a malá akce, nezpracovaná akce, vyřazené soubory)
- [ ] 2.4 V `app.py` doplnit do `GET /api/akce` `drzitel`
  (`jmeno`, `vase` podle `?relace=`, bez relace v odpovědi)
  a v `akce_save` a `akce_finish` volat `model.touch` se jménem
  z `g.user`; ověřit testy v `tests/test_app.py` (držitel, „vase“,
  zápis `upravili`, ignorování hodnoty z klienta)
- [ ] 2.5 Ověřit testem v `tests/test_xmp.py` a `tests/test_index.py`,
  že `upravili` se nedostane do sidecaru ani indexu
- [ ] 2.6 Změřit dobu `GET /api/akce` před a po na kopii archivu
  (jeden běh před a jeden po) a výsledek uvést
  v souhrnu změny

## 3. Klient: seznam akcí

- [ ] 3.1 Přepsat `showList()` na karty podle vybrané varianty (datum,
  název-odkaz, počet, stav a štítky, hotovost, pruh náhledů
  s `loading="lazy"` a zástupnou ikonou, držitel); ověřit ručně scénáře
  Karta akce, Náhledy na kartě, Držitel zámku na kartě, Odznak
  poškozených
- [ ] 3.2 Přidat čisté funkce filtru, hledání (bez diakritiky)
  a řazení do samostatného modulu `static/` a testy v `tests/js`;
  ověřit `node --test tests/js/*.test.mjs` podle scénářů Filtry
  a hledání a Řazení seznamu
- [ ] 3.3 Napojit filtry, hledání a řazení na seznam se stavem v hash
  adrese (`#/?filtr=…`); ověřit ručně scénář Návrat z plochy
  a výchozí řazení

## 4. Kontrolní stránka dokončení

- [ ] 4.1 Rozšířit `missingItems()` o stav, skupinu kontroly a odkazy
  nápravy (údaje akce, soubory, nálezy, poškozené, k vyřazení,
  export); ověřit, že navigátor a lišta plochy fungují beze změny
- [ ] 4.2 Přidat route `#/akce/<název>/dokonceni`: sdílený stav akce
  s plochou (zámek, heartbeat bez uvolnění), přímé otevření, jen pro
  čtení bez zámku, přesměrování nezpracované akce; ověřit ručně scénáře
  Přechod z plochy, Přímý odkaz bez zámku, Nezpracovaná akce
- [ ] 4.3 Vykreslit seznam kontrol, tlačítko Dokončit / Přesto
  dokončit a výsledek dokončení (počty sidecarů, chyby, odkaz na
  seznam); tlačítko Dokončit akci na ploše jen uloží a otevře stránku
  (bez `confirmDialog`); ověřit scénáře požadavku Dokončení akce
  (úplná, neúplná, nepodporovaný soubor, opakované dokončení)
  ve vývojovém režimu
- [ ] 4.4 Odkazy nápravy: plocha s výběrem dotčených souborů, skok na
  oddíl, dialog Uklidit…; ověřit ručně scénář Náprava chybějícího data

## 5. Dokumentace a ověření

- [ ] 5.1 Aktualizovat `README.md` (Datový model: `upravili`;
  Aplikace, Tok práce: seznam akcí, filtry, kontrolní stránka)
  a zmínku v `AGENTS.md`, kdo píše `upravili`; ověřit, že README
  odpovídá specům změny
- [ ] 5.2 Spustit `.venv/bin/python -m pytest -q`
  a `node --test tests/js/*.test.mjs`, projít aplikaci na kopii
  archivu v okně 1280 × 720 i na šířce telefonu a `openspec validate
  fronta-akci --strict`
