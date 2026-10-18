import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from carconnect.elm327 import Elm327Error, Elm327Timeout
from carconnect.obd import PIDS, ObdClient, describe
from carconnect.recorder import Recorder
from carconnect.session import Session
from carconnect.transport import BleTransport, SimulatedTransport, TraceTransport, Transport
from carconnect.transport.ble_scan import scan
from carconnect.uds import UdsClient, module_report, scan_modules

_ZERO = {"rpm": 0.0, "speed": 0.0, "coolant": 0.0, "throttle": 0.0, "load": 0.0, "voltage": 0.0}
_KIND_LABELS = {"stored": "Mémorisés", "pending": "En attente", "permanent": "Permanents"}


class Backend(QObject):
    """Pont entre la session OBD (thread de travail) et l'interface QML."""

    valuesChanged = Signal()
    statusChanged = Signal()
    connectedChanged = Signal()
    dtcsChanged = Signal()
    infoChanged = Signal()
    scanningChanged = Signal()
    devicesChanged = Signal()
    recordingChanged = Signal()
    diagChanged = Signal()  # bilan, données figées, calculateurs
    devicesFound = Signal()  # la liste doit être montrée à l'utilisateur

    # Signaux internes : émis depuis un thread de travail, traités dans le thread Qt.
    _ready = Signal(str)
    _sampled = Signal(object)
    _info = Signal(object)
    _failed = Signal(str)
    _jobFailed = Signal(str)
    _dtcsRead = Signal(str, object)
    _scanned = Signal(object, str)
    _readinessRead = Signal(object)
    _freezeRead = Signal(object)
    _modulesFound = Signal(object)
    _moduleReport = Signal(str)
    _progress = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._values = dict(_ZERO)
        self._status = "Déconnecté"
        self._connected = False
        self._dtcs: list[dict] = []
        self._dtc_info = "Aucune lecture"
        self._vehicle_info: dict = {}
        self._scanning = False
        self._auto = False
        self._devices: list[dict] = []
        self._readiness: list[dict] = []
        self._freeze: dict = {}
        self._modules: list[dict] = []
        self._module_report = ""
        self._scan_status = ""
        self._recorder: Recorder | None = None
        self._session: Session | None = None
        self._ready.connect(self._on_ready)
        self._sampled.connect(self._on_sampled)
        self._info.connect(self._on_info)
        self._failed.connect(self._on_failed)
        self._jobFailed.connect(lambda message: self._set_status(f"Erreur : {message}"))
        self._dtcsRead.connect(self._on_dtcs)
        self._scanned.connect(self._on_scanned)
        self._readinessRead.connect(self._on_readiness)
        self._freezeRead.connect(self._on_freeze)
        self._modulesFound.connect(self._on_modules)
        self._moduleReport.connect(self._on_module_report)
        self._progress.connect(self._on_progress)

    # -- propriétés QML -----------------------------------------------------

    @Property("QVariantMap", notify=valuesChanged)
    def values(self) -> dict:
        return self._values

    @Property("QVariantMap", notify=infoChanged)
    def info(self) -> dict:
        return self._vehicle_info

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._connected

    @Property(bool, notify=scanningChanged)
    def scanning(self) -> bool:
        return self._scanning

    @Property("QVariantList", notify=devicesChanged)
    def devices(self) -> list:
        return self._devices

    @Property("QVariantList", notify=dtcsChanged)
    def dtcs(self) -> list:
        return self._dtcs

    @Property(str, notify=dtcsChanged)
    def dtcInfo(self) -> str:
        return self._dtc_info

    @Property(bool, notify=recordingChanged)
    def recording(self) -> bool:
        return self._recorder is not None

    @Property(str, notify=recordingChanged)
    def recordingPath(self) -> str:
        return str(self._recorder.path) if self._recorder else ""

    @Property("QVariantList", notify=diagChanged)
    def readiness(self) -> list:
        return self._readiness

    @Property("QVariantMap", notify=diagChanged)
    def freeze(self) -> dict:
        return self._freeze

    @Property("QVariantList", notify=diagChanged)
    def modules(self) -> list:
        return self._modules

    @Property(str, notify=diagChanged)
    def moduleReport(self) -> str:
        return self._module_report

    @Property(str, notify=diagChanged)
    def scanStatus(self) -> str:
        return self._scan_status

    # -- actions appelées depuis QML ---------------------------------------

    @Slot()
    def connectSimulator(self) -> None:
        self._start(SimulatedTransport(), "simulateur")

    @Slot(str)
    def connectBluetooth(self, address: str) -> None:
        self._start(BleTransport(address.strip()), address.strip())

    @Slot()
    def autoConnect(self) -> None:
        """Cherche l'adaptateur et s'y connecte s'il n'y en a qu'un seul de probable."""
        self._scan(auto=True)

    @Slot()
    def scan(self) -> None:
        self._scan(auto=False)

    @Slot()
    def disconnectDevice(self) -> None:
        self._stop_session()
        self._set_status("Déconnecté")

    @Slot(str)
    def readDtcs(self, kind: str) -> None:
        self._submit(lambda obd: self._dtcsRead.emit(kind, obd.read_dtcs(kind)))

    @Slot()
    def clearDtcs(self) -> None:
        def job(obd: ObdClient) -> None:
            obd.clear_dtcs()
            self._dtcsRead.emit("stored", obd.read_dtcs("stored"))

        self._submit(job)

    @Slot()
    def readReadiness(self) -> None:
        self._submit(lambda obd: self._readinessRead.emit(obd.readiness()))

    @Slot()
    def readFreezeFrame(self) -> None:
        self._submit(lambda obd: self._freezeRead.emit(obd.freeze_frame()))

    @Slot()
    def scanModules(self) -> None:
        def job(obd: ObdClient) -> None:
            try:
                modules = scan_modules(obd.elm, progress=lambda tx: self._progress.emit(f"Recherche en cours… {tx:#05x}"))
            except Elm327Timeout:
                raise
            except Elm327Error as exc:
                self._progress.emit(f"Recherche impossible : {exc}")
                return
            self._modulesFound.emit(modules)

        self._submit(job)

    @Slot(int)
    def readModule(self, tx: int) -> None:
        def job(obd: ObdClient) -> None:
            try:
                uds = UdsClient(obd.elm)
                uds.select(tx)
                report = module_report(uds, tx)
            except Elm327Timeout:
                raise
            except Elm327Error as exc:  # le rapport doit toujours expliquer ce qui s'est passé
                report = f"Lecture impossible : {exc}"
            finally:
                obd.elm.restore_obd()
            self._moduleReport.emit(report)

        self._submit(job)

    @Slot()
    def startRecording(self) -> None:
        if self._recorder or not self._connected:
            return
        columns = list(_ZERO) + [p["key"] for p in self._vehicle_info.get("pids", []) if p["key"] not in _ZERO]
        path = Path.home() / "CarConnect" / time.strftime("mesures_%Y%m%d_%H%M%S.csv")
        self._recorder = Recorder(path, columns)
        self.recordingChanged.emit()

    @Slot()
    def stopRecording(self) -> None:
        if self._recorder:
            self._recorder.close()
            self._set_status(f"Enregistrement terminé : {self._recorder.path}")
            self._recorder = None
            self.recordingChanged.emit()

    def shutdown(self) -> None:
        self._stop_session()

    # -- interne ------------------------------------------------------------

    def _submit(self, job: Callable[[ObdClient], None]) -> None:
        """Exécute `job` dans le thread de la session ; une erreur n'interrompt pas la connexion."""
        if not self._session:
            return

        def safe(obd: ObdClient) -> None:
            try:
                job(obd)
            except Exception as exc:
                self._jobFailed.emit(str(exc) or type(exc).__name__)

        self._session.submit(safe)

    def _scan(self, auto: bool) -> None:
        if self._scanning or self._connected:
            return
        self._auto = auto
        self._scanning = True
        self.scanningChanged.emit()
        self._set_status("Recherche des appareils Bluetooth…")

        def work() -> None:
            try:
                self._scanned.emit(scan(), "")
            except Exception as exc:
                self._scanned.emit([], str(exc) or type(exc).__name__)

        threading.Thread(target=work, name="ble-scan", daemon=True).start()

    def _on_scanned(self, devices: list, error: str) -> None:
        self._scanning = False
        self.scanningChanged.emit()
        self._devices = [
            {"name": d.name, "address": d.address, "rssi": d.rssi, "likely": d.likely} for d in devices
        ]
        self.devicesChanged.emit()
        if error:
            self._set_status(f"Recherche impossible : {error}")
            return
        likely = [d for d in devices if d.likely]
        if self._auto and len(likely) == 1:
            self.connectBluetooth(likely[0].address)
            return
        self._set_status(f"{len(devices)} appareil(s) trouvé(s), choisis ton adaptateur")
        self.devicesFound.emit()

    def _start(self, transport: Transport, label: str) -> None:
        self._stop_session()
        trace = os.environ.get("CARCONNECT_TRACE")  # journal des échanges, pour comprendre un problème
        if trace:
            # "1" : un fichier daté dans ~/CarConnect/logs ; sinon la valeur est le chemin du fichier à écrire
            default = Path.home() / "CarConnect" / "logs" / time.strftime("trace_%Y%m%d_%H%M%S.log")
            path = default if trace == "1" else Path(trace).expanduser()
            transport = TraceTransport(transport, path)
            label = f"{label} (journal : {path})"
        self._set_status(f"Connexion à {label}…")
        self._session = Session(
            transport,
            on_ready=self._ready.emit,
            on_sample=self._sampled.emit,
            on_error=self._failed.emit,
            on_info=self._info.emit,
        )
        self._session.start()

    def _stop_session(self) -> None:
        self.stopRecording()
        if self._session:
            self._session.stop()
            self._session = None
        self._values = dict(_ZERO)
        self.valuesChanged.emit()
        self._vehicle_info = {}
        self.infoChanged.emit()
        self._readiness, self._freeze, self._modules = [], {}, []
        self._module_report = self._scan_status = ""
        self.diagChanged.emit()
        self._set_connected(False)

    def _set_status(self, text: str) -> None:
        self._status = text
        self.statusChanged.emit()

    def _set_connected(self, connected: bool) -> None:
        if connected != self._connected:
            self._connected = connected
            self.connectedChanged.emit()

    def _on_ready(self, version: str) -> None:
        self._set_connected(True)
        self._set_status(f"Connecté — {version}")

    def _on_info(self, info: dict) -> None:
        self._vehicle_info = info
        self.infoChanged.emit()

    def _on_sampled(self, sample: dict) -> None:
        self._values = {**self._values, **sample}
        self.valuesChanged.emit()
        if self._recorder:
            self._recorder.write(self._values)

    def _on_failed(self, message: str) -> None:
        self._stop_session()
        self._set_status(f"Erreur : {message}")

    def _on_dtcs(self, kind: str, codes: list) -> None:
        self._dtcs = [{"code": code, "text": describe(code)} for code in codes]
        count = f"{len(codes)} code(s)" if codes else "aucun code"
        self._dtc_info = f"{_KIND_LABELS[kind]} — {count}"
        self.dtcsChanged.emit()

    def _on_readiness(self, monitors: list) -> None:
        self._readiness = [{"name": m.name, "complete": m.complete} for m in monitors]
        self.diagChanged.emit()

    def _on_freeze(self, frame: object) -> None:
        if frame is None:
            self._freeze = {"empty": True, "dtc": "", "dtcText": "", "items": []}
        else:
            self._freeze = {
                "empty": False,
                "dtc": frame.dtc or "",
                "dtcText": describe(frame.dtc) if frame.dtc else "",
                "items": [
                    {"name": PIDS[pid].name, "value": round(value, 1), "unit": PIDS[pid].unit}
                    for pid, value in frame.values.items()
                ],
            }
        self.diagChanged.emit()

    def _on_progress(self, text: str) -> None:
        self._scan_status = text
        self.diagChanged.emit()

    def _on_modules(self, modules: list) -> None:
        self._modules = [{"tx": m.tx, "rx": m.rx, "label": f"{m.tx:#05x} → {m.rx:#05x}"} for m in modules]
        self._scan_status = f"{len(modules)} calculateur(s) trouvé(s)"
        self.diagChanged.emit()

    def _on_module_report(self, report: str) -> None:
        self._module_report = report
        self.diagChanged.emit()
