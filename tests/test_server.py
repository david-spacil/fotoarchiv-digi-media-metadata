import http.client
import json
import socket
import threading
import time
from urllib.parse import quote

import pytest
from cheroot import wsgi

from fotoarchiv import immich
from fotoarchiv.__main__ import main, serve
from fotoarchiv.app import create_app
from .conftest import make_tree

pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnraisableExceptionWarning")


@pytest.fixture
def base_env(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    return archiv, work


@pytest.fixture
def live_server(tmp_path, monkeypatch):
    """Spustí aplikaci se skutečným serverem cheroot na volném portu."""
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr("fotoarchiv.scan.run_exiftool", lambda d, n: {})
    app = create_app(archiv, work, zapis=False, prihlaseni=False)
    server = wsgi.Server(("127.0.0.1", 0), app)
    server.prepare()
    thread = threading.Thread(target=server.serve, daemon=True)
    thread.start()
    host, port = server.bind_addr
    yield app, host, port, archiv, work
    server.stop()
    thread.join(timeout=2)


def test_serve_starts_and_stops_on_keyboard_interrupt(monkeypatch):
    called = {}

    class DummyServer:
        def __init__(self, bind_addr, wsgi_app, numthreads=10):
            called["init"] = (bind_addr, numthreads)

        def start(self):
            called["started"] = True
            raise KeyboardInterrupt

        def stop(self):
            called["stopped"] = True

    monkeypatch.setattr("fotoarchiv.__main__.wsgi.Server", DummyServer)
    serve(None, "127.0.0.1", 5000, 16)
    assert called["init"] == (("127.0.0.1", 5000), 16)
    assert called["started"] is True
    assert called["stopped"] is True


def test_main_calls_serve_with_default_vlakna(base_env, monkeypatch):
    archiv, work = base_env
    captured = {}
    monkeypatch.setattr("fotoarchiv.__main__.serve",
                        lambda app, host, port, threads: captured.update(
                            host=host, port=port, threads=threads))
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni"])
    assert captured == {"host": "127.0.0.1", "port": 5000, "threads": 32}


def test_main_calls_serve_with_custom_vlakna(base_env, monkeypatch):
    archiv, work = base_env
    captured = {}
    monkeypatch.setattr("fotoarchiv.__main__.serve",
                        lambda app, host, port, threads: captured.update(
                            threads=threads))
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni",
          "--vlakna", "8"])
    assert captured["threads"] == 8


def test_main_rejects_vlakna_less_than_one(base_env):
    archiv, work = base_env
    for val in ("0", "-1"):
        with pytest.raises(SystemExit):
            main(["--archiv", str(archiv), "--work", str(work),
                  "--bez-prihlaseni", "--vlakna", val])


def test_main_debug_calls_app_run(base_env, monkeypatch):
    archiv, work = base_env
    captured = {}
    monkeypatch.setattr("fotoarchiv.__main__.serve",
                        lambda *a, **k: pytest.fail("serve nesmí být voláno"))
    monkeypatch.setattr("flask.Flask.run",
                        lambda self, **kw: captured.update(kw))
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni",
          "--debug"])
    assert captured.get("debug") is True
    assert captured.get("threaded") is True


def test_debug_immich_interval_handling(base_env, monkeypatch):
    archiv, work = base_env
    calls = []
    real_create_app = create_app

    def fake_create_app(*args, **kwargs):
        calls.append(kwargs.get("immich_interval"))
        return real_create_app(*args, **kwargs)

    monkeypatch.setattr("fotoarchiv.__main__.create_app", fake_create_app)
    monkeypatch.setattr("fotoarchiv.__main__.serve", lambda *a, **k: None)
    monkeypatch.setattr("flask.Flask.run", lambda *a, **k: None)

    # 1. --debug bez WERKZEUG_RUN_MAIN (hlídací proces reloaderu)
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni",
          "--debug"])
    assert calls[-1] is None

    # 2. --debug s WERKZEUG_RUN_MAIN (obslužný proces)
    monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni",
          "--debug"])
    assert calls[-1] == immich.INTERVAL

    # 3. bez --debug
    monkeypatch.delenv("WERKZEUG_RUN_MAIN", raising=False)
    main(["--archiv", str(archiv), "--work", str(work), "--bez-prihlaseni"])
    assert calls[-1] == immich.INTERVAL


