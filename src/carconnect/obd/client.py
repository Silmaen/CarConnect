from dataclasses import dataclass

from carconnect.elm327 import Elm327, NoDataError
from carconnect.elm327.isotp import split_messages
from carconnect.obd.dtc import decode_dtc
from carconnect.obd.pids import PIDS
from carconnect.obd.readiness import Monitor, decode_readiness

_DTC_MODES = {"stored": 0x03, "pending": 0x07, "permanent": 0x0A}


@dataclass(frozen=True)
class Status:
    mil: bool  # voyant moteur allumé
    dtc_count: int


@dataclass(frozen=True)
class FreezeFrame:
    dtc: str | None  # code qui a déclenché l'enregistrement
    values: dict[int, float]  # PID -> valeur décodée


def _parse(lines: list[str]) -> list[bytes]:
    frames = []
    for line in lines:
        try:
            frames.append(bytes.fromhex(line))
        except ValueError:
            continue
    return frames


class ObdClient:
    """OBD-II générique (services 01, 02, 03, 04, 07, 09 et 0A), pour véhicules CAN."""

    def __init__(self, elm: Elm327) -> None:
        self.elm = elm

    def _read(self, mode: int, pid: int) -> bytes:
        """Données d'un PID du service 01 (temps réel) ou 02 (données figées, trame 0)."""
        suffix, echo = ("00", b"\x00") if mode == 2 else ("", b"")
        prefix = bytes([0x40 | mode, pid]) + echo
        for frame in _parse(self.elm.send(f"{mode:02X}{pid:02X}{suffix}")):
            if frame[: len(prefix)] == prefix:
                return frame[len(prefix) :]
        raise NoDataError(f"{mode:02X}{pid:02X}")

    def _mode01(self, pid: int) -> bytes:
        return self._read(1, pid)

    def read(self, pid: int) -> float:
        """Valeur décodée d'un PID du service 01 (voir `PIDS`)."""
        data = self._mode01(pid)
        return PIDS[pid].decode(data)

    def supported_pids(self, mode: int = 1) -> set[int]:
        found: set[int] = set()
        base = 0
        while True:
            try:
                mask = int.from_bytes(self._read(mode, base)[:4], "big")
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

    def readiness(self) -> list[Monitor]:
        """État des moniteurs de préparation (prêt pour le contrôle technique ou non)."""
        return decode_readiness(self._mode01(0x01))

    def freeze_frame(self) -> FreezeFrame | None:
        """Mesures enregistrées au moment du premier défaut, ou None s'il n'y en a pas."""
        try:
            raw = self._read(2, 0x02)
        except NoDataError:
            return None
        dtc = None if raw[:2] == b"\x00\x00" else decode_dtc(raw[0], raw[1])
        values: dict[int, float] = {}
        for pid in sorted(self.supported_pids(2) & PIDS.keys()):
            try:
                values[pid] = PIDS[pid].decode(self._read(2, pid))
            except NoDataError:
                pass
        return FreezeFrame(dtc, values)

    def vin(self) -> str:
        """Numéro de châssis (service 09, PID 02), réponse multi-trame de l'ELM327."""
        for message in split_messages(self.elm.send("0902")):
            if message[:2] == b"\x49\x02":
                return message[3:].decode("ascii", "ignore").strip("\x00 ")[:17]
        raise NoDataError("0902")

    def read_dtcs(self, kind: str = "stored") -> list[str]:
        """Codes défaut : `stored` (03), `pending` (07, en attente) ou `permanent` (0A)."""
        mode = _DTC_MODES[kind]
        try:
            lines = self.elm.send(f"{mode:02X}")
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
        self.elm.send("04")
