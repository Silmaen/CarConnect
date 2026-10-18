import pytest

from carconnect.elm327 import Elm327, NoDataError
from carconnect.obd import ObdClient
from carconnect.transport import SimulatedTransport
from carconnect.transport.simulator import VIN
from carconnect.uds import Module, UdsClient, UdsNegativeResponse, module_report, scan_modules


@pytest.fixture
def elm():
    elm = Elm327(SimulatedTransport(clock=lambda: 0.0), timeout=1)
    elm.initialize()
    return elm


def test_scan_finds_modules_and_restores_obd(elm):
    seen = []
    modules = scan_modules(elm, progress=seen.append)
    assert modules == [Module(0x726, 0x72E), Module(0x760, 0x768), Module(0x7E0, 0x7E8)]
    assert 0x7DF not in seen
    assert ObdClient(elm).read(0x0C) > 0  # l'adaptateur est revenu en mode OBD-II


def test_identification_and_dtcs(elm):
    uds = UdsClient(elm)
    uds.select(0x7E0)
    uds.tester_present()
    assert uds.identification() == {"VIN": VIN, "Référence pièce": "CC-ECM-0001", "Version logicielle": "SW 1.2.3"}
    (dtc,) = uds.read_dtcs()
    assert dtc.code == "P0133"
    assert dtc.active and dtc.confirmed


def test_negative_response(elm):
    uds = UdsClient(elm)
    uds.select(0x760)
    with pytest.raises(UdsNegativeResponse) as error:
        uds.read_did(0xF194)
    assert error.value.nrc == 0x31


def test_no_module_at_address(elm):
    uds = UdsClient(elm)
    uds.select(0x7A0)
    with pytest.raises(NoDataError):
        uds.tester_present()


def test_module_report(elm):
    uds = UdsClient(elm)
    uds.select(0x760)
    report = module_report(uds, 0x760)
    assert "0x760 → 0x768" in report
    assert "C0035" in report
    assert "confirmé" in report
