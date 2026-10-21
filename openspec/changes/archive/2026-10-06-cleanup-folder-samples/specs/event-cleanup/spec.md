## ADDED Requirements

### Requirement: Ukázky obsahu podsložky
Průvodce SHALL u každé nalezené podsložky ukázat až 8 souborů vybraných
rovnoměrně podle abecedy z jejích fotek a videí, každý s náhledem
a názvem souboru. Neobsahuje-li podsložka fotky ani videa, SHALL se
stejně vybrat z ostatních souborů (bez `Thumbs.db`) a ukázat jen jejich
názvy. Klik na náhled SHALL ukázat zvětšený náhled. Zobrazení ukázek
MUST NOT v archivu nic změnit.

#### Scenario: Podsložka s fotkami
- **WHEN** podsložka `VZK 2026` obsahuje 13 fotek
- **THEN** průvodce u ní ukáže 8 náhledů s názvy souborů od první
  fotky po některou z posledních dvou, ne prvních 8 fotek

#### Scenario: Podsložka bez fotek
- **WHEN** podsložka `Prezentační` obsahuje jen soubory PPTX a PDF
- **THEN** průvodce u ní ukáže jejich názvy bez náhledů
