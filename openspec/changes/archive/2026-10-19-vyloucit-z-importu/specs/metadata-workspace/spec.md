## MODIFIED Requirements

### Requirement: Klávesy v kroku skupin
V kroku „Skupiny a autoři“ průvodce prvním otevřením i importu SHALL
Esc zrušit výběr souborů i skupiny. V kroku importu SHALL Delete
vyloučit vybraná média z importu (viz `photo-import`, Vyloučení
z importu). V průvodci prvním otevřením MUST NOT Delete nic dělat:
krok nekreslí označení k vyřazení. Enter a P MUST NOT v žádném z obou
kroků nic dělat: krok nemá lupu ani skládací panel.

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
