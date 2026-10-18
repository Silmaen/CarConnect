import csv

from carconnect.recorder import Recorder


def test_recorder_writes_header_and_rows(tmp_path):
    recorder = Recorder(tmp_path / "sub" / "mesures.csv", ["rpm", "speed", "coolant"])
    recorder.write({"rpm": 900.0, "speed": 0.0})  # colonne absente -> vide
    recorder.write({"rpm": 1500.0, "speed": 12.0, "coolant": 90.0, "inconnue": 1})  # colonne inconnue ignorée
    recorder.close()

    rows = list(csv.DictReader((tmp_path / "sub" / "mesures.csv").open(encoding="utf-8")))
    assert [r["rpm"] for r in rows] == ["900.0", "1500.0"]
    assert rows[0]["coolant"] == ""
    assert rows[1]["coolant"] == "90.0"
    assert float(rows[1]["time"]) >= float(rows[0]["time"])
