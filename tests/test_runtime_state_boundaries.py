import os
from pathlib import Path

import verification_app.services as services


class _RecordingLock:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        self.events.append("lock-enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.events.append("lock-exit")


def test_calculation_services_share_process_cwd_lock(monkeypatch, tmp_path):
    events = []
    lock = _RecordingLock(events)
    monkeypatch.setattr(services, "_CALCULATION_CWD_LOCK", lock)

    def calculate(input_data):
        events.append(("calculate", Path.cwd()))

    first = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path / "first",
    )
    second = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path / "second",
    )

    assert first.run({}).succeeded
    assert second.run({}).succeeded
    assert events == [
        "lock-enter",
        ("calculate", (tmp_path / "first").resolve()),
        "lock-exit",
        "lock-enter",
        ("calculate", (tmp_path / "second").resolve()),
        "lock-exit",
    ]


def test_calculation_service_restores_cwd_after_failure(tmp_path):
    previous_cwd = Path.cwd()

    def calculate(input_data):
        assert Path.cwd() == tmp_path.resolve()
        raise RuntimeError("calculation failed")

    service = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
    )

    result = service.run({})

    assert not result.succeeded
    assert "RuntimeError: calculation failed" in result.log
    assert Path.cwd() == previous_cwd
    assert Path(os.getcwd()) == previous_cwd
