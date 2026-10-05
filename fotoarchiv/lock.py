"""Zámky otevřených akcí v paměti serveru.

Server běží jako jediný proces, takže zámek stačí držet ve slovníku.
Čas je monotónní čas serveru; opuštěnost (bez heartbeatu déle než
`timeout`) se vyhodnocuje líně při každém dotazu. Jedna relace prohlížeče
drží nejvýš jeden zámek.
"""

import threading
import time
from datetime import datetime

TIMEOUT = 5 * 60


class Locks:
    def __init__(self, timeout=TIMEOUT, clock=time.monotonic):
        self.timeout = timeout
        self.clock = clock
        self._locks = {}  # akce → {jmeno, relace, ziskan, heartbeat}
        self._mutex = threading.Lock()

    def _live(self, akce):
        """Platný zámek akce, nebo None (opuštěný se zahodí)."""
        lock = self._locks.get(akce)
        if lock and self.clock() - lock["heartbeat"] > self.timeout:
            del self._locks[akce]
            return None
        return lock

    def _info(self, lock):
        return {"jmeno": lock["jmeno"], "ziskan": lock["ziskan"],
                "heartbeat_pred_s": round(self.clock() - lock["heartbeat"])}

    def acquire(self, akce, relace, jmeno):
        """Vrátí (True, zámek), nebo (False, držitel) u cizího zámku.

        Získání uvolní zámek, který relace drží na jiné akci.
        """
        with self._mutex:
            lock = self._live(akce)
            if lock and lock["relace"] != relace:
                return False, self._info(lock)
            for other in [a for a, l in self._locks.items()
                          if l["relace"] == relace and a != akce]:
                del self._locks[other]
            now = self.clock()
            if lock is None:
                lock = self._locks[akce] = {
                    "relace": relace,
                    "ziskan": datetime.now().isoformat(timespec="seconds")}
            lock["jmeno"] = jmeno
            lock["heartbeat"] = now
            return True, self._info(lock)

    def heartbeat(self, akce, relace):
        """Obnoví zámek; False, když ho relace už nedrží."""
        with self._mutex:
            lock = self._live(akce)
            if not lock or lock["relace"] != relace:
                return False
            lock["heartbeat"] = self.clock()
            return True

    def release(self, akce, relace):
        with self._mutex:
            lock = self._locks.get(akce)
            if lock and lock["relace"] == relace:
                del self._locks[akce]

    def holds(self, akce, relace):
        with self._mutex:
            lock = self._live(akce)
            return bool(lock and relace and lock["relace"] == relace)

    def holder(self, akce):
        """Informace o platném zámku akce, nebo None."""
        with self._mutex:
            lock = self._live(akce)
            return self._info(lock) if lock else None
