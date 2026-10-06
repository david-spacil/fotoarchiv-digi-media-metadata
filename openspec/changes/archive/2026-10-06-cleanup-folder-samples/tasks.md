## 1. Server

- [x] 1.1 `cleanup.subfolders` vrací `ukazky` (až 8 rovnoměrně
      z médií, jinak z ostatních souborů); ověřit testem
      v `tests/test_cleanup.py`
- [x] 1.2 Endpoint `GET /api/akce/<akce>/uklid/nahled/<slozka>/<soubor>`
      (jen média v podsložce první úrovně, archiv beze změny); ověřit
      testem v `tests/test_app.py`

## 2. Klient

- [x] 2.1 V `renderCleanup` pás náhledů s názvy, klik otevře dialog
      s náhledem 1600 px; ověřit v prohlížeči na akci s podsložkami

## 3. Dokumentace

- [x] 3.1 Doplnit popis kroku Úklid v `README.md`; ověřit
      `openspec validate cleanup-folder-samples --strict`
