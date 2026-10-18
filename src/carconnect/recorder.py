import csv
import time
from pathlib import Path


class Recorder:
    """Enregistre les mesures dans un fichier CSV (une ligne par lecture, temps en secondes)."""

    def __init__(self, path: Path, columns: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._file = path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, ["time", *columns], extrasaction="ignore")
        self._writer.writeheader()
        self._t0 = time.monotonic()

    def write(self, values: dict[str, float]) -> None:
        self._writer.writerow({"time": round(time.monotonic() - self._t0, 3), **values})

    def close(self) -> None:
        self._file.close()
