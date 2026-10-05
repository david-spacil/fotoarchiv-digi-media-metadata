## ADDED Requirements

### Requirement: Velké náhledy a originál videa
Aplikace SHALL umět ke každé fotce vytvořit velký náhled (delší strana
kolem 1600 px, se zachovanou EXIF orientací). Velké náhledy MUST být
uloženy v lokální cache mimo archiv a znovu použity, dokud se soubor
nezmění. Videa SHALL být klientovi dostupná k přehrání přímo z archivu
s podporou čtení po částech; aplikace přitom MUST NOT do archivu nic
zapisovat. Vydat SHALL jít jen fotky a videa v kořeni akce.

#### Scenario: Velký náhled z cache
- **WHEN** uživatel v lupě podruhé zobrazí fotku, která se nezměnila
- **THEN** velký náhled se načte z cache bez čtení originálu

#### Scenario: Přetáčení videa
- **WHEN** uživatel v přehrávači přeskočí doprostřed videa
- **THEN** aplikace pošle jen požadovanou část souboru

#### Scenario: Soubor mimo kořen
- **WHEN** klient požádá o soubor z podsložky nebo o soubor, který není
  fotka ani video
- **THEN** aplikace požadavek odmítne
