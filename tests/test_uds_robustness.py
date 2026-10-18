import pytest

from carconnect.elm327 import Elm327, Elm327Error
from carconnect.transport import SimulatedTransport
from carconnect.transport.simulator import VIN
from carconnect.uds import DEFAULT_STATUS_MASK, UdsClient, UdsNegativeResponse, module_report


def make(**attrs):
    transport = SimulatedTransport(clock=lambda: 0.0)
    for name, value in attrs.items():
        setattr(transport, name, value)
    elm = Elm327(transport, timeout=1)
    elm.initialize()
    return elm, UdsClient(elm)


def test_pending_response_is_skipped_when_the_real_answer_follows():
    _, uds = make(uds_pending_first=True)
    uds.select(0x7E0)
    assert uds.read_did(0xF190).decode() == VIN  # multi-trame derrière un "7F 22 78"
    assert [dtc.code for dtc in uds.read_dtcs()] == ["P0133"]


def test_negative_response_still_reported_after_a_pending_one():
    _, uds = make(uds_pending_first=True)
    uds.select(0x760)
    with pytest.raises(UdsNegativeResponse) as error:
        uds.read_did(0xF194)  # inconnu de ce calculateur
    assert error.value.nrc == 0x31


def test_unexpected_response_is_an_error_not_a_crash():
    elm, uds = make()
    uds.select(0x7E0)
    elm.send = lambda command: ["41 0C 1A F8"]  # réponse d'un autre service
    with pytest.raises(Elm327Error, match="réponse inattendue"):
        uds.request(0x22, b"\xf1\x90")


def test_report_describes_failures_instead_of_raising():
    elm, uds = make()
    uds.select(0x7E0)
    elm.send = lambda command: ["41 0C 1A F8"]
    report = module_report(uds, 0x7E0)
    assert "Identification : non disponible" in report
    assert "lecture impossible" in report


def test_truncated_answer_is_explained_with_raw_frames():
    elm, uds = make(uds_overflow_mask=DEFAULT_STATUS_MASK)
    uds.select(0x7E0)
    report = module_report(uds, 0x7E0)
    assert "lecture impossible (réponse inattendue : AF 59 02 FF 03 28 12)" in report
    assert "Trames brutes : 7E8 11 9F 59 02 FF 03 28 12" in report  # en-têtes activés pour l'analyse
    assert "annonce 415 octets" in report
    assert elm.send("ATH0") == ["OK"]  # les en-têtes ont été désactivés à nouveau


def test_default_mask_avoids_the_oversized_answer():
    _, uds = make(uds_overflow_mask=0xFF)  # le masque large dépasse ce que l'adaptateur transmet
    uds.select(0x7E0)
    with pytest.raises(Elm327Error, match="réponse inattendue"):
        uds.read_dtcs(0xFF)
    assert [dtc.code for dtc in uds.read_dtcs()] == ["P0133"]  # les codes "test pas passé" sont filtrés
    # masque 0x50 : bits "test non terminé", que le masque par défaut ignore volontairement
    assert [dtc.code for dtc in uds.read_dtcs(0x50)] == ["P0420"]
