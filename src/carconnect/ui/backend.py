import threading

from PySide6.QtCore import Property, QObject, Signal, Slot

from carconnect.session import Session
from carconnect.transport import BleTransport, SimulatedTransport, Transport
from carconnect.transport.ble_scan import scan

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
    devicesFound = Signal()  # la liste doit être montrée à l'utilisateur

    # Signaux internes : émis depuis un thread de travail, traités dans le thread Qt.
    _ready = Signal(str)
    _sampled = Signal(object)
    _info = Signal(object)
    _failed = Signal(str)
    _dtcsRead = Signal(str, object)
    _scanned = Signal(object, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._values = dict(_ZERO)
        self._status = "Déconnecté"
        self._connected = False
        self._dtcs: list[str] = []
        self._dtc_info = "Aucune lecture"
        self._vehicle_info: dict = {}
        self._scanning = False
        self._auto = False
        self._devices: list[dict] = []
        self._session: Session | None = None
        self._ready.connect(self._on_ready)
        self._sampled.connect(self._on_sampled)
        self._info.connect(self._on_info)
        self._failed.connect(self._on_failed)
        self._dtcsRead.connect(self._on_dtcs)
        self._scanned.connect(self._on_scanned)

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
        if self._session:
            self._session.submit(lambda obd: self._dtcsRead.emit(kind, obd.read_dtcs(kind)))

    @Slot()
    def clearDtcs(self) -> None:
        if self._session:

            def job(obd) -> None:
                obd.clear_dtcs()
                self._dtcsRead.emit("stored", obd.read_dtcs("stored"))

            self._session.submit(job)

    def shutdown(self) -> None:
        self._stop_session()

    # -- interne ------------------------------------------------------------

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
        if self._session:
            self._session.stop()
            self._session = None
        self._values = dict(_ZERO)
        self.valuesChanged.emit()
        self._vehicle_info = {}
        self.infoChanged.emit()
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

    def _on_failed(self, message: str) -> None:
        self._stop_session()
        self._set_status(f"Erreur : {message}")

    def _on_dtcs(self, kind: str, codes: list) -> None:
        self._dtcs = codes
        count = f"{len(codes)} code(s)" if codes else "aucun code"
        self._dtc_info = f"{_KIND_LABELS[kind]} — {count}"
        self.dtcsChanged.emit()
