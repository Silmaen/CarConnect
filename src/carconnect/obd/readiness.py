from dataclasses import dataclass

_CONTINUOUS = ("Ratés d'allumage", "Circuit de carburant", "Composants")
_SPARK = (
    "Catalyseur",
    "Catalyseur chauffé",
    "Système EVAP",
    "Air secondaire",
    "Climatisation (réfrigérant)",
    "Sondes O2",
    "Réchauffeur des sondes O2",
    "EGR / VVT",
)
_DIESEL = (
    "Catalyseur NMHC",
    "Catalyseur NOx / SCR",
    None,
    "Pression de suralimentation",
    None,
    "Sonde de gaz d'échappement",
    "Filtre à particules",
    "EGR / VVT",
)


@dataclass(frozen=True)
class Monitor:
    name: str
    complete: bool


def decode_readiness(data: bytes) -> list[Monitor]:
    """Octets A B C D du PID 01 -> moniteurs supportés et leur état (SAE J1979)."""
    _, b, c, d = data[:4]
    monitors = [Monitor(name, not b & (1 << (4 + i))) for i, name in enumerate(_CONTINUOUS) if b & (1 << i)]
    names = _DIESEL if b & 0x08 else _SPARK
    monitors += [Monitor(name, not d & (1 << i)) for i, name in enumerate(names) if name and c & (1 << i)]
    return monitors
