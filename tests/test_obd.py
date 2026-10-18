import pytest

from carconnect.elm327 import Elm327, Elm327Error, NoDataError
from carconnect.obd import ObdClient
from carconnect.transport import SimulatedTransport
from carconnect.transport.simulator import VIN


@pytest.fixture
def elm():
    transport = SimulatedTransport(clock=lambda: 0.0, dtcs=["P0133", "U0100"], pending=["P0301"])
    elm = Elm327(transport, timeout=1)
    elm.initialize()
    return elm


def test_initialize_returns_version():
    assert Elm327(SimulatedTransport(), timeout=1).initialize() == "ELM327 v1.5"


def test_unknown_command(elm):
    with pytest.raises(Elm327Error):
        elm.send("ZZZ")


def test_unsupported_pid(elm):
    with pytest.raises(NoDataError):
        ObdClient(elm).read(0x10 + 0x20)  # 0x30 : connu de la table mais absent du simulateur


def test_read_pids(elm):
    obd = ObdClient(elm)
    # horloge figée à t=0 : wave = 0.5
    assert obd.read(0x0C) == pytest.approx(1925, abs=1)
    assert obd.read(0x05) == 90
    assert obd.read(0x42) == pytest.approx(14.1)
    assert obd.read(0x06) == pytest.approx(1.5625)
    assert obd.read(0x5C) == 85


def test_supported_pids_follows_range_links(elm):
    expected = {0x01, 0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x1F}
    expected |= {0x2F, 0x31, 0x33, 0x42, 0x46, 0x5C}
    assert ObdClient(elm).supported_pids() == expected


def test_status(elm):
    status = ObdClient(elm).status()
    assert status.mil is True
    assert status.dtc_count == 2


def test_vin_multiframe(elm):
    assert ObdClient(elm).vin() == VIN


def test_dtcs_read_and_clear(elm):
    obd = ObdClient(elm)
    assert obd.read_dtcs() == ["P0133", "U0100"]
    assert obd.read_dtcs("pending") == ["P0301"]
    assert obd.read_dtcs("permanent") == []
    obd.clear_dtcs()
    assert obd.read_dtcs() == []
    assert obd.read_dtcs("pending") == []


def test_readiness(elm):
    by_name = {m.name: m.complete for m in ObdClient(elm).readiness()}
    assert by_name["Catalyseur"] is True
    assert by_name["Système EVAP"] is False


def test_freeze_frame(elm):
    frame = ObdClient(elm).freeze_frame()
    assert frame.dtc == "P0133"
    assert frame.values[0x0C] == pytest.approx(2100)
    assert frame.values[0x05] == 85


def test_no_freeze_frame_without_dtc(elm):
    obd = ObdClient(elm)
    obd.clear_dtcs()
    assert obd.freeze_frame() is None
