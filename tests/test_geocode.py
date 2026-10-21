import json

import pytest

from fotoarchiv import geocode

VZORKOV = {"name": "Vzorkov", "lat": "49.1234", "lon": "16.4321",
            "display_name": "Vzorkov, okres Ukázkový, Vzorový kraj, "
                            "Česko",
            "osm_type": "relation", "osm_id": 123456,
            "addresstype": "village"}


class FakeService:
    def __init__(self, answer=(VZORKOV,)):
        self.answer = list(answer)
        self.calls = []
        self.now = 100.0
        self.slept = []

    def fetch(self, query, user_agent):
        self.calls.append((query, user_agent, self.now))
        return self.answer

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def geocoder(tmp_path, service):
    return geocode.Geocoder(tmp_path / "cache", "test@example.org",
                            fetch=service.fetch, clock=service.clock,
                            sleep=service.sleep)


def test_normalize():
    assert geocode.normalize("  ZKUŠEBNÁ ") == "zkušebná"
    assert geocode.normalize("Zkušebná") == "zkušebná"  # NFD
    assert geocode.normalize("Nové   Město") == "nové město"


def test_second_query_from_cache(tmp_path):
    service = FakeService()
    g = geocoder(tmp_path, service)
    found, cached = g.search("Vzorkov")
    assert not cached
    assert found == [{"nazev": "Vzorkov",
                      "popis": VZORKOV["display_name"],
                      "gps": [49.1234, 16.4321],
                      "osm": "relation/123456", "typ": "village"}]
    assert g.search(" vzorkov ") == (found, True)
    assert len(service.calls) == 1
    assert service.calls[0][1] == \
        "fotoarchiv-digi-media-metadata (test@example.org)"
    # Cache přežije restart serveru.
    again = geocoder(tmp_path, service)
    assert again.search("VZORKOV") == (found, True)
    assert len(service.calls) == 1
    stored = json.loads((tmp_path / "cache" / "geokodovani.json")
                        .read_text(encoding="utf-8"))
    assert list(stored) == ["vzorkov"]


def test_candidate_without_osm_object():
    item = {k: v for k, v in VZORKOV.items()
            if k not in ("osm_type", "osm_id")}
    assert "osm" not in geocode.candidate(item)
    assert "osm" not in geocode.candidate({**VZORKOV, "osm_id": None})
    assert geocode.candidate(VZORKOV)["osm"] == "relation/123456"


def test_interval_between_queries(tmp_path):
    service = FakeService()
    g = geocoder(tmp_path, service)
    g.search("a")
    service.now += 0.3
    g.search("b")
    assert service.slept == [pytest.approx(0.8)]
    assert service.calls[1][2] - service.calls[0][2] == \
        pytest.approx(geocode.INTERVAL)
    service.now += 5
    g.search("c")
    assert len(service.slept) == 1


def test_empty_answer_cached(tmp_path):
    service = FakeService(answer=[])
    g = geocoder(tmp_path, service)
    assert g.search("u rybníka") == ([], False)
    assert g.search("u rybníka") == ([], True)
    assert len(service.calls) == 1


def test_error_not_cached(tmp_path):
    service = FakeService()
    calls = []

    def failing(query, user_agent):
        calls.append(query)
        raise geocode.GeocodeError("timeout")

    g = geocode.Geocoder(tmp_path / "cache", "x", fetch=failing,
                         clock=service.clock, sleep=service.sleep)
    with pytest.raises(geocode.GeocodeError):
        g.search("Vzorkov")
    with pytest.raises(geocode.GeocodeError):
        g.search("Vzorkov")
    assert len(calls) == 2


def test_contact_read_per_query(tmp_path):
    service = FakeService(answer=[])
    contact = geocode.Contact(tmp_path / "work")
    g = geocode.Geocoder(tmp_path / "cache", contact.load,
                         fetch=service.fetch, clock=service.clock,
                         sleep=service.sleep)
    assert not g.enabled
    with pytest.raises(geocode.GeocodeError):
        g.search("a")
    assert service.calls == []
    contact.save("archiv@example.cz")
    assert (tmp_path / "work" / "nominatim.json").stat().st_mode & 0o777 \
        == 0o600
    g.search("a")
    contact.save("jiny@example.cz")  # bez restartu
    g.search("b")
    assert [ua for _, ua, _ in service.calls] == [
        "fotoarchiv-digi-media-metadata (archiv@example.cz)",
        "fotoarchiv-digi-media-metadata (jiny@example.cz)"]
