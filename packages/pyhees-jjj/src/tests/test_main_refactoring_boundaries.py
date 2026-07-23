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

def test_create_domain_services_preserves_constructor_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main, 'ClimateService', lambda *args: calls.append(('climate', args)) or 'climate')
    monkeypatch.setattr(experiment_main, 'HeatQuantityService', lambda *args: calls.append(('heat', args)) or 'heat')
    monkeypatch.setattr(experiment_main, 'CoolQuantityService', lambda *args: calls.append(('cool', args)) or 'cool')
    house = SimpleNamespace(region=6, A_A=120.0)

    result = experiment_main._create_domain_services(house, 'ufac', 'climate.csv', 'heat-setting', 'cool-setting')

    assert result == ('climate', 'heat', 'cool')
    assert calls == [
        ('climate', (6, 'ufac', 'climate.csv')),
        ('heat', ('heat-setting', 6, 120.0)),
        ('cool', ('cool-setting', 6, 120.0)),
    ]