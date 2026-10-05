from fotoarchiv.lock import Locks


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def locks():
    clock = Clock()
    return Locks(timeout=300, clock=clock), clock


def test_free_event_acquired():
    l, _ = locks()
    ok, info = l.acquire("A", "r1", "Spáčil, David")
    assert ok and info["jmeno"] == "Spáčil, David"
    assert l.holds("A", "r1") and not l.holds("A", "r2")
    assert not l.holds("A", None)


def test_busy_event_returns_holder():
    l, clock = locks()
    l.acquire("A", "r1", "Spáčil, David")
    clock.t += 42
    ok, info = l.acquire("A", "r2", "Kopáčová, Jana")
    assert not ok
    assert info["jmeno"] == "Spáčil, David"
    assert info["heartbeat_pred_s"] == 42
    assert l.holds("A", "r1")


def test_reacquire_by_same_session():
    l, _ = locks()
    l.acquire("A", "r1", "X")
    assert l.acquire("A", "r1", "X")[0]


def test_one_lock_per_session():
    l, _ = locks()
    l.acquire("A", "r1", "X")
    l.acquire("B", "r1", "X")
    assert l.holder("A") is None and l.holds("B", "r1")
    assert l.acquire("A", "r2", "Y")[0]


def test_heartbeat_keeps_lock():
    l, clock = locks()
    l.acquire("A", "r1", "X")
    for _ in range(3):
        clock.t += 200
        assert l.heartbeat("A", "r1")
    assert not l.acquire("A", "r2", "Y")[0]


def test_abandoned_after_timeout():
    l, clock = locks()
    l.acquire("A", "r1", "X")
    clock.t += 300
    assert not l.acquire("A", "r2", "Y")[0]
    clock.t += 1
    assert l.acquire("A", "r2", "Y")[0]


def test_lost_lock_heartbeat_rejected():
    l, clock = locks()
    l.acquire("A", "r1", "X")
    clock.t += 301
    l.acquire("A", "r2", "Y")
    assert not l.heartbeat("A", "r1")
    assert not l.holds("A", "r1") and l.holds("A", "r2")


def test_release_only_by_holder():
    l, _ = locks()
    l.acquire("A", "r1", "X")
    l.release("A", "r2")
    assert l.holds("A", "r1")
    l.release("A", "r1")
    assert l.holder("A") is None
    assert not l.heartbeat("A", "r1")
