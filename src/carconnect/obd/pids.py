from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Pid:
    code: int
    key: str
    name: str
    unit: str
    decode: Callable[[bytes], float]


def _percent(d: bytes) -> float:
    return d[0] * 100 / 255


def _temperature(d: bytes) -> float:
    return d[0] - 40


def _trim(d: bytes) -> float:
    return (d[0] - 128) * 100 / 128


def _word(d: bytes) -> int:
    return d[0] * 256 + d[1]


# Formules du service 01 (SAE J1979)
PIDS: dict[int, Pid] = {
    p.code: p
    for p in (
        Pid(0x04, "load", "Charge moteur", "%", _percent),
        Pid(0x05, "coolant", "Température liquide de refroidissement", "°C", _temperature),
        Pid(0x06, "stft1", "Correction carburant court terme (banc 1)", "%", _trim),
        Pid(0x07, "ltft1", "Correction carburant long terme (banc 1)", "%", _trim),
        Pid(0x0A, "fuel_pressure", "Pression de carburant", "kPa", lambda d: d[0] * 3),
        Pid(0x0B, "map", "Pression collecteur d'admission", "kPa", lambda d: d[0]),
        Pid(0x0C, "rpm", "Régime moteur", "tr/min", lambda d: _word(d) / 4),
        Pid(0x0D, "speed", "Vitesse", "km/h", lambda d: d[0]),
        Pid(0x0E, "timing", "Avance à l'allumage", "°", lambda d: d[0] / 2 - 64),
        Pid(0x0F, "intake_temp", "Température d'admission", "°C", _temperature),
        Pid(0x10, "maf", "Débit d'air (débitmètre)", "g/s", lambda d: _word(d) / 100),
        Pid(0x11, "throttle", "Position du papillon", "%", _percent),
        Pid(0x1F, "run_time", "Durée depuis le démarrage", "s", _word),
        Pid(0x21, "mil_distance", "Distance voyant moteur allumé", "km", _word),
        Pid(0x23, "rail_pressure", "Pression rampe d'injection", "kPa", lambda d: _word(d) * 10),
        Pid(0x2C, "egr", "Commande EGR", "%", _percent),
        Pid(0x2F, "fuel_level", "Niveau de carburant", "%", _percent),
        Pid(0x30, "warmups", "Cycles de chauffe depuis effacement", "", lambda d: d[0]),
        Pid(0x31, "clear_distance", "Distance depuis effacement des codes", "km", _word),
        Pid(0x33, "baro", "Pression barométrique", "kPa", lambda d: d[0]),
        Pid(0x42, "voltage", "Tension du module", "V", lambda d: _word(d) / 1000),
        Pid(0x43, "abs_load", "Charge absolue", "%", lambda d: _word(d) * 100 / 255),
        Pid(0x45, "rel_throttle", "Position relative du papillon", "%", _percent),
        Pid(0x46, "ambient_temp", "Température extérieure", "°C", _temperature),
        Pid(0x49, "pedal_d", "Position pédale d'accélérateur D", "%", _percent),
        Pid(0x4A, "pedal_e", "Position pédale d'accélérateur E", "%", _percent),
        Pid(0x5C, "oil_temp", "Température d'huile", "°C", _temperature),
        Pid(0x5E, "fuel_rate", "Débit de carburant", "L/h", lambda d: _word(d) / 20),
    )
}
