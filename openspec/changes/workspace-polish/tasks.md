## 1. Stálá výška hlavičky

- [ ] 1.1 V prohlížeči ověřit příčinu poskočení (zalomení `.paths` při
      delším textu stavu)
- [ ] 1.2 CSS: `#save-status` bez zalomení s `min-width`, `.paths`
      jednořádkově s ořezem, plná cesta v `title`
- [ ] 1.3 Ověřit na úzkém i širokém okně přepínání všech stavů

## 2. Kalendář u data pořízení

- [ ] 2.1 K poli typu `datetime` přidat tlačítko se skrytým
      `<input type="date">` a `showPicker()` (s fallbackem)
- [ ] 2.2 Zvolený den nahradí datum a zachová čas; hodnota bez času
      zůstane bez času
- [ ] 2.3 Výběr s rozdílnými hodnotami: přepsat den každému souboru se
      zachováním jeho času
- [ ] 2.4 Ověřit scénáře ze specifikace (s časem, WhatsApp, prázdné,
      rozdílný výběr)

## 3. Dokončit akci jen při změnách

- [ ] 3.1 Funkce „je co exportovat“ (neuloženo, verze ≠ exportVersion,
      neaktuální sidecary, selhaný export, chybějící kontrola)
- [ ] 3.2 Tlačítko Dokončit akci vypnout u dokončené akce bez změn;
      přepočítat při změně stavu ukládání a exportu
- [ ] 3.3 Třídu `pending` u `#export-status` odvodit z téže funkce
      místo regulárního výrazu
- [ ] 3.4 Ověřit scénáře: dokončená beze změn, úprava po dokončení,
      rozpracovaná akce, selhaný export

## 4. Dokumentace

- [ ] 4.1 README (Aplikace, Dokončení akce): tlačítko neaktivní bez
      změn, kalendář u data pořízení
