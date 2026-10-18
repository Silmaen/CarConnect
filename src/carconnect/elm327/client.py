import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # import de typage seulement : transport -> simulator -> obd -> elm327 est circulaire
    from carconnect.transport.base import Transport


class Elm327Error(Exception):
    pass


class NoDataError(Elm327Error):
    """Le véhicule n'a pas répondu à la requête (PID non supporté, par exemple)."""


_ERRORS = (
    "UNABLE TO CONNECT",
    "CAN ERROR",
    "BUS BUSY",
    "BUS ERROR",
    "BUFFER FULL",
    "DATA ERROR",
    "FB ERROR",
    "STOPPED",
    "ACT ALERT",
    "LP ALERT",
)
_NOISE = ("SEARCHING", "BUS INIT")


class Elm327:
    """Dialogue AT avec un adaptateur ELM327."""

    def __init__(self, transport: "Transport", timeout: float = 10.0) -> None:
        self._transport = transport
        self._timeout = timeout

    def initialize(self) -> str:
        """Réinitialise l'adaptateur et renvoie sa version."""
        version = self.send("ATZ")[-1]
        for cmd in ("ATE0", "ATL0", "ATS0", "ATH0", "ATSP0"):
            self.send(cmd)
        return version

    def voltage(self) -> str:
        return self.send("ATRV")[-1]

    def send(self, command: str) -> list[str]:
        """Envoie une commande et renvoie les lignes de réponse, sans écho ni bruit."""
        self._transport.write(command.encode("ascii") + b"\r")
        lines = []
        for line in self._read_until_prompt().replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or line.upper() == command.upper() or line.startswith(_NOISE):
                continue
            lines.append(line)
        for line in lines:
            if line == "?":
                raise Elm327Error(f"commande inconnue : {command}")
            if line == "NO DATA":
                raise NoDataError(command)
            if line.startswith(_ERRORS):
                raise Elm327Error(line)
        return lines

    def _read_until_prompt(self) -> str:
        deadline = time.monotonic() + self._timeout
        buffer = b""
        while b">" not in buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Elm327Error("délai dépassé (pas de réponse de l'adaptateur)")
            buffer += self._transport.read(min(0.2, remaining))
        return buffer.decode("ascii", "replace").replace(">", "")
