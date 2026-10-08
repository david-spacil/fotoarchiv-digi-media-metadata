# Verze pro hlavičku aplikace: image `.git` nemá, zjistí se tady.
# Bez --dirty, stage nemá pracovní soubory (.dockerignore). Selhání
# gitu (např. .git jako soubor u `git worktree`) build nezastaví.
FROM alpine/git AS verze
WORKDIR /src
COPY .git .git
RUN (git describe --tags --always 2>/dev/null || true) > /VERZE

FROM python:3.12-slim

# exiftool (čtení EXIF ve scan.py) a ffmpeg (náhledy videí);
# tzdata kvůli zoneinfo Europe/Prague v XMP exportu.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libimage-exiftool-perl ffmpeg tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fotoarchiv/ fotoarchiv/
COPY --from=verze /VERZE fotoarchiv/VERZE
# Zdroje v repu mohou mít mód 600 vlastníka; v image musí být čitelné
# pro libovolné UID, pod kterým kontejner běží.
RUN chmod -R a+rX /app

ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Prague \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1

# Zápisy smějí jít jen do /work a /archiv (bind mounty), proto
# neprivilegovaný uživatel; s libovolným UID z compose `user:` funguje
# také — soubory nejsou vlastněné rootem.
USER 1000:1000
EXPOSE 5000

ENTRYPOINT ["python", "-m", "fotoarchiv"]
CMD ["--archiv", "/archiv", "--work", "/work", \
     "--host", "0.0.0.0", "--port", "5000"]
