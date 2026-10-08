import json
import os
import subprocess

import pytest

from fotoarchiv import integrity
from fotoarchiv.__main__ import main
from fotoarchiv.importer import file_sha256, kind
from fotoarchiv.integrity import OK, SUSPECT, UNREADABLE
from .conftest import snapshot
from .fixtures.integrity import make_samples

# Skutečné dekodéry (jinde je conftest nahrazuje, testy tam nahrávají
# do „.jpg“ textový obsah).
pytestmark = pytest.mark.real_decoders


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    return make_samples.write(tmp_path_factory.mktemp("vzorky"))


def check(samples, name):
    return integrity.check(samples / name, kind(name))


# --- kontrola souboru --------------------------------------------------------

def test_samples_deterministic(tmp_path):
    a = make_samples.write(tmp_path / "a")
    b = make_samples.write(tmp_path / "b")
    for f in sorted(os.listdir(a)):
        assert file_sha256(a / f) == file_sha256(b / f), f


def test_zeros_at_start_unreadable(samples):
    r = check(samples, "nuly_zacatek.jpg")
    assert r["stav"] == UNREADABLE
    assert r["duvody"] == ["soubor nejde otevřít jako obrázek",
                           "768 KiB nul od začátku"]
    assert r["nuly"] == {"delka": 768 * 1024, "od": 0}


def test_zeros_at_end_suspect(samples):
    # Dekodér konec z nul přijme (šedý pruh); pozná ho jen test nul.
    r = check(samples, "nuly_konec.jpg")
    assert r["stav"] == SUSPECT
    assert len(r["duvody"]) == 1 and r["duvody"][0].endswith("nul na konci")


def test_zeros_in_middle_suspect(samples):
    r = check(samples, "nuly_uprostred.jpg")
    assert r["stav"] == SUSPECT
    assert r["duvody"] == ["64 KiB nul uprostřed (od 536 KiB)"]


def test_short_zero_run_ok(samples):
    r = check(samples, "nuly_pod_prahem.jpg")
    assert r["stav"] == OK and r["duvody"] == []
    assert r["nuly"]["delka"] == 24 * 1024


def test_healthy(samples):
    for name in ("ok.jpg", "ok.nef"):
        r = check(samples, name)
        assert (r["stav"], r["duvody"], r["nuly"]) == (OK, [], None), name


def test_truncated_photo_suspect(samples):
    r = check(samples, "useknuty.jpg")
    assert r["stav"] == SUSPECT
    assert r["duvody"] == ["obraz je neúplný (useknutý soubor)"]


def test_truncated_with_end_marker_not_detected(samples):
    # Známé omezení (design): useknutý JPEG zakončený FFD9 dekodér přijme.
    assert check(samples, "useknuty_ffd9.jpg")["stav"] == OK


def test_empty_and_all_zero_unreadable(samples):
    assert check(samples, "prazdny.jpg")["duvody"] == ["prázdný soubor (0 B)"]
    assert check(samples, "jen_nuly.jpg")["duvody"] == \
        ["soubor obsahuje jen nuly"]
    for name in ("prazdny.jpg", "jen_nuly.jpg"):
        assert check(samples, name)["stav"] == UNREADABLE


def test_raw_zero_test_only(samples):
    r = check(samples, "nuly.nef")
    assert r["stav"] == SUSPECT and r["duvody"] == ["128 KiB nul od začátku"]


def test_unaligned_zeros_ignored(tmp_path):
    # Úsek nul, který nezačíná na hranici bloku, se počítá jen od ní.
    data = bytearray(make_samples.noise_jpeg())
    data[1000:1000 + 70 * 1024] = bytes(70 * 1024)
    path = tmp_path / "a.nef"
    path.write_bytes(bytes(data))
    r = integrity.check(path, "raw")
    assert r["nuly"]["od"] == 4096 and r["nuly"]["delka"] < 70 * 1024


