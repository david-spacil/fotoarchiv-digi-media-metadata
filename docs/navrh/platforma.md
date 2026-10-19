[← Dokumentace](../README.md)

# Platforma a náhledy

Metadata (JPG, mp4) čte `exiftool`. Náhledy
(320 px do mřížky, 1600 px do lupy) se cachují lokálně mimo archiv —
archiv leží na SMB; lupa si sousední fotky načítá předem. Videa se do
lupy posílají přímo z archivu, jen ke čtení.

Primárně Linux (Fedora). Kolegové na Windows jsou žádoucí, ale ne
priorita: snadné spuštění na Windows se řeší, jen pokud nebude stát
dny práce.
