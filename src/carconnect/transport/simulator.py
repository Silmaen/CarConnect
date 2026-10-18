import math
import re
import time
from collections.abc import Callable, Iterable

from carconnect.obd.dtc import encode_dtc
from carconnect.transport.base import Transport

VIN = "VF1CCONNECT000001"


def _hex(data: bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def _word(value: float) -> bytes:
    return max(0, min(0xFFFF, int(value))).to_bytes(2, "big")


def _byte(value: float) -> bytes:
    return bytes([max(0, min(0xFF, int(value)))])


class SimulatedTransport(Transport):
    """Faux ELM327 branché sur un véhicule fictif, pour développer sans voiture."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        dtcs: Iterable[str] = ("P0133",),
        pending: Iterable[str] = ("P0301",),
    ) -> None:
        self._clock = clock
        self._t0 = clock()
        self.dtcs = list(dtcs)
        self.pending = list(pending)
        self._echo = True
        self._out = b""

    def open(self) -> None:
        self._t0 = self._clock()

    def close(self) -> None:
        pass

    def write(self, data: bytes) -> None:
        for raw in data.decode("ascii", "ignore").split("\r"):
            if raw.strip():
                self._out += self._answer(raw).encode("ascii")

    def read(self, timeout: float) -> bytes:
        out, self._out = self._out, b""
        return out

    # -- ELM327 -------------------------------------------------------------

    def _answer(self, raw: str) -> str:
        cmd = raw.replace(" ", "").upper()
        echo = f"{raw.strip()}\r" if self._echo else ""
        if cmd.startswith("AT"):
            body = self._at(cmd[2:])
        elif re.fullmatch(r"[0-9A-F]+", cmd):
            body = self._obd(cmd)
        else:
            body = "?"
        return f"{echo}{body}\r\r>"

    def _at(self, cmd: str) -> str:
        exact = {"Z": "ELM327 v1.5", "I": "ELM327 v1.5", "DP": "AUTO, ISO 15765-4 (CAN 11/500)", "RV": "14.1V"}
        if cmd in exact:
            if cmd == "Z":
                self._echo = True
            return exact[cmd]
        if cmd in ("E0", "E1"):
            self._echo = cmd == "E1"
            return "OK"
        if cmd.startswith(("L", "S", "H", "SP", "AT", "D")):
            return "OK"
        return "?"

    # -- OBD-II -------------------------------------------------------------

    def _pid_values(self) -> dict[int, bytes]:
        t = self._clock() - self._t0
        wave = 0.5 + 0.5 * math.sin(t / 3)
        mil = 0x80 if self.dtcs else 0
        return {
            0x01: bytes([mil | len(self.dtcs), 0x07, 0xE5, 0x00]),
            0x04: _byte((20 + 40 * wave) * 255 / 100),
            0x05: _byte(90 + 40),
            0x06: _byte(128 + 2),
            0x07: _byte(128 - 1),
            0x0B: _byte(30 + 20 * wave),
            0x0C: _word((850 + 2150 * wave) * 4),
            0x0D: _byte(70 * (0.5 + 0.5 * math.sin(t / 5))),
            0x0E: _byte((8 + 6 * wave + 64) * 2),
            0x0F: _byte(25 + 40),
            0x10: _word((3 + 12 * wave) * 100),
            0x11: _byte((12 + 30 * wave) * 255 / 100),
            0x1F: _word(t),
            0x2F: _byte(60 * 255 / 100),
            0x31: _word(1234),
            0x33: _byte(101),
            0x42: _word(14100),
            0x46: _byte(18 + 40),
            0x5C: _byte(85 + 40),
        }

    def _support_mask(self, base: int, supported: Iterable[int]) -> bytes:
        mask = 0
        for pid in supported:
            if base < pid <= base + 0x20:
                mask |= 1 << (32 - (pid - base))
        if any(pid > base + 0x20 for pid in supported):
            mask |= 1
        return mask.to_bytes(4, "big")

    def _dtc_frame(self, mode: int, codes: list[str]) -> str:
        pairs = b"".join(encode_dtc(code) for code in codes)
        return _hex((bytes([0x40 | mode, len(codes)]) + pairs).ljust(8, b"\x00"))

    def _vin_frames(self) -> str:
        data = bytes([0x49, 0x02, 0x01]) + VIN.encode("ascii")
        chunks = [data[:6]] + [data[i : i + 7] for i in range(6, len(data), 7)]
        lines = [f"{len(data):03X}"] + [f"{n}: {_hex(chunk)}" for n, chunk in enumerate(chunks)]
        return "\r".join(lines)

    def _obd(self, cmd: str) -> str:
        if len(cmd) == 4 and cmd.startswith("01"):
            pid = int(cmd[2:], 16)
            values = self._pid_values()
            if pid % 0x20 == 0:
                mask = self._support_mask(pid, values)
                if mask != bytes(4):
                    return _hex(bytes([0x41, pid]) + mask)
            elif pid in values:
                return _hex(bytes([0x41, pid]) + values[pid])
        elif cmd == "03":
            return self._dtc_frame(0x03, self.dtcs)
        elif cmd == "07":
            return self._dtc_frame(0x07, self.pending)
        elif cmd == "0A":
            return self._dtc_frame(0x0A, [])
        elif cmd == "04":
            self.dtcs.clear()
            self.pending.clear()
            return "44"
        elif cmd == "0902":
            return self._vin_frames()
        return "NO DATA"
