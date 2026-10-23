## MODIFIED Requirements

### Requirement: Klávesy v kroku skupin
V kroku „Skupiny a autoři“ průvodce prvním otevřením i importu SHALL
Esc zrušit výběr souborů i skupiny a Enter otevřít lehkou lupu
s aktuálním souborem (viz `loupe-view`, Lupa v kroku skupin). V kroku
importu SHALL Delete vyloučit vybraná média z importu (viz
`photo-import`, Vyloučení z importu). V průvodci prvním otevřením MUST
NOT Delete nic dělat: krok nekreslí označení k vyřazení. P MUST NOT
v žádném z obou kroků nic dělat: krok nemá skládací panel.

#### Scenario: Esc po výběru všeho
- **WHEN** uživatel v kroku „Skupiny a autoři“ importu stiskne Ctrl+A
  a pak Esc
- **THEN** žádný soubor ani skupina nejsou vybrané

#### Scenario: Delete v průvodci
- **WHEN** v průvodci prvním otevřením jsou vybrané dva soubory
  a uživatel stiskne Delete
- **THEN** soubory nejsou označené k vyřazení a výběr zůstává

#### Scenario: Delete v importu
- **WHEN** v kroku „Skupiny a autoři“ importu jsou vybrané dva soubory
  a uživatel stiskne Delete
- **THEN** soubory jsou vyloučené z importu, nejsou označené
  k vyřazení a výběr zůstává

#### Scenario: Enter v kroku
- **WHEN** v kroku „Skupiny a autoři“ průvodce prvním otevřením je
  aktuální `P1503720.JPG` a uživatel stiskne Enter
- **THEN** otevře se lehká lupa s `P1503720.JPG`

#### Scenario: P v kroku
- **WHEN** v kroku „Skupiny a autoři“ importu uživatel stiskne P
- **THEN** panel zůstane, jak byl, a lupa se neotevře