def test_partial_last_block_counts(tmp_path):
    data = make_samples.noise_jpeg()
    n = len(data) // 4096 * 4096 - 16 * 4096
    path = tmp_path / "a.nef"
    path.write_bytes(data[:n] + bytes(16 * 4096 + 100))
    r = integrity.check(path, "raw")
    assert r["nuly"] == {"delka": 16 * 4096 + 100, "od": n}
    assert r["duvody"] == ["64 KiB nul na konci"]


@pytest.mark.skipif(not make_samples.shutil.which("ffprobe"),
                    reason="bez ffprobe")
def test_video(samples):
    if not (samples / "ok.mp4").exists():
        pytest.skip("bez ffmpeg")
    assert check(samples, "ok.mp4")["stav"] == OK
    r = check(samples, "bez_moov.mp4")
    assert r["stav"] == UNREADABLE
    assert r["duvody"][0].startswith("video nejde přečíst")


def pcm_samples(samples):
    if not (samples / "ticho_pcm.mov").exists():
        pytest.skip("bez ffmpeg")


def test_silent_pcm_audio_ok(samples):
    # Ticho v nekomprimovaném zvuku (jako P1503720.MP4 z Panasonicu) jsou
    # dlouhé úseky nul; počítají se jen nuly v obrazových datech.
    pcm_samples(samples)
    r = check(samples, "ticho_pcm.mov")
    assert (r["stav"], r["duvody"], r["nuly"]) == (OK, [], None)
    assert r["nuly_rozsah"] == "obraz"
    assert r["nuly_soubor"]["delka"] >= 180 * 1024


def test_zeros_in_video_data_suspect(samples):
    pcm_samples(samples)
    from fotoarchiv import mp4
    path = samples / "nuly_v_obraze.mov"
    r = check(samples, "nuly_v_obraze.mov")
    start = r["nuly"]["od"]
    # Vzorek opravdu nuluje obraz, ne zvuk (druhá cesta: rozsahy).
    assert mp4.overlap(mp4.video_ranges(path), start,
                       start + 64 * 1024)[0] == 64 * 1024
    assert r["stav"] == SUSPECT
    assert r["duvody"] == [f"64 KiB nul v obrazových datech (od "
                           f"{integrity._at(start)})"]


def test_zeros_across_video_and_audio(samples, tmp_path):
    # Úsek přes konec snímku do zvuku: v obraze se počítá jen jeho část.
    pcm_samples(samples)
    from fotoarchiv import mp4
    data = (samples / "ticho_pcm.mov").read_bytes()
    src = samples / "ticho_pcm.mov"
    (first, end), *_ = mp4.video_ranges(src)
    start = end // 4096 * 4096 - 4096
    path = tmp_path / "a.mov"
    path.write_bytes(data[:start] + bytes(80 * 1024) +
                     data[start + 80 * 1024:])
    r = integrity.check(path, "video")
    assert r["stav"] == OK
    assert r["nuly"]["delka"] == end - start < 64 * 1024


def test_video_without_tables_strict(tmp_path):
    # Bez čitelných tabulek (tady prázdný moov) se počítá celý soubor.
    from .test_mp4 import atom
    path = tmp_path / "a.mp4"
    path.write_bytes(atom(b"ftyp", b"isom\0\0\0\0") +
                     atom(b"mdat", bytes(70 * 1024)) + atom(b"moov"))
    r = integrity.check(path, "video")
    assert "nuly_rozsah" not in r
    assert any("nul" in d for d in r["duvody"])


def test_video_without_ffprobe(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity.shutil, "which", lambda name: None)
    path = tmp_path / "a.mp4"
    path.write_bytes(b"cokoli")
    r = integrity.check(path, "video")
    assert r["stav"] == OK
    assert r["poznamka"] == "video ověřeno jen testem nul (chybí ffprobe)"


def test_video_name_with_colon_is_file(tmp_path, samples):
    if not (samples / "ok.mp4").exists():
        pytest.skip("bez ffmpeg")
    path = tmp_path / "http:a.mp4"
    path.write_bytes((samples / "ok.mp4").read_bytes())
    assert integrity.check(path, "video")["stav"] == OK


