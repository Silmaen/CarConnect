from carconnect.obd import describe
from carconnect.obd.dtc_db import DESCRIPTIONS


def test_known_codes():
    assert "réponse lente" in describe("P0133")
    assert describe("p0301") == "Raté d'allumage détecté sur le cylindre 1"
    assert "cylindre 12" in describe("P0312")
    assert "moteur" in describe("U0100")


def test_fallback_uses_code_structure():
    assert describe("P0999") == "Groupe motopropulseur — transmission — code générique (SAE)"
    assert describe("P1234") == "Groupe motopropulseur — code propre au constructeur"
    assert describe("B0001").startswith("Carrosserie")
    assert describe("C1234").endswith("propre au constructeur")


def test_all_entries_are_well_formed():
    for code, text in DESCRIPTIONS.items():
        assert len(code) == 5 and code[0] in "PCBU", code
        assert text, code
