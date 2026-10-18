from abc import ABC, abstractmethod


class Transport(ABC):
    """Canal d'octets vers l'adaptateur."""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def write(self, data: bytes) -> None: ...

    @abstractmethod
    def read(self, timeout: float) -> bytes:
        """Renvoie les octets disponibles, ou b"" si rien n'arrive avant `timeout` secondes."""