# --- průběh a sha256 ---------------------------------------------------------

def test_sha256_and_progress(samples, monkeypatch):
    monkeypatch.setattr(integrity, "STEP", 256 * 1024)
    gen = integrity.iter_check(samples / "ok.jpg", "foto")
    steps = []
    while True:
        try:
            steps.append(next(gen))
        except StopIteration as stop:
            result = stop.value
            break
    assert result["sha256"] == file_sha256(samples / "ok.jpg")
    # Průběh i uvnitř souboru (po STEP); čte se po CHUNK = 1 MiB.
    assert steps == [integrity.CHUNK]


# --- cache --------------------------------------------------------------------

def todo(samples, *names):
    return [(n, samples / n, os.stat(samples / n), kind(n)) for n in names]


def drain(gen):
    events = []
    while True:
        try:
            events.append(next(gen))
        except StopIteration as stop:
            return events, stop.value


def test_cache_and_sha_cache(samples, tmp_path, monkeypatch):
    cache = tmp_path / "kontrola" / "akce.json"
    shas = tmp_path / "sha256" / "akce.json"
    files = todo(samples, "ok.jpg", "nuly_konec.jpg")
    events, results = drain(integrity.iter_check_files(files, cache, shas))
    assert results["ok.jpg"]["stav"] == OK
    assert results["nuly_konec.jpg"]["stav"] == SUSPECT
    assert "sha256" not in results["ok.jpg"]
    assert events[0] == {"typ": "kontrola", "souboru": 2,
                         "bajtu": sum(f[2].st_size for f in files)}
    assert events[-1]["hotovo_souboru"] == 2
    stored = json.loads(shas.read_text())
    assert stored["ok.jpg"]["sha256"] == file_sha256(samples / "ok.jpg")
    assert integrity.cached(files, cache) == results

    # Podruhé se nic nečte.
    def no_read(*a, **k):
        raise AssertionError("čte soubor")
    monkeypatch.setattr(integrity, "iter_check", no_read)
    events, again = drain(integrity.iter_check_files(files, cache, shas))
    assert again == results
    assert events[-1] == {"typ": "kontrola_prubeh", "hotovo_souboru": 2,
                          "hotovo_bajtu": events[0]["bajtu"]}


def test_cache_changed_file_rechecked(samples, tmp_path):
    path = tmp_path / "a.jpg"
    path.write_bytes((samples / "ok.jpg").read_bytes())
    cache = tmp_path / "kontrola.json"
    item = [("a.jpg", path, os.stat(path), "foto")]
    assert integrity.check_files(item, cache)["a.jpg"]["stav"] == OK
    path.write_bytes((samples / "nuly_konec.jpg").read_bytes())
    os.utime(path, ns=(1, 1))
    item = [("a.jpg", path, os.stat(path), "foto")]
    assert integrity.cached(item, cache) == {}
    assert integrity.check_files(item, cache)["a.jpg"]["stav"] == SUSPECT


def test_cache_version_invalidates(samples, tmp_path, monkeypatch):
    cache = tmp_path / "kontrola.json"
    files = todo(samples, "ok.jpg")
    integrity.check_files(files, cache)
    monkeypatch.setattr(integrity, "VERSION", integrity.VERSION + 1)
    assert integrity.cached(files, cache) == {}


def test_cache_saved_when_interrupted(samples, tmp_path):
    cache = tmp_path / "kontrola.json"
    gen = integrity.iter_check_files(
        todo(samples, "ok.jpg", "useknuty.jpg"), cache)
    for event in gen:
        if event.get("hotovo_souboru") == 1:
            break
    gen.close()
    assert list(json.loads(cache.read_text())) == ["ok.jpg"]


