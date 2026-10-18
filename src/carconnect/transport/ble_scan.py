import asyncio
import re
from dataclasses import dataclass

_NAME = re.compile(r"obd|elm327|vgate|v-?link|icar|viecar|konnwei|ob2", re.IGNORECASE)
# Services GATT courants des ELM327 BLE
_SERVICES = ("0000fff0", "0000ffe0", "000018f0", "e7810a71")


@dataclass(frozen=True)
class BleDevice:
    name: str
    address: str
    rssi: int
    likely: bool  # ressemble à un adaptateur OBD


def is_likely(name: str | None, service_uuids: list[str]) -> bool:
    if name and _NAME.search(name):
        return True
    return any(uuid.lower().startswith(_SERVICES) for uuid in service_uuids)


def scan(timeout: float = 5.0) -> list[BleDevice]:
    """Appareils BLE alentour, adaptateurs probables d'abord, puis par signal décroissant."""
    return asyncio.run(_scan(timeout))


async def _scan(timeout: float) -> list[BleDevice]:
    from bleak import BleakScanner

    found = await BleakScanner.discover(timeout=timeout, return_adv=True)
    devices = []
    for device, adv in found.values():
        name = adv.local_name or device.name
        devices.append(
            BleDevice(
                name=name or "(sans nom)",
                address=device.address,
                rssi=adv.rssi,
                likely=is_likely(name, adv.service_uuids),
            )
        )
    return sorted(devices, key=lambda d: (not d.likely, -d.rssi))
