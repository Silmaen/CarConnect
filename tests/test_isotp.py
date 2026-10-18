from carconnect.elm327.isotp import split_messages


def test_single_frames_stay_separate():
    assert split_messages(["7F 22 78", "62 F1 90 41"]) == [b"\x7f\x22\x78", b"\x62\xf1\x90\x41"]


def test_multiframe_is_joined_and_trimmed_to_declared_length():
    lines = ["00A", "0: 62 F1 90 56 46 31", "1: 41 42 43 44 AA AA AA"]  # 10 octets utiles, bourrage AA
    assert split_messages(lines) == [bytes.fromhex("62F19056463141424344")]


def test_pending_then_multiframe():
    lines = ["7F 22 78", "008", "0: 62 F1 90 01 02 03", "1: 04 05"]
    assert split_messages(lines) == [b"\x7f\x22\x78", bytes.fromhex("62F190010203" + "0405")]


def test_unreadable_lines_are_ignored():
    assert split_messages(["STOPPED?", "", "41 00 BE"]) == [b"\x41\x00\xbe"]
    assert split_messages([]) == []
