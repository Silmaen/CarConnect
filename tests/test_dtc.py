import pytest

from carconnect.obd import decode_dtc, encode_dtc


@pytest.mark.parametrize(
    ("raw", "code"),
    [((0x01, 0x33), "P0133"), ((0x41, 0x00), "C0100"), ((0x81, 0x23), "B0123"), ((0xC1, 0x23), "U0123"), ((0x34, 0x56), "P3456")],
)
def test_decode_encode_roundtrip(raw, code):
    assert decode_dtc(*raw) == code
    assert encode_dtc(code) == bytes(raw)
