# Design

## Context

Krok autoři skupin (`renderAuthorsStep` v `static/app.js`) skládá pro
každou skupinu `fieldset` s pásem náhledů a řádkem `fieldRow(targetsFor(
"skupina", [gid]), "autori", …)`. `fieldRow` se vykreslí jednou: stav
„zděděno z akce“ a zděděná jména spočítá při vzniku a sám se
nepřepočítá, když se změní vyšší úroveň.

Dědění `autori` z akce na skupinu a soubor už funguje (`resolveGroup`,
`resolve` v `inherit.js` a `model.py`); `missing()` počítá skupinu bez
autorů ze zděděné hodnoty, takže skupina se zděděnými autory akce už
dnes mezi ně nepatří. Krok údaje akce autory vyřazuje filtrem
`FIELDS.akce.filter((k) => k !== "autori")`.

## Goals / Non-Goals

**Goals:**
- Zadat autory akce v průvodci jednou a vidět, které skupiny je dědí.

**Non-Goals:**
- Změna dědění, datového modelu, exportu nebo lišty chybějících údajů.
- Přejmenování kroku „Autoři skupin“ (spec ho tak uvádí na víc
  místech; obsah kroku stačí doplnit).
- Pole autorů v kroku údaje akce (zůstane filtrované).

## Decisions

- **Pole akce nahoře v kroku autorů, ne v kroku údaje akce.** Autoři
  akce a skupin spolu souvisejí (dědění), a uživatel tak vidí výsledek
  hned pod sebou. Alternativa (vrátit pole do kroku údaje akce) by
  oddělila zadání od skupin, kterých se týká.
- **Řádek akce vlastní `fieldset` s legendou „Celá akce“** a krátkou
  nápovědou „Skupiny bez vlastních autorů je zdědí“, stejný
  `fieldRow(targetsFor("akce", []), "autori", onChange)` jako na ploše.
- **Překreslení jen řádků autorů skupin** při změně autorů akce:
  `onChange` nahradí každý skupinový `fieldRow` novým (`replaceWith`),
  pole akce zůstane (zachová fokus a rozepsaný text). Překreslit celý
  krok by vstup akce zničil uprostřed psaní.
- **Upozornění při dokončení** (`m.skupinyBezAutoru`) zůstává beze
  změny; po zadání autorů akce se jen vynuluje tlačítko „Přesto
  dokončit“, aby nezůstalo z dřívějšího pokusu (stav `dataset.confirm`
  a text varování).
- **Test:** nový fixture dědění `autori-jen-u-akce.json` (skupina bez
  autorů dědí z akce, druhá skupina je přepisuje) testuje Python i JS
  přes stávající společné testy; plus test `missing()` / `incomplete()`,
  že skupina se zděděnými autory akce nechybí.

## Risks / Trade-offs

- [Uživatel zadá autory akce i skupin a nevšimne si, že skupina akce
  přepisuje] → skupinové pole ukazuje „zadáno“ vs. „zděděno z akce“
  stejně jako na ploše, s odkazem „vrátit na zděděné“.
- [Autoři akce zadaní „pro jistotu“ zakryjí skupinu, kterou fotil někdo
  jiný] → stejné riziko jako na ploše dnes; nápověda u pole říká, že se
  dědí.