def test_missing_file_skipped(samples, tmp_path):
    path = tmp_path / "a.jpg"
    path.write_bytes(b"x")
    item = [("a.jpg", path, os.stat(path), "foto")]
    path.unlink()
    assert integrity.check_files(item, tmp_path / "k.json") == {}


def test_real_samples_from_issue():
    """Vzorky z issue #10 (mimo repozitář), jen jsou-li k dispozici."""
    root = os.environ.get("FOTOARCHIV_VZORKY_ISSUE10")
    if not root:
        pytest.skip("FOTOARCHIV_VZORKY_ISSUE10 nenastaveno")
    a = integrity.check(os.path.join(root, "20151107_140851.jpg"), "foto")
    assert a["stav"] == UNREADABLE and "768 KiB nul od začátku" in a["duvody"]
    b = integrity.check(os.path.join(root, "20151107_135155.jpg"), "foto")
    assert b["stav"] == SUSPECT and "119 KiB nul na konci" in b["duvody"]


def test_ffprobe_failure_on_garbage(tmp_path):
    if not make_samples.shutil.which("ffprobe"):
        pytest.skip("bez ffprobe")
    path = tmp_path / "a.mov"
    path.write_bytes(b"\x01" * 5000)
    assert integrity.check(path, "video")["stav"] == UNREADABLE


def test_ffprobe_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr(integrity.shutil, "which", lambda name: "/x")

    def slow(*a, **k):
        raise subprocess.TimeoutExpired("ffprobe", 1)
    monkeypatch.setattr(integrity.subprocess, "run", slow)
    path = tmp_path / "a.mp4"
    path.write_bytes(b"x")
    r = integrity.check(path, "video")
    assert r["stav"] == OK and "nedoběhl" in r["poznamka"]


# --- příkaz zkontrolovat ------------------------------------------------------

A = "2015-11-07 Hlozek"
B = "2026-04-28 kontrola"


@pytest.fixture
def archive(tmp_path, samples):
    root = tmp_path / "archiv"
    a = root / A
    (a / "RAW.ignored").mkdir(parents=True)
    (a / "Video.ignored").mkdir()
    for name in ("ok.jpg", "nuly_zacatek.jpg", "nuly_konec.jpg",
                 "nuly_pod_prahem.jpg"):
        (a / name).write_bytes((samples / name).read_bytes())
    (a / "RAW.ignored" / "P1.NEF").write_bytes(
        (samples / "nuly.nef").read_bytes())
    (a / "RAW.ignored" / "pozn.txt").write_bytes(bytes(100_000))
    (a / "Video.ignored" / "x.jpg").write_bytes(bytes(100_000))
    (a / "Thumbs.db").write_bytes(bytes(100_000))
    (a / "_metadata.json").write_text("{}")
    b = root / (B + ".ignored")  # nedokončená akce skrytá před Immichem
    b.mkdir()
    (b / "P2.JPG").write_bytes((samples / "ok.jpg").read_bytes())
    (root / "přetřídit").mkdir()
    return root


def run(archive, tmp_path, *args):
    main(["zkontrolovat", *args, "--archiv", str(archive),
          "--work", str(tmp_path / "work")])


def report(tmp_path):
    (path,) = (tmp_path / "work" / "kontrola").glob("report-*.json")
    return json.loads(path.read_text())


def test_event_files(archive):
    keys = [t[0] for t in integrity.event_files(archive / A)]
    assert keys == ["nuly_konec.jpg", "nuly_pod_prahem.jpg",
                    "nuly_zacatek.jpg", "ok.jpg", "RAW.ignored/P1.NEF"]


