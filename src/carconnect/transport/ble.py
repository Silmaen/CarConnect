import asyncio
import queue
import threading

from carconnect.transport.base import Transport

_GENERIC_SERVICES = ("00001800", "00001801")  # Generic Access / Generic Attribute


class BleTransport(Transport):
    """Bluetooth Low Energy : la plupart des ELM327 BLE exposent une caractéristique
    "notify" (réception) et une caractéristique "write" (émission), souvent dans le service 0xFFF0.

    bleak est asynchrone : une boucle asyncio tourne dans un thread dédié et on y
    dépose les coroutines, pour garder l'interface synchrone des autres transports.
    """

    CHUNK = 20  # MTU BLE par défaut moins l'en-tête

    def __init__(self, address: str, connect_timeout: float = 15.0) -> None:
        self._address = address
        self._connect_timeout = connect_timeout
        self._rx: queue.Queue[bytes] = queue.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client = None
        self._write_char = None

    def open(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="ble-loop", daemon=True)
        self._thread.start()
        try:
            self._call(self._connect(), self._connect_timeout + 10)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self._loop is None:
            return
        if self._client is not None:
            try:
                self._call(self._client.disconnect(), 5)
            except Exception:
                pass
            self._client = None
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._loop = None
        self._thread = None

    def write(self, data: bytes) -> None:
        self._call(self._write(data), 10)

    def read(self, timeout: float) -> bytes:
        try:
            data = self._rx.get(timeout=timeout)
        except queue.Empty:
            return b""
        while True:
            try:
                data += self._rx.get_nowait()
            except queue.Empty:
                return data

    # -- interne ------------------------------------------------------------

    def _call(self, coro, timeout: float):
        assert self._loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    async def _connect(self) -> None:
        from bleak import BleakClient

        client = BleakClient(self._address, timeout=self._connect_timeout)
        await client.connect()
        self._client = client
        notify, self._write_char = self._pick(client.services)
        await client.start_notify(notify, lambda _char, data: self._rx.put(bytes(data)))

    async def _write(self, data: bytes) -> None:
        assert self._client is not None and self._write_char is not None
        with_response = "write-without-response" not in self._write_char.properties
        for i in range(0, len(data), self.CHUNK):
            await self._client.write_gatt_char(self._write_char, data[i : i + self.CHUNK], response=with_response)

    @staticmethod
    def _pick(services):
        """Choisit la caractéristique de réception et celle d'émission, de préférence dans le même service."""
        for service in services:
            if service.uuid.startswith(_GENERIC_SERVICES):
                continue
            notify = [c for c in service.characteristics if {"notify", "indicate"} & set(c.properties)]
            write = [c for c in service.characteristics if {"write", "write-without-response"} & set(c.properties)]
            if notify and write:
                return notify[0], write[0]
        found = [f"{c.uuid} {c.properties}" for s in services for c in s.characteristics]
        raise RuntimeError("aucune paire notify/write trouvée ; caractéristiques : " + "; ".join(found))
