# Spec Delta

## Purpose

Desktopový klient pro Windows a Linux, který z telefonu připojeného
kabelem nahraje vybraná média s originálními metadaty (včetně GPS)
do importu aplikace v jednom kroku.

## ADDED Requirements

### Requirement: Nalezení telefonu
Klient SHALL najít telefon připojený kabelem v režimu přenosu souborů
(MTP) bez vývojářského režimu a bez instalace čehokoli do telefonu.
Je-li připojeno víc zařízení s médii, klient MUST nechat uživatele
vybrat. Když žádné není, klient SHALL uživateli říct, že má telefon
připojit, odemknout a zapnout přenos souborů.

#### Scenario: Telefon a čtečka karet
- **WHEN** je připojený Pixel 8a a čtečka SD karet bez karty
- **THEN** klient nabídne Pixel 8a a prázdná čtečka výpis nezastaví

#### Scenario: Zamčený telefon
- **WHEN** telefon je připojený, ale zamčený
- **THEN** klient zobrazí výzvu k odemčení a po odemčení výpis načte

### Requirement: Výpis médií z fotoaparátu
Klient SHALL vypsat fotky a videa z fotoaparátu telefonu (`DCIM`,
bez WhatsAppu, snímků obrazovky a podobně) s náhledem, názvem
a datem, seřazené od nejnovějších.

#### Scenario: Řazení
- **WHEN** telefon má `PXL_20260101_120000000.MP.jpg`
  a `PXL_20260102_090000000.jpg`
- **THEN** klient ukáže `PXL_20260102_090000000.jpg` jako první

### Requirement: Výběr médií
Uživatel SHALL moci označit jednotlivá média, souvislý rozsah a všechna
nová. Klient SHALL ukázat počet a celkovou velikost výběru.

#### Scenario: Jen nové
- **WHEN** uživatel zvolí „vybrat nové“
- **THEN** označí se právě média, která klient z tohoto telefonu ještě
  nenahrál

### Requirement: Evidence nahraných
Klient SHALL si u každého telefonu pamatovat média, která úspěšně
nahrál, a ve výpisu je označit. Evidence MUST být jen na počítači
uživatele, ne v archivu ani na serveru.

#### Scenario: Druhé připojení
- **WHEN** uživatel včera nahrál 20 fotek a dnes telefon připojí znovu
- **THEN** těch 20 fotek je označeno jako nahrané a „vybrat nové“ je
  nevybere

### Requirement: Nahrání originálů
Klient MUST poslat na server originální bajty souborů z telefonu, beze
změny metadat (GPS, EXIF, vložené video Motion Photo). Kopie
na počítači MUST být jen dočasná a klient ji MUST po nahrání smazat.

#### Scenario: Zachovaná poloha
- **WHEN** klient nahraje `PXL_20260101_120000000.MP.jpg` s polohou
  50.00000 N, 15.00000 E
- **THEN** soubor v importu má stejný SHA-256 jako originál v telefonu
  a přehled importu ho neoznačí jako fotku s odebranou polohou

### Requirement: Napojení na import aplikace
Klient SHALL přihlásit uživatele jeho loginem a heslem v aplikaci,
založit nový import a nahrát do něj výběr. Po nahrání SHALL otevřít
výchozí prohlížeč na průvodci tímto importem. Klient MUST NOT ukládat
heslo.

#### Scenario: Pokračování v prohlížeči
- **WHEN** klient nahraje 12 fotek do nového importu
- **THEN** prohlížeč otevře `#/import/<id>` a uživatel přihlášený
  stejným loginem vidí přehled s 12 fotkami

#### Scenario: Přerušené nahrávání
- **WHEN** se během nahrávání odpojí telefon
- **THEN** klient ohlásí, které soubory se nenahrály, do evidence
  zapíše jen nahrané a archiv zůstane beze změny

### Requirement: Spuštění po připojení
Klient SHALL jít spustit z nabídky, kterou systém ukáže po připojení
telefonu (AutoPlay ve Windows, obsluha médií s fotkami v Linuxu),
a také ručně.

#### Scenario: AutoPlay
- **WHEN** uživatel ve Windows připojí telefon a v nabídce AutoPlay
  zvolí Fotoarchiv
- **THEN** klient se spustí s tímto telefonem vybraným
