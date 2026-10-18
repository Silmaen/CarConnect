_LETTERS = "PCBU"


def decode_dtc(b1: int, b2: int) -> str:
    """Deux octets OBD-II -> code défaut (ex. 0x01 0x33 -> P0133)."""
    return f"{_LETTERS[b1 >> 6]}{(b1 >> 4) & 3}{b1 & 0xF:X}{b2:02X}"


def encode_dtc(code: str) -> bytes:
    letter, digit, rest = code[0], int(code[1]), int(code[2:], 16)
    return bytes([(_LETTERS.index(letter) << 6) | (digit << 4) | (rest >> 8), rest & 0xFF])
