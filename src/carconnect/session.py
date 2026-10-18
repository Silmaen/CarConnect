import queue
import threading
from collections.abc import Callable

from carconnect.elm327 import Elm327, Elm327Error, NoDataError
from carconnect.obd import PIDS, ObdClient
from carconnect.transport import Transport

# Lus à chaque cycle ; les autres PIDs supportés le sont un par cycle, en rotation.
POLLED_PIDS = (0x0C, 0x0D, 0x05, 0x11, 0x04, 0x42)


class Session:
    """Une connexion à l'adaptateur : lecture cyclique des PIDs dans un thread dédié.

    Les rappels sont appelés depuis ce thread. Les opérations ponctuelles (DTC, ...)
    passent par `submit` pour ne pas se mélanger aux lectures sur le même canal.
    """

    def __init__(
        self,
        transport: Transport,
        on_ready: Callable[[str], None],
        on_sample: Callable[[dict[str, float]], None],
        on_error: Callable[[str], None],
        on_info: Callable[[dict], None] = lambda info: None,
    ) -> None:
        self._transport = transport
        self._on_ready = on_ready
        self._on_sample = on_sample
        self._on_error = on_error
        self._on_info = on_info
        self._jobs: queue.Queue[Callable[[ObdClient], None]] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="obd-session", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)

    def submit(self, job: Callable[[ObdClient], None]) -> None:
        self._jobs.put(job)

    def _run(self) -> None:
        try:
            self._transport.open()
            elm = Elm327(self._transport)
            version = elm.initialize()
            obd = ObdClient(elm)
            self._on_ready(version)
            supported, info = self._discover(obd)
            self._on_info(info)
            fast = [pid for pid in POLLED_PIDS if pid in supported] or list(POLLED_PIDS)
            slow = [pid for pid in supported if pid not in fast]
            turn = 0
            while not self._stop.is_set():
                self._drain_jobs(obd)
                pids = list(fast)
                if slow:
                    pids.append(slow[turn % len(slow)])
                    turn += 1
                sample: dict[str, float] = {}
                for pid in pids:
                    try:
                        sample[PIDS[pid].key] = obd.read(pid)
                    except NoDataError:
                        pass
                self._on_sample(sample)
                self._stop.wait(0.05)
        except Exception as exc:
            self._on_error(str(exc) or type(exc).__name__)
        finally:
            self._transport.close()

    def _discover(self, obd: ObdClient) -> tuple[list[int], dict]:
        supported = sorted(pid for pid in obd.supported_pids() if pid in PIDS)
        info: dict = {
            "pids": [{"key": PIDS[p].key, "name": PIDS[p].name, "unit": PIDS[p].unit} for p in supported],
            "vin": "",
            "mil": False,
            "dtcCount": 0,
        }
        try:
            info["vin"] = obd.vin()
        except Elm327Error:
            pass
        try:
            status = obd.status()
            info["mil"], info["dtcCount"] = status.mil, status.dtc_count
        except Elm327Error:
            pass
        return supported, info

    def _drain_jobs(self, obd: ObdClient) -> None:
        while True:
            try:
                job = self._jobs.get_nowait()
            except queue.Empty:
                return
            job(obd)