def test_real_server_streamed_upload(live_server):
    app, host, port, _, _ = live_server
    # Vytvořit import
    conn = http.client.HTTPConnection(host, port)
    conn.request("POST", "/api/import",
                 body=json.dumps({"jmeno": "Spáčil, David", "celkem": 1}))
    resp = conn.getresponse()
    assert resp.status == 200
    import_id = json.loads(resp.read().decode())["id"]
    conn.close()

    total_size = (1024 * 1024) + (512 * 1024)
    chunk1 = b"A" * (1024 * 1024)
    chunk2 = b"B" * (512 * 1024)

    s = socket.create_connection((host, port))
    q_jmeno = quote("Spáčil, David")
    req = (f"POST /api/import/{import_id}/soubor?jmeno={q_jmeno}"
           f"&cesta=test.jpg&relace=r1 HTTP/1.1\r\n"
           f"Host: {host}\r\nContent-Length: {total_size}\r\n"
           f"Connection: close\r\n\r\n")
    s.sendall(req.encode("utf-8"))

    # První blok (1 MiB)
    s.sendall(chunk1)

    # Jiná záložka vidí průběžný nahrávaný stav před koncem těla
    imports = app.config["IMPORTS"]
    deadline = time.time() + 2.0
    active = {}
    while time.time() < deadline:
        active = imports.activity(import_id, relace="r2")
        if active.get("nahrava"):
            break
        time.sleep(0.02)
    assert active.get("nahrava") == [{
        "cesta": "test.jpg",
        "prijato": 1024 * 1024,
        "velikost": total_size,
    }]

    # Druhý blok (512 KiB)
    s.sendall(chunk2)
    f = s.makefile("rb")
    status = f.readline().decode()
    assert "200 OK" in status
    f.close()
    s.close()

    # Soubor nad 1 MiB se uložil celý
    record = imports.get(import_id, "Spáčil, David")
    assert len(record["soubory"]) == 1
    assert record["soubory"][0]["velikost"] == total_size


def test_real_server_ndjson_and_disconnect(live_server, monkeypatch):
    app, host, port, _, _ = live_server
    closed = threading.Event()

    def fake_overview(*args, **kwargs):
        try:
            for i in range(50):
                yield {"typ": "slozka", "krok": i}
                time.sleep(0.02)
        except GeneratorExit:
            closed.set()
            raise

    monkeypatch.setattr("fotoarchiv.unsorted.iter_overview", fake_overview)

    s = socket.create_connection((host, port))
    s.sendall(f"GET /api/pretridit HTTP/1.0\r\nHost: {host}\r\n\r\n"
              .encode("utf-8"))
    f = s.makefile("rb")
    while True:
        line = f.readline()
        if line in (b"\r\n", b"\n"):
            break

    # Přečteme první řádky (v HTTP/1.0 čisté řádky bez chunked framing)
    line1 = json.loads(f.readline().decode().strip())
    assert line1 == {"typ": "slozka", "krok": 0}

    line2 = json.loads(f.readline().decode().strip())
    assert line2 == {"typ": "slozka", "krok": 1}

    # Zavřeme spojení uprostřed streamu
    f.close()
    s.close()

    assert closed.wait(timeout=2)


def test_real_server_range_request(live_server):
    _, host, port, archiv, _ = live_server
    event = "2026-04-28 akce"
    content = b"0123456789abcdefghij"
    make_tree(archiv, {f"{event}/": {"video.mp4": content.decode("ascii")}})

    conn = http.client.HTTPConnection(host, port)
    conn.request("GET", f"/api/akce/{quote(event)}/soubor/video.mp4",
                 headers={"Range": "bytes=4-9"})
    resp = conn.getresponse()
    assert resp.status == 206
    assert resp.getheader("Content-Range") == f"bytes 4-9/{len(content)}"
    assert resp.read() == content[4:10]
    conn.close()
