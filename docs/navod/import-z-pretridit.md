[← Dokumentace](../README.md)

# Import ze složky přetřídit

- **Import ze složky `přetřídit`:** provedení soubory **přesouvá**
  (přejmenování na stejném svazku, obsah i čas změny zůstanou), nic
  nekopíruje. Měřítkem je poslední plán (snímek cest, velikostí a časů
  změny v `import.json`; provedení bez něj server odmítne a snímek
  spotřebuje): soubor, který od plánu ze zdroje zmizel, je selhaný,
  změněný blokovaný a přibylý se nepřesune a výsledek ho uvede zvlášť.
  Přesun nepřepíše existující soubor; přesun na jiný svazek je
  selhání souboru. Duplicity, blokované, poškozené a nepodporované
  soubory zůstanou ve zdroji. Kontrola přečte každý soubor zdroje
  jednou a tentýž průchod uloží sha256 do `.work/cache/sha256/`, takže
  plán zdroj znovu nečte; jinak by se sha256 počítal jen u souborů,
  jejichž velikost má soubor v kořeni cílové akce nebo jiný soubor
  výběru. Po provedení server smaže odspodu
  podsložky a nakonec zdrojovou složku, jsou-li prázdné nebo jen
  s `Thumbs.db`; složky `*.ignored` nechá. Výsledek uvede, co ve
  zdroji zůstalo a zda složka zanikla. Import bez zbylých podporovaných
  souborů ve zdroji se zruší; zahození importu zdroj nemění. Varianty
  se stejným jménem (např. `Procházka 60/JPEG orig`) se navzájem
  zablokují a nepřesune se nic z nich: podsložku přejmenujte na
  `.ignored` a import zopakujte. Ve vývojovém režimu přehled, plán
  i krok skupin fungují, provedení ne.
- **Stránka Přetřídit** (odkaz ze seznamu akcí): složky první úrovně
  `přetřídit` (bez `.ignored`) s počty fotek, videí, RAWů a ostatních
  souborů, podsložkami, rozsahem dat z EXIF, datem z názvu
  (`d.m.yyyy`, `yyyy_mm_dd`, `yyyy_m_d`, `dd_mm_yyyy`; samotný rok jen
  informativně) a navrženou akcí `YYYY-MM-DD název` (datum nejstarší
  den z EXIF, jinak z názvu, jinak ho doplní uživatel; název = název
  složky). Výpis přijde hned, údaje z EXIF se doplňují po složkách
  (stream); EXIF se cachuje podle jména, velikosti a času změny.
  Složka s rozpracovaným importem uživatele je zvýrazněná. Kliknutí
  založí (nebo obnoví) import s navrženou novou akcí jako cílem
  a otevře přehled.
