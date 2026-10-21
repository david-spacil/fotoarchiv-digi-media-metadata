## Why

V nástroji pojmenování osob nejde vzít zpět omyl: překlep ve jménu,
omylem stisknutá klávesa Odložit/Skrýt nebo špatně poznaná osoba se dá
opravit jen přímo v Immichi, protože vyřízená osoba z nástroje zmizí
(issue #54). Navíc seznam návrhů jmen pod polem jména ořízne okno
nástroje, takže návrhy nejsou vidět bez posouvání okna (issue #55).
Totéž hrozí poli jmen v panelu editoru.

## What Changes

- **Krok zpět v nástroji pojmenování:** tlačítko „Zpět“ a zkratka
  Alt+Backspace vrátí poslední pojmenování, skrytí nebo odložení.
  Immich se vrátí do stavu před krokem (jméno se smaže, skrytí zruší,
  odložení zruší) a osoba se znovu nabídne, po pojmenování
  s předvyplněným jménem. Jen jeden krok, jen do zavření nástroje.
- **Sloučení zůstává nevratné:** nabídka sloučení to výslovně řekne
  a po sloučení krok zpět není k dispozici.
- **Ochrana před přepsáním cizí změny:** Zpět se provede, jen když
  osoba v Immichi pořád má stav po kroku; jinak ho server odmítne.
- **Seznam návrhů jmen přes okraj:** všechna pole jmen (nástroj
  pojmenování, autoři a účastníci v panelu) kreslí návrhy nad
  obsahem stránky, mimo ořez okna či panelu; pod polem, a když tam
  není místo (např. klávesnice telefonu), nad ním.
- Nástroj pojmenování ukáže až 10 návrhů jako server (dnes 8).

## Capabilities

### New Capabilities
<!-- žádné -->

### Modified Capabilities
- `person-naming`: nový požadavek Krok zpět; sloučení upozorní na
  nevratnost; zkratka Alt+Backspace v klávesových zkratkách nástroje.
- `person-names`: nový požadavek na zobrazení seznamu návrhů (mimo
  ořez, pod/nad polem) a počet návrhů v nástroji pojmenování.

## Impact

- `fotoarchiv/app.py` — nový endpoint
  `POST /api/akce/<nazev>/osoby/<person_id>/zpet`.
- `fotoarchiv/naming.py` — odebrání jedné osoby z odložených.
- `fotoarchiv/static/naming.js` — stav posledního kroku, tlačítko
  a zkratka Zpět, text nabídky sloučení, 10 návrhů, sdílené
  našeptávání.
- `fotoarchiv/static/app.js` (`namesField`) — sdílené našeptávání.
- Nový modul `fotoarchiv/static/naseptavani.js` — umístění seznamu
  návrhů v horní vrstvě (Popover API).
- `fotoarchiv/static/style.css` — `.suggest` mimo tok stránky.
- Testy: `tests/test_app.py`, `tests/test_naming.py`,
  `tests/js/naming.test.mjs`, nový `tests/js/naseptavani.test.mjs`.
- `docs/navod/pojmenovani-osob.md`.
- Immich: zápis jen přes `PUT /api/people` (jméno, skrytí) jako dnes;
  nová oprávnění klíče nejsou potřeba. Archiv ani `_metadata.json` se
  nemění.