def test_cli_one_event(archive, tmp_path, capsys):
    before = snapshot(archive)
    run(archive, tmp_path, A)
    out = capsys.readouterr().out.splitlines()
    assert f"{A}/nuly_zacatek.jpg: NEČITELNÝ: soubor nejde otevřít jako " \
        "obrázek; 768 KiB nul od začátku" in out
    assert f"{A}/RAW.ignored/P1.NEF: PODEZŘELÝ: 128 KiB nul od začátku" in out
    assert any(o.startswith(f"{A}/nuly_konec.jpg: PODEZŘELÝ: ") for o in out)
    assert "Zkontrolováno 5 souborů v 1 akcích: podezřelých 2, " \
        "nečitelných 1." in out
    assert snapshot(archive) == before
    r = report(tmp_path)
    assert r["dokonceno"] and r["prah_bajtu"] == 64 * 1024
    (akce,) = r["akce"]
    assert (akce["akce"], akce["souboru"], akce["ok"], akce["podezrele"],
            akce["necitelne"]) == (A, 5, 2, 2, 1)
    # Soubor pod prahem je v reportu s nejdelším úsekem (ověření prahu).
    pod = {f["soubor"]: f for f in akce["soubory"]}["nuly_pod_prahem.jpg"]
    assert pod["stav"] == OK and pod["nuly"]["delka"] == 24 * 1024
    assert "ok.jpg" not in {f["soubor"] for f in akce["soubory"]}


def test_cli_whole_archive_hidden_event(archive, tmp_path, capsys):
    before = snapshot(archive)
    run(archive, tmp_path)
    out = capsys.readouterr().out
    assert "Zkontrolováno 6 souborů v 2 akcích" in out
    assert [a["akce"] for a in report(tmp_path)["akce"]] == \
        [B + ".ignored", A]
    assert snapshot(archive) == before
    # Cache podle názvu akce bez přípony (přežije zveřejnění).
    assert (tmp_path / "work" / "cache" / "kontrola" / f"{B}.json").exists()


def test_cli_rerun_uses_cache(archive, tmp_path, monkeypatch, capsys):
    run(archive, tmp_path, A)

    def no_read(*a, **k):
        raise AssertionError("čte soubor")
    monkeypatch.setattr(integrity, "iter_check", no_read)
    for f in (tmp_path / "work" / "kontrola").glob("*.json"):
        f.unlink()
    run(archive, tmp_path, A)
    assert "nečitelných 1" in capsys.readouterr().out


def test_cli_unknown_event(archive, tmp_path):
    with pytest.raises(SystemExit) as e:
        run(archive, tmp_path, "2000-01-01 nic")
    assert "Akce nenalezena" in str(e.value.code)


def test_cli_interrupted_keeps_report(archive, tmp_path, monkeypatch):
    calls = []

    def interrupt(todo, cache_path, sha_cache=None):
        calls.append(cache_path)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return (yield from real(todo, cache_path, sha_cache))
    real = integrity.iter_check_files
    monkeypatch.setattr(integrity, "iter_check_files", interrupt)
    with pytest.raises(SystemExit) as e:
        run(archive, tmp_path)
    assert e.value.code == 130
    r = report(tmp_path)
    assert r["preruseno"] and not r["dokonceno"]
    assert [a["akce"] for a in r["akce"]] == [B + ".ignored"]


def test_read_error_not_cached(samples, tmp_path, monkeypatch):
    path = tmp_path / "a.jpg"
    path.write_bytes((samples / "ok.jpg").read_bytes())
    item = [("a.jpg", path, os.stat(path), "foto")]

    def broken(path, typ):
        raise PermissionError(13, "Permission denied")
        yield
    monkeypatch.setattr(integrity, "iter_check", broken)
    r = integrity.check_files(item, tmp_path / "k.json")["a.jpg"]
    assert r["stav"] == UNREADABLE and r["chyba_cteni"]
    assert r["duvody"] == ["soubor nejde přečíst (Permission denied)"]
    assert not (tmp_path / "k.json").exists()


def test_cli_report_video_with_silence(archive, tmp_path, samples):
    pcm_samples(samples)
    (archive / A / "P1503720.MOV").write_bytes(
        (samples / "ticho_pcm.mov").read_bytes())
    run(archive, tmp_path, A)
    (akce,) = report(tmp_path)["akce"]
    v = {f["soubor"]: f for f in akce["soubory"]}["P1503720.MOV"]
    assert (v["stav"], v["nuly"], v["nuly_rozsah"]) == (OK, None, "obraz")
    assert v["nuly_soubor"]["delka"] >= 180 * 1024


