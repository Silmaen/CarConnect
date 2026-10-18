import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # import de typage seulement : transport -> simulator -> obd -> elm327 est circulaire
    from carconnect.transport.base import Transport


class Elm327Error(Exception):
    pass


class NoDataError(Elm327Error):
    """Le véhicule n'a pas répondu à la requête (PID non supporté, par exemple)."""


class Elm327Timeout(Elm327Error):
    """L'adaptateur lui-même n'a pas répondu : liaison probablement perdue."""


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
_OBD_SETUP = ("ATE0", "ATL0", "ATS0", "ATH0", "ATSP0")
_DEFAULT_REQUEST = ("ATSH7DF", "ATST32")  # adresse fonctionnelle OBD-II (CAN 11 bits) et délai par défaut
_ATZ_ATTEMPTS = 3
_ATZ_TIMEOUT = 4.0  # secondes par essai : ATZ prend en général 1 à 2 s


class Elm327:
    """Dialogue AT avec un adaptateur ELM327."""

    def __init__(self, transport: "Transport", timeout: float = 10.0) -> None:
        self._transport = transport
        self._timeout = timeout

    def initialize(self) -> str:
        """Réinitialise l'adaptateur et renvoie sa version.

        Juste après la connexion, un adaptateur peut ignorer la première commande : on réessaie jusqu'à
        `_ATZ_ATTEMPTS` fois, en vidant ce qui traîne et en envoyant un retour chariot pour le "réveiller".
        """
        for attempt in range(1, _ATZ_ATTEMPTS + 1):
            try:
                version = self.send("ATZ", timeout=min(self._timeout, _ATZ_TIMEOUT))[-1]
                break
            except Elm327Timeout:
                if attempt == _ATZ_ATTEMPTS:
                    raise Elm327Timeout(
                        "l'adaptateur ne répond pas à ATZ : le débrancher puis le rebrancher, et vérifier "
                        "qu'aucune autre application n'y est connectée"
                    ) from None
                self._drain()
                self._transport.write(b"\r")
        for cmd in _OBD_SETUP:
            self.send(cmd)
        return version

    def _drain(self) -> None:
        """Jette ce que l'adaptateur envoie encore, pour ne pas décaler les réponses suivantes."""
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and self._transport.read(0.2):
            pass

    def protocol(self) -> str:
        """Protocole détecté, au format ELM327 ("A6" : ISO 15765-4, CAN 11 bits, 500 kbit/s)."""
        return self.send("ATDPN")[-1]

    def restore_obd(self) -> None:
        """Remet l'adaptateur en configuration OBD-II après des requêtes à un calculateur précis.

        On ne remet d'abord que ce qui a été changé (adresse d'envoi et délai), pour ne pas relancer la
        détection du protocole. Si cela échoue, on reconfigure complètement.
        """
        try:
            for cmd in _DEFAULT_REQUEST:
                self.send(cmd)
        except Elm327Timeout:
            raise
        except Elm327Error:
            for cmd in ("ATD", *_OBD_SETUP):
                self.send(cmd)

    def voltage(self) -> str:
        return self.send("ATRV")[-1]

    def send(self, command: str, timeout: float | None = None) -> list[str]:
        """Envoie une commande et renvoie les lignes de réponse, sans écho ni bruit."""
        self._transport.write(command.encode("ascii") + b"\r")
        lines = []
        for line in self._read_until_prompt(timeout or self._timeout).replace("\r", "\n").split("\n"):
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

    def _read_until_prompt(self, timeout: float) -> str:
        deadline = time.monotonic() + timeout
        buffer = b""
        while b">" not in buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise Elm327Timeout("délai dépassé (pas de réponse de l'adaptateur)")
            buffer += self._transport.read(min(0.2, remaining))
        return buffer.decode("ascii", "replace").replace(">", "")
