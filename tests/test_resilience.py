import threading

import pytest

from carconnect.elm327 import Elm327, Elm327Error, Elm327Timeout
from carconnect.obd import ObdClient
from carconnect.session import Session
from carconnect.transport import SimulatedTransport, TraceTransport
from carconnect.uds import scan_modules


class FlakyBus(SimulatedTransport):
    """Simulateur dont le bus renvoie des erreurs : sur les premières lectures du régime, ou sur tout le UDS."""

    def __init__(self, rpm_errors: int = 0, uds_errors: bool = False) -> None:
        super().__init__()
        self.rpm_errors = rpm_errors
        self.uds_errors = uds_errors

    def _obd(self, cmd: str) -> str:
        if cmd == "010C" and self.rpm_errors > 0:
            self.rpm_errors -= 1
            return "CAN ERROR"
        if cmd == "3E00" and self.uds_errors:
            return "BUFFER FULL"
        return super()._obd(cmd)


def run_session(transport, wanted_samples=3):
    done = threading.Event()
    samples, errors = [], []

    def on_sample(sample):
        samples.append(sample)
        if len(samples) >= wanted_samples:
            done.set()

    def on_error(message):
        errors.append(message)
        done.set()

    session = Session(transport, lambda v: None, on_sample, on_error)
    session.start()
    assert done.wait(5)
    session.stop()
    return samples, errors


def test_session_survives_transient_bus_errors():
    samples, errors = run_session(FlakyBus(rpm_errors=2))
    assert not errors
    assert len(samples) == 3


def test_session_gives_up_after_repeated_bus_errors():
    samples, errors = run_session(FlakyBus(rpm_errors=100))
    assert errors == ["CAN ERROR"]
    assert not samples


def test_scan_stops_on_repeated_errors_and_restores_obd():
    elm = Elm327(FlakyBus(uds_errors=True), timeout=1)
    elm.initialize()
    with pytest.raises(Elm327Error, match="recherche interrompue"):
        scan_modules(elm)
    assert ObdClient(elm).read(0x0C) > 0  # l'adresse d'envoi a été rétablie malgré l'échec


def test_scan_needs_11_bit_can():
    transport = SimulatedTransport()
    elm = Elm327(transport, timeout=1)
    elm.initialize()
    elm.protocol = lambda: "A7"  # CAN 29 bits
    with pytest.raises(Elm327Error, match="CAN 11 bits requis"):
        scan_modules(elm)


def test_trace_transport_logs_exchanges(tmp_path):
    path = tmp_path / "logs" / "trace.log"
    transport = TraceTransport(SimulatedTransport(clock=lambda: 0.0), path)
    transport.open()
    elm = Elm327(transport, timeout=1)
    elm.initialize()
    elm.send("010C")
    transport.close()

    text = path.read_text(encoding="utf-8")
    assert ">> b'010C\\r'" in text
    assert "<< b'41 0C" in text
    assert text.rstrip().endswith("fermeture")


class DeafAtFirst(SimulatedTransport):
    """Adaptateur qui ignore les premières écritures, comme juste après une connexion BLE."""

    def __init__(self, ignored_writes: int) -> None:
        super().__init__()
        self.ignored_writes = ignored_writes

    def write(self, data: bytes) -> None:
        if self.ignored_writes > 0:
            self.ignored_writes -= 1
            return
        super().write(data)


def test_initialize_retries_when_the_adapter_ignores_the_first_command():
    elm = Elm327(DeafAtFirst(ignored_writes=2), timeout=0.3)
    assert elm.initialize() == "ELM327 v1.5"


def test_initialize_gives_up_with_a_helpful_message():
    elm = Elm327(DeafAtFirst(ignored_writes=100), timeout=0.3)
    with pytest.raises(Elm327Timeout, match="rebrancher"):
        elm.initialize()