def test_cli_reports_not_overwritten(archive, tmp_path, monkeypatch):
    monkeypatch.setattr("fotoarchiv.__main__.time.strftime",
                        lambda fmt: "20261008-120000")
    run(archive, tmp_path, A)
    run(archive, tmp_path, A)
    assert sorted(p.name for p in (tmp_path / "work" / "kontrola").iterdir()) \
        == ["report-20261008-120000-2.json", "report-20261008-120000.json"]


# --- konzistence akcí a náprava (issue #11) ---------------------------------

def add_findings(archive):
    """Do akce A přidá nálezy všech druhů konzistence."""
    a = archive / A
    (a / "zprava.pdf").write_bytes(b"%PDF-1.4")
    (a / "P999.JPG.xmp").write_text("<x/>")       # osiřelý sidecar
    (a / "P1.RW2").write_bytes(b"raw")            # RAW v kořeni
    (a / "_metadata.json").write_text(json.dumps(
        {"schema": "x", "soubory": {"chybi.jpg": {}}}))


def test_cli_fast_mode_lists_findings(archive, tmp_path, monkeypatch,
                                       capsys):
    add_findings(archive)
    # Obsah souborů se nesmí číst.
    monkeypatch.setattr(integrity, "iter_check_files",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("čte soubor")))
    before = snapshot(archive)
    run(archive, tmp_path, "--rychle")
    out = capsys.readouterr().out
    assert f"{A}: konzistence: nepodporovaný soubor zprava.pdf" in out
    assert "osiřelý sidecar P999.JPG.xmp" in out
    assert "RAW v kořeni P1.RW2" in out
    assert "záznam bez souboru chybi.jpg" in out
    assert "nálezů konzistence 4" in out
    assert snapshot(archive) == before
    r = report(tmp_path)
    assert r["rychle"] and r["dokonceno"] and r["prah_bajtu"] is None
    entries = {a["akce"]: a for a in r["akce"]}
    assert len(entries[A]["nalezy"]) == 4
    assert "souboru" not in entries[A]  # poškození se nekontrolovala
    assert entries[B + ".ignored"]["nalezy"] == []


def test_cli_repair_needs_confirmation(archive, tmp_path, monkeypatch):
    add_findings(archive)
    before = snapshot(archive)
    monkeypatch.setattr("builtins.input", lambda *a: "ne")
    run(archive, tmp_path, "--zapis-do-archivu")
    assert snapshot(archive) == before


def test_cli_repair_confirmed(archive, tmp_path, monkeypatch, capsys):
    add_findings(archive)
    monkeypatch.setattr("builtins.input", lambda *a: "ano")
    run(archive, tmp_path, "--zapis-do-archivu")
    a = archive / A
    assert (a / "ostatni.ignored" / "zprava.pdf").is_file()
    assert (a / "ostatni.ignored" / "P999.JPG.xmp").is_file()
    assert (a / "RAW.ignored" / "P1.RW2").is_file()
    assert not (a / "zprava.pdf").exists()
    out = capsys.readouterr().out
    assert "přesun zprava.pdf → ostatni.ignored/zprava.pdf" in out
    assert "přesun P1.RW2 → RAW.ignored/P1.RW2" in out
    assert "hotovo 3" in out
    # Záznam bez souboru zůstává (jen hlásit) a média na místě.
    assert json.loads((a / "_metadata.json").read_text())["soubory"] == \
        {"chybi.jpg": {}}
    assert (a / "ok.jpg").is_file()
    # Další běh už nemá co napravovat.
    monkeypatch.setattr("builtins.input",
                        lambda *a: (_ for _ in ()).throw(
                            AssertionError("ptá se znovu")))
    run(archive, tmp_path, "--rychle")
