import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QEventLoop  # noqa: E402

from carconnect.ui.backend import Backend  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QCoreApplication.instance() or QCoreApplication([])


def wait_for(app, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 20)
    return bool(predicate())


def test_full_flow_with_simulator(app, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    backend = Backend()
    backend.connectSimulator()
    try:
        assert wait_for(app, lambda: backend.connected and backend.info.get("vin"))
        assert backend.info["mil"] is True
        assert wait_for(app, lambda: backend.values["rpm"] > 0)

        backend.startRecording()
        assert backend.recording
        backend.readReadiness()
        backend.readFreezeFrame()
        backend.readDtcs("stored")
        assert wait_for(app, lambda: backend.readiness and backend.freeze and backend.dtcs)
        assert backend.dtcs[0]["code"] == "P0133"
        assert "lente" in backend.dtcs[0]["text"]
        assert backend.freeze["dtc"] == "P0133"

        backend.scanModules()
        assert wait_for(app, lambda: len(backend.modules) == 3)
        backend.readModule(0x760)
        assert wait_for(app, lambda: "C0035" in backend.moduleReport)

        # la lecture OBD-II continue après les requêtes UDS
        rpm_before = backend.values["rpm"]
        assert wait_for(app, lambda: backend.values["rpm"] != rpm_before)

        backend.clearDtcs()
        assert wait_for(app, lambda: backend.dtcs == [])
        backend.stopRecording()
        (csv_file,) = (tmp_path / "CarConnect").glob("mesures_*.csv")
        assert len(csv_file.read_text().splitlines()) > 1
    finally:
        backend.shutdown()
    assert not backend.connected
