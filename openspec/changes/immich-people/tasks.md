## 0. Ověření orientace

- [ ] 0.1 V testovací knihovně najít (nebo doplnit) fotku na výšku
      s EXIF Orientation ≠ 1; porovnat `imageWidth/Height`
      a obdélníky z `/api/faces` s rozměry originálu a otočeného obrazu
- [ ] 0.2 Zkušebně zapsat MWG sidecar k takové fotce v testovací
      knihovně a ověřit, kam Immich obličej umístí
- [ ] 0.3 Výsledek zapsat do design.md (Orientace) a podle něj doplnit
      přepočet v úkolech 3.2 a 5.1

## 1. Model a export

- [ ] 1.1 `obliceje` mimo dědění v `model.py` a `static/inherit.js`,
      upravit fixtury `tests/fixtures/inheritance`
- [ ] 1.2 Při uložení odstranit `osoby` všude a `obliceje` mimo
      soubory; test
- [ ] 1.3 `xmp.py`: vypustit tagy `osoba/…`; upravit `tests/test_xmp.py`
- [ ] 1.4 `names.py`: jména z `obliceje[].jmeno` místo `osoby`; test

## 2. Nastavení Immiche

- [ ] 2.1 Načtení a atomický zápis `.work/immich.json` s právy `0600`
- [ ] 2.2 API `GET/PUT/DELETE /api/immich` bez klíče v odpovědi; změna
      adresy bez klíče → chyba; testy
- [ ] 2.3 `POST /api/immich/test` (verze, osoby, obličeje) s
      podvrženým HTTP; testy

## 3. Synchronizace

- [ ] 3.1 `fotoarchiv/immich.py`: klient (`x-api-key`, timeout,
      stránkování osob, hledání podle osoby, `/api/faces`)
- [ ] 3.2 Mapa (akce, soubor) → pojmenované obličeje z posledních dvou
      částí `originalPath`; přepočet oblasti a zaokrouhlení; kanonizace
      jmen přes `names.py`
- [ ] 3.3 Zápis akce: jen při změně, pod zámkem `immich-sync`,
      přeskočit cizí zámek, posun záznamu o exportu
- [ ] 3.4 Vlákno v serveru (start + 15 min), `POST /api/immich/sync`,
      stav posledního běhu (čas, změněné/přeskočené akce, chyba)
- [ ] 3.5 Testy: nový a odebraný obličej, nepojmenovaný ignorován,
      přepočet (i jiné měřítko), akce bez metadat, zamčená akce,
      selhání dotazu nic nezapíše, export zůstane aktuální

## 4. Klient

- [ ] 4.1 Stránka `#/nastaveni` (adresa, klíč, Otestovat, Smazat,
      Načíst osoby, stav posledního běhu) a odkaz v hlavičce
- [ ] 4.2 Pole osob u souboru jen pro čtení (jména z `obliceje`,
      „z Immiche“), bez pole u skupiny a akce, „Immich není napojen“
      bez nastavení
- [ ] 4.3 Ukládaný diff nesmí obsahovat `obliceje` ani `osoby`; osoby
      mimo lištu chybějících údajů
- [ ] 4.4 `node --test tests/js` a `pytest` zelené

## 5. Export pro obnovu

- [ ] 5.1 `xmp.py`: `mwg-rs:Regions` s `AppliedToDimensions` (rozměry
      originálu přes Pillow) a oblastmi `Face`; deterministický výstup
- [ ] 5.2 `exportovat --obliceje`; nemění záznam o exportu; testy
- [ ] 5.3 Zkušební obnova: sidecary jedné akce s `--obliceje`
      v testovací knihovně Immiche se zapnutým importem obličejů;
      ověřit osoby a polohu obličejů

## 6. Ověření a dokumentace

- [ ] 6.1 Jeden běh synchronizace proti skutečnému Immichi (RO klíč)
      na akci `2026-09-08 Konference Dějiny archeologie` ve vývojovém
      režimu; porovnat s odpovědí API z 6. 10. 2026
- [ ] 6.2 README (datový model `obliceje`, Výstupy — tabulka bez `osoby`,
      obnova obličejů, Aplikace, Immich), AGENTS.md (invariant:
      `obliceje` píše jen synchronizace)
