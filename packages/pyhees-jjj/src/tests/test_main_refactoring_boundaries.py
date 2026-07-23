from types import SimpleNamespace

from jjjexperiment import main as experiment_main


def test_log_equipment_specs_preserves_print_and_log_order(monkeypatch):
    cool = SimpleNamespace(q_rtd=1.0, q_max=2.0, e_rtd=3.0)
    heat = SimpleNamespace(q_rtd=4.0, q_max=5.0, e_rtd=6.0)
    printed = []
    logged = []
    monkeypatch.setattr('builtins.print', lambda *args: printed.append(args))
    monkeypatch.setattr(experiment_main._logger, 'info', logged.append)

    experiment_main._log_equipment_specs(cool, heat)

    assert printed == [
        ("q_rtd_C, q_rtd_H, q_max_C, q_max_H, e_rtd_C, e_rtd_H",),
        (1.0, 4.0, 2.0, 5.0, 3.0, 6.0),
    ]
    assert logged == [
        "q_rtd_C [w]: 1.0",
        "q_max_C [w]: 2.0",
        "e_rtd_C [-]: 3.0",
        "q_rtd_H [w]: 4.0",
        "q_max_H [w]: 5.0",
        "e_rtd_H [-]: 6.0",
    ]