import threading
import time
from pathlib import Path

from carconnect.transport.base import Transport


class TraceTransport(Transport):
    """Enveloppe un transport et journalise chaque échange dans un fichier (`>>` envoyé, `<<` reçu)."""

    def __init__(self, inner: Transport, path: Path) -> None:
        self._inner = inner
        self.path = path
        self._file = None
        self._lock = threading.Lock()
        self._t0 = time.monotonic()

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", buffering=1)
        self._t0 = time.monotonic()
        self._log("--", "ouverture")
        try:
            self._inner.open()
        except BaseException as exc:
            self._log("!!", f"ouverture impossible : {exc!r}")
            raise

    def close(self) -> None:
        self._inner.close()
        self._log("--", "fermeture")
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None

    def write(self, data: bytes) -> None:
        self._log(">>", repr(data))
        try:
            self._inner.write(data)
        except BaseException as exc:
            self._log("!!", f"écriture impossible : {exc!r}")
            raise

    def read(self, timeout: float) -> bytes:
        data = self._inner.read(timeout)
        if data:
            self._log("<<", repr(data))
        return data

    def note(self, text: str) -> None:
        """Ajoute une remarque au journal (par exemple l'erreur qui a fermé la session)."""
        self._log("!!", text)

    def _log(self, tag: str, text: str) -> None:
        with self._lock:
            if self._file is not None:
                self._file.write(f"{time.monotonic() - self._t0:9.3f} {tag} {text}\n")
