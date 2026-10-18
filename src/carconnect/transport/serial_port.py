from carconnect.transport.base import Transport


class SerialTransport(Transport):
    """Port série réel ou virtuel (/dev/rfcomm0, COMx, ...)."""

    def __init__(self, port: str, baudrate: int = 38400) -> None:
        self._port = port
        self._baudrate = baudrate
        self._ser = None

    def open(self) -> None:
        import serial

        self._ser = serial.Serial(self._port, self._baudrate, timeout=1)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def write(self, data: bytes) -> None:
        assert self._ser is not None
        self._ser.write(data)

    def read(self, timeout: float) -> bytes:
        assert self._ser is not None
        self._ser.timeout = timeout
        data = self._ser.read(1)
        if data:
            data += self._ser.read(self._ser.in_waiting)
        return data
