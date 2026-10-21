## ADDED Requirements

### Requirement: Zobrazení návrhů
Seznam návrhů jmen SHALL ležet nad obsahem stránky a MUST NOT ho
oříznout okno ani panel, ve kterém je pole jména; SHALL být celý
vidět a zarovnaný s polem. Otevírá se pod polem; nevejde-li se tam do
viditelné části okna (např. nad klávesnici telefonu), SHALL se otevřít
nad polem. Platí pro všechna pole jmen osob: nástroj pojmenování
i autory a účastníky v panelu. Posun obsahu pod seznamem SHALL seznam
zavřít.

#### Scenario: Pole dole v okně nástroje
- **WHEN** archivář v nástroji pojmenování napíše do pole jména `vz`
  a server vrátí 10 návrhů
- **THEN** všech 10 návrhů je vidět bez posouvání okna nástroje, i ty,
  které sahají pod jeho dolní okraj

#### Scenario: Málo místa pod polem
- **WHEN** pod polem jména zbývá do konce viditelné části okna méně
  místa, než seznam potřebuje, a nad polem víc
- **THEN** seznam se otevře nad polem

#### Scenario: Klávesnice telefonu
- **WHEN** na telefonu klávesnice zakrývá spodní polovinu obrazovky
  a pole jména je těsně nad ní
- **THEN** seznam se otevře nad polem a není schovaný pod klávesnicí

#### Scenario: Pole v panelu
- **WHEN** archivář píše autora skupiny do pole u dolního okraje
  panelu
- **THEN** seznam návrhů není panelem oříznutý a panel se kvůli němu
  neposune

#### Scenario: Posun pod seznamem
- **WHEN** je seznam otevřený a archivář posune panel nebo okno
- **THEN** seznam se zavře a v poli zůstane rozepsaný text

### Requirement: Počet návrhů
Nástroj pojmenování SHALL nabídnout tolik návrhů, kolik jich vrátí
server (nejvýš 10). Panel nabízí návrhy beze změny počtu.

#### Scenario: Deset shod
- **WHEN** na dotaz v nástroji pojmenování odpovídá 12 jmen ze seznamu
- **THEN** nástroj nabídne 10 návrhů
