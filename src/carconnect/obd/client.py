from dataclasses import dataclass

from carconnect.elm327 import Elm327, NoDataError
from carconnect.obd.dtc import decode_dtc
from carconnect.obd.pids import PIDS

_DTC_MODES = {"stored": 0x03, "pending": 0x07, "permanent": 0x0A}


@dataclass(frozen=True)
class Status:
    mil: bool  # voyant moteur allumé
    dtc_count: int


def _parse(lines: list[str]) -> list[bytes]:
    frames = []
    for line in lines:
        try:
            frames.append(bytes.fromhex(line))
        except ValueError:
            continue
    return frames


class ObdClient:
    """OBD-II générique (services 01, 03, 04, 07, 09 et 0A), pour véhicules CAN."""

    def __init__(self, elm: Elm327) -> None:
        self._elm = elm

    def _mode01(self, pid: int) -> bytes:
        for frame in _parse(self._elm.send(f"01{pid:02X}")):
            if frame[:2] == bytes([0x41, pid]):
                return frame[2:]
        raise NoDataError(f"01{pid:02X}")

    def read(self, pid: int) -> float:
        """Valeur décodée d'un PID du service 01 (voir `PIDS`)."""
        data = self._mode01(pid)
        return PIDS[pid].decode(data)

    def supported_pids(self) -> set[int]:
        found: set[int] = set()
        base = 0
        while True:
            try:
                mask = int.from_bytes(self._mode01(base)[:4], "big")
            except NoDataError:
                break
            found.update(base + i + 1 for i in range(32) if mask & (1 << (31 - i)))
            if not mask & 1:
                break
            base += 0x20
        return {pid for pid in found if pid % 0x20}

    def status(self) -> Status:
        a = self._mode01(0x01)[0]
        return Status(mil=bool(a & 0x80), dtc_count=a & 0x7F)

    def vin(self) -> str:
        """Numéro de châssis (service 09, PID 02), réponse multi-trame de l'ELM327."""
        data = b""
        for line in self._elm.send("0902"):
            payload = line.split(":", 1)[-1]  # "0: 49 02 ..." -> "49 02 ..."
            try:
                data += bytes.fromhex(payload)
            except ValueError:  # ligne de longueur ("014") ou bruit
                continue
        if data[:2] != b"\x49\x02":
            raise NoDataError("0902")
        return data[3:].decode("ascii", "ignore").strip("\x00 ")[:17]

    def read_dtcs(self, kind: str = "stored") -> list[str]:
        """Codes défaut : `stored` (03), `pending` (07, en attente) ou `permanent` (0A)."""
        mode = _DTC_MODES[kind]
        try:
            lines = self._elm.send(f"{mode:02X}")
        except NoDataError:
            return []
        codes = []
        for frame in _parse(lines):
            if frame[:1] != bytes([0x40 | mode]):
                continue
            payload = frame[1:]
            if len(payload) % 2:  # CAN : un octet de comptage précède les codes
                payload = payload[1:]
            for i in range(0, len(payload), 2):
                if payload[i : i + 2] != b"\x00\x00":
                    codes.append(decode_dtc(payload[i], payload[i + 1]))
        return codes

    def clear_dtcs(self) -> None:
        self._elm.send("04")
