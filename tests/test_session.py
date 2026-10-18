import threading

from carconnect.session import Session
from carconnect.transport import SimulatedTransport


def test_session_streams_samples_and_runs_jobs():
    got_sample = threading.Event()
    got_dtcs = threading.Event()
    samples, dtcs, errors = [], [], []

    def on_sample(sample):
        samples.append(sample)
        got_sample.set()

    session = Session(SimulatedTransport(), on_ready=lambda v: None, on_sample=on_sample, on_error=errors.append)
    session.start()
    assert got_sample.wait(5)
    session.submit(lambda obd: (dtcs.extend(obd.read_dtcs()), got_dtcs.set()))
    assert got_dtcs.wait(5)
    session.stop()

    assert not errors
    assert {"rpm", "speed", "coolant", "throttle", "load", "voltage"} <= samples[0].keys()
    assert dtcs == ["P0133"]
