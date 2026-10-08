# Tasks

## 1. Příprava

- [ ] 1.1 Vytvořit venv a spustit výchozí testy (`.venv/bin/python -m
      pytest -q`, `node --test tests/js/*.test.mjs`); ověřit nenulové
      počty testů a že vše prochází

## 2. Zjištění verze na serveru

- [ ] 2.1 Nový modul `fotoarchiv/version.py`: `app_version()` zkusí
      `git describe --tags --always --dirty` v kořeni repozitáře (jen
      když existuje `.git`), pak soubor `fotoarchiv/VERZE`, jinak
      `None`; testy v `tests/test_version.py` (git repo s tagem, dirty,
      soubor, nic) a ověřit, že prochází
- [ ] 2.2 `create_app` zjistí verzi jednou, `/api/info` ji vrací jako
      `verze`; test v `tests/test_app.py`
- [ ] 2.3 `fotoarchiv/VERZE` do `.gitignore`

## 3. Hlavička

- [ ] 3.1 V `header()` v `app.js` drobný text verze vedle názvu
      („verze neznámá“ pro `null`), styl v `style.css`; ověřit
      v prohlížeči, že je vidět a výška hlavičky se nemění

## 4. Docker a dokumentace

- [ ] 4.1 `Dockerfile`: stage `alpine/git` zapíše `git describe --tags
      --always` (při chybě prázdně), výsledný image ho zkopíruje do
      `fotoarchiv/VERZE`; z `.dockerignore` odebrat `.git`; ověřit
      `docker build` (je-li Docker k dispozici), že image obsahuje
      `VERZE` a ne `.git`
- [ ] 4.2 README: odkud se verze bere (Lokální spuštění, Docker)
