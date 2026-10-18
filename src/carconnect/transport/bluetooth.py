import socket

from carconnect.transport.base import Transport


class BluetoothTransport(Transport):
    """Bluetooth classique (RFCOMM / SPP). Les adaptateurs BLE nécessiteront un autre transport."""

    def __init__(self, address: str, channel: int = 1) -> None:
        self._address = address
        self._channel = channel
        self._sock: socket.socket | None = None

    def open(self) -> None:
        sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        sock.settimeout(10)
        sock.connect((self._address, self._channel))
        self._sock = sock

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def write(self, data: bytes) -> None:
        assert self._sock is not None
        self._sock.sendall(data)

    def read(self, timeout: float) -> bytes:
        assert self._sock is not None
        self._sock.settimeout(timeout)
        try:
            return self._sock.recv(1024)
        except TimeoutError:
            return b""
