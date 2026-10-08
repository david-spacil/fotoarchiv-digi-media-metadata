# Proposal

## Why

V archivu i ve zdrojích importu jsou fotky poškozené na úrovni karty nebo
souborového systému: bloky souboru jsou vynulované, délka zůstala
(issue #10). Vzorky ze 7. 11. 2015 (Samsung SM-G360F):
`20151107_140851.jpg` má nulových prvních 768 KiB a nejde otevřít,
`20151107_135155.jpg` má nulových posledních 119 KiB a místo spodní části
obrazu ukáže šedý pruh. Import dnes takové soubory bez varování přenese
a zjistí se to až chybějícím náhledem. Exiftool druhou vadu nepozná
a dekodér obrázků nuly uprostřed souboru často přijme jako platná data.

## What Changes

- Nová kontrola souboru: jedno čtení souboru, test souvislého úseku
  nul (zarovnaného na 4 KiB, od 64 KiB; u videa jen v obrazových
  datech), dekódování fotky a `ffprobe` u videa. Výsledek *v pořádku*, *podezřelý*
  (otevře se, ale je poškozený) nebo *nečitelný*, vždy s důvodem.
  Výsledek se cachuje v pracovním adresáři podle jména, velikosti
  a času změny.
- Import: kontrola v kroku Přehled s průběhem (stream). Nečitelný soubor
  se nepřenese; podezřelý se nepřenese, pokud ho uživatel výslovně
  nepovolí. Oba jde po potvrzení smazat: nahraný z pracovního adresáře,
  soubor zdroje v `přetřídit` jen v produkčním režimu. Plán a výsledek
  uvedou poškozené soubory zvlášť; zůstanou ve zdroji, resp.
  v pracovním adresáři.
- Import: po přenosu server porovná velikost souboru v cíli s originálem
  a nesoulad uvede ve výsledku. Zpětné čtení obsahu z archivu se
  nedělá (viz design).
- Nový příkaz `python -m fotoarchiv zkontrolovat [AKCE]`: zkontroluje
  kořen a `RAW.ignored/` jedné nebo všech akcí, vypíše nálezy a uloží
  report do pracovního adresáře. Archiv jen čte v obou režimech.
  Report obsahuje i nejdelší úsek nul u souborů pod prahem, aby šel
  práh po prvním průchodu archivem ověřit.
- Mimo rozsah (samostatný change po vyhodnocení průchodu archivem):
  odznak poškozených souborů v aplikaci, kontrola při generování
  náhledu a přesun poškozených souborů akce do `POSKOZENE.ignored/`.

## Capabilities

### New Capabilities
- `file-integrity`: kontrola, zda soubor média není poškozený
  (klasifikace, důvody, cache) a příkaz pro kontrolu akcí v archivu
  s reportem.

### Modified Capabilities
- `photo-import`: kontrola v kroku Přehled, volba u podezřelých
  souborů, smazání poškozeného nahraného souboru, poškozené soubory
  v plánu a výsledku, ověření velikosti po přenosu.
- `unsorted-import`: poškozené soubory zdroje zůstávají ve zdroji,
  smazání jen v produkčním režimu po potvrzení, průběh kontroly přes
  síťový disk.

## Impact

- Kód: nový modul pro kontrolu souboru, `importer.py` (přehled, plán,
  provedení, výsledek), `app.py` (stream kontroly, smazání souboru
  importu), `__main__.py` (příkaz `zkontrolovat`), klient průvodce
  importem v `static/app.js`.
- Závislosti: žádné nové; Pillow už je, `ffprobe` je
  součástí `ffmpeg` (bez něj se video kontroluje jen testem nul).
- Výkon: kontrola zdroje v `přetřídit` přečte celé soubory přes SMB
  (dosud se četly jen kandidáti na duplicitu); zmírňuje cache a to, že
  tentýž průchod spočítá i sha256 pro plán.
- Dokumentace: README (Import, příkazy), AGENTS.md (Příkazy).
- Archiv: import ani příkaz nemění originály; mazání jen po potvrzení
  a jen poškozených souborů importu.
