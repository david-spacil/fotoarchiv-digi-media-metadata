## 1. Server

- [x] 1.1 Velikost náhledu jako parametr `thumbnail()` (součást klíče
  cache), endpoint `?velikost=320|1600`, jiné hodnoty 400; ověřit
  pytestem (oddělená cache, druhé volání nečte originál, orientace)
  a `curl` nad fotkou z 2026-04-28.
- [x] 1.2 Endpoint originálu `/api/akce/<n>/soubor/<soubor>` s Range;
  ověřit pytestem (206 pro Range, 404 pro podsložku, RAW a neznámý
  soubor) a že archiv zůstane beze změny.

## 2. Lupa v klientu

- [x] 2.1 Stav `view` a `current`, společná funkce výběru pro mřížku
  i pás (klik, Ctrl, Shift nastavují i aktuální soubor); přepínač
  režimu, Enter a dvojklik do lupy, Esc zpět se zachovaným výběrem;
  ověřit v prohlížeči.
- [x] 2.2 Rozvržení lupy: velká fotka (1600 px, během načítání 320 px),
  video přes `<video>` s pádem na náhled a zprávu; ověřit v prohlížeči
  na fotce G9, fotce na výšku a mp4 ze Samsungu.
- [x] 2.3 Filmový pás: celá akce v pořadí mřížky, předěly a názvy
  skupin, odlišení aktuálního a vybraných, posun na aktuální, klik
  na název skupiny vybere skupinu; ověřit scénáře Ctrl+klik a Shift+klik
  ze spec.
- [x] 2.4 Šipky a Shift+šipky přes hranice skupin, ignorované v polích
  formuláře; předběžné načítání sousedů; ověřit scénáře ze spec
  `loupe-view` a plynulost přepínání nad akcí 2026-04-28.

## 3. Ověření celku

- [x] 3.1 Projít doplňování popisu a osob v lupě nad akcí 2026-04-28,
  přepnout do mřížky a zpět, znovu otevřít akci; ověřit uložení,
  `pytest` a `node --test` a že archiv je beze změny (`find -newer`).
- [x] 3.2 Doplnit do README popis lupy (sekce Aplikace) a do `AGENTS.md`
  nic, pokud se nemění příkazy.
