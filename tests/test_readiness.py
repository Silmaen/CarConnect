from carconnect.obd.readiness import Monitor, decode_readiness


def test_spark_ignition():
    # B : 3 moniteurs continus supportés et terminés ; C : catalyseur, EVAP, sondes O2, réchauffeur, EGR ; D : EVAP non prêt
    monitors = decode_readiness(bytes([0x82, 0x07, 0xE5, 0x04]))
    by_name = {m.name: m.complete for m in monitors}
    assert len(monitors) == 8
    assert by_name["Ratés d'allumage"] is True
    assert by_name["Catalyseur"] is True
    assert by_name["Système EVAP"] is False


def test_continuous_monitor_not_complete():
    monitors = decode_readiness(bytes([0x00, 0x11, 0x00, 0x00]))  # ratés supportés et incomplets
    assert monitors == [Monitor("Ratés d'allumage", False)]


def test_compression_ignition_uses_diesel_names():
    monitors = decode_readiness(bytes([0x00, 0x08, 0x40, 0x40]))  # filtre à particules supporté et incomplet
    assert monitors == [Monitor("Filtre à particules", False)]
