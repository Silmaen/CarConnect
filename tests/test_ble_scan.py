import pytest

from carconnect.transport.ble_scan import is_likely


@pytest.mark.parametrize(
    ("name", "uuids", "expected"),
    [
        ("OBDII", [], True),
        ("Vgate iCar Pro", [], True),
        ("IOS-Vlink", [], True),
        (None, ["0000fff0-0000-1000-8000-00805f9b34fb"], True),
        ("JBL Flip 5", ["0000110b-0000-1000-8000-00805f9b34fb"], False),
        (None, [], False),
    ],
)
def test_is_likely(name, uuids, expected):
    assert is_likely(name, uuids) is expected
