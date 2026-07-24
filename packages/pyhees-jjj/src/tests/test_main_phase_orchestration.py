from types import SimpleNamespace

import pytest

from jjjexperiment import main as experiment_main


def _call_heating_fan(setting_type, minimum_volume, minimum_power):
    return experiment_main._select_heating_fan_power(
        SimpleNamespace(type=setting_type),
        "heat-quantity",
        SimpleNamespace(
            input_V_hs_min=minimum_volume,
            input_E_E_fan_min=minimum_power,
        ),
        "rated-fan",
        "ventilation",
        "supply",
        "design",
        "capacity",
        6,
    )


@pytest.mark.parametrize(
    ("setting_type", "minimum_volume", "minimum_power", "expected"),
    [
        (
            experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル,
            object(),
            object(),
            "latent",
        ),
        (
            experiment_main.計算モデル.ダクト式セントラル空調機,
            experiment_main.最低風量直接入力.入力しない,
            object(),
            "standard",
        ),
        (
            experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
            experiment_main.最低風量直接入力.入力する,
            experiment_main.最低電力直接入力.入力しない,
            "minimum-volume",
        ),
        (
            experiment_main.計算モデル.電中研モデル,
            experiment_main.最低風量直接入力.入力する,
            experiment_main.最低電力直接入力.入力する,
            "minimum-power",
        ),
    ],
)
def test_select_heating_fan_power_preserves_branch_and_result_identity(
    monkeypatch,
    setting_type,
    minimum_volume,
    minimum_power,
    expected,
):
    results = {name: object() for name in (
        "latent",
        "standard",
        "minimum-volume",
        "minimum-power",
    )}
    calls = []
    monkeypatch.setattr(
        experiment_main,
        "_get_latent_heating_fan_power",
        lambda *args: calls.append(("latent", args)) or results["latent"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_standard_heating_fan_power",
        lambda *args: calls.append(("standard", args)) or results["standard"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_minimum_volume_heating_fan_power",
        lambda *args: calls.append(("minimum-volume", args))
        or results["minimum-volume"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_minimum_power_heating_fan",
        lambda *args: calls.append(("minimum-power", args))
        or results["minimum-power"],
    )

    result = _call_heating_fan(setting_type, minimum_volume, minimum_power)

    assert result is results[expected]
    assert [call[0] for call in calls] == [expected]


@pytest.mark.parametrize(
    ("setting_type", "expected"),
    [
        (experiment_main.計算モデル.ダクト式セントラル空調機, "type1-3"),
        (
            experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル,
            "type1-3",
        ),
        (
            experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
            "type2",
        ),
        (experiment_main.計算モデル.電中研モデル, "type4"),
    ],
)
def test_select_heating_electricity_preserves_model_dispatch_and_result_identity(
    monkeypatch,
    setting_type,
    expected,
):
    results = {name: object() for name in ("type1-3", "type2", "type4")}
    calls = []
    for helper_name, label in (
        ("_get_heating_electricity_type1_and_type3", "type1-3"),
        ("_get_heating_electricity_type2", "type2"),
        ("_get_heating_electricity_type4", "type4"),
    ):
        monkeypatch.setattr(
            experiment_main,
            helper_name,
            lambda *args, label=label: calls.append((label, args)) or results[label],
        )

    result = experiment_main._select_heating_electricity(
        "case",
        "climate.csv",
        SimpleNamespace(type=setting_type),
        "house",
        "climate",
        "heat-crac",
        "cool-crac",
        "heat-quantity",
        "cool-quantity",
        "catalog",
        "real-inner",
        "fan",
        "capacity",
        "outlet",
        "inlet",
        "supply",
        "rated-fan",
        "simulation",
    )

    assert result is results[expected]
    assert [call[0] for call in calls] == [expected]


def test_heating_selectors_preserve_invalid_input_errors():
    invalid_setting = object()
    with pytest.raises(ValueError):
        _call_heating_fan(invalid_setting, object(), object())

    with pytest.raises(Exception, match="暖房方式が不正"):
        experiment_main._select_heating_electricity(
            *(["value"] * 2),
            SimpleNamespace(type=invalid_setting),
            *(["value"] * 15),
        )

def _call_cooling_fan(setting_type, minimum_volume, minimum_power):
    return experiment_main._select_cooling_fan_power(
        SimpleNamespace(type=setting_type),
        "cool-quantity",
        SimpleNamespace(
            input_V_hs_min=minimum_volume,
            input_E_E_fan_min=minimum_power,
        ),
        "rated-fan",
        "ventilation",
        "supply",
        "design",
        "capacity",
        6,
    )


@pytest.mark.parametrize(
    ("setting_type", "minimum_volume", "minimum_power", "expected"),
    [
        (
            experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル,
            object(),
            object(),
            "latent",
        ),
        (
            experiment_main.計算モデル.ダクト式セントラル空調機,
            experiment_main.最低風量直接入力.入力しない,
            object(),
            "standard",
        ),
        (
            experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
            experiment_main.最低風量直接入力.入力する,
            experiment_main.最低電力直接入力.入力しない,
            "minimum-volume",
        ),
        (
            experiment_main.計算モデル.電中研モデル,
            experiment_main.最低風量直接入力.入力する,
            experiment_main.最低電力直接入力.入力する,
            "minimum-power",
        ),
    ],
)
def test_select_cooling_fan_power_preserves_branch_and_result_identity(
    monkeypatch,
    setting_type,
    minimum_volume,
    minimum_power,
    expected,
):
    results = {name: object() for name in (
        "latent",
        "standard",
        "minimum-volume",
        "minimum-power",
    )}
    calls = []
    for helper_name, label in (
        ("_get_latent_cooling_fan_power", "latent"),
        ("_get_standard_cooling_fan_power", "standard"),
        ("_get_minimum_volume_cooling_fan_power", "minimum-volume"),
        ("_get_minimum_power_cooling_fan", "minimum-power"),
    ):
        monkeypatch.setattr(
            experiment_main,
            helper_name,
            lambda *args, label=label: calls.append((label, args)) or results[label],
        )

    result = _call_cooling_fan(setting_type, minimum_volume, minimum_power)

    assert result is results[expected]
    assert [call[0] for call in calls] == [expected]


@pytest.mark.parametrize(
    ("setting_type", "expected"),
    [
        (experiment_main.計算モデル.ダクト式セントラル空調機, "type1-3"),
        (
            experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル,
            "type1-3",
        ),
        (
            experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
            "type2",
        ),
        (experiment_main.計算モデル.電中研モデル, "type4"),
    ],
)
def test_select_cooling_electricity_preserves_model_dispatch_and_result_identity(
    monkeypatch,
    setting_type,
    expected,
):
    results = {name: object() for name in ("type1-3", "type2", "type4")}
    calls = []
    for helper_name, label in (
        ("_get_cooling_electricity_type1_and_type3", "type1-3"),
        ("_get_cooling_electricity_type2", "type2"),
        ("_get_cooling_electricity_type4", "type4"),
    ):
        monkeypatch.setattr(
            experiment_main,
            helper_name,
            lambda *args, label=label: calls.append((label, args)) or results[label],
        )

    result = experiment_main._select_cooling_electricity(
        "case",
        "climate.csv",
        SimpleNamespace(type=setting_type),
        "house",
        "climate",
        "cool-crac",
        "cool-quantity",
        "catalog",
        "real-inner",
        "fan",
        "sensible",
        "latent",
        "outlet",
        "inlet",
        "outlet-humidity",
        "inlet-humidity",
        "supply",
        "rated-fan",
        "simulation",
    )

    assert result is results[expected]
    assert [call[0] for call in calls] == [expected]


def test_cooling_selectors_preserve_invalid_input_errors():
    invalid_setting = object()
    with pytest.raises(ValueError):
        _call_cooling_fan(invalid_setting, object(), object())

    with pytest.raises(Exception, match="冷房方式が不正"):
        experiment_main._select_cooling_electricity(
            *( ["value"] * 2 ),
            SimpleNamespace(type=invalid_setting),
            *( ["value"] * 16 ),
        )

def test_run_heating_phase_preserves_order_and_result_context(monkeypatch):
    events = []
    values = {name: object() for name in (
        "unprocessed", "outlet", "inlet", "supply", "ventilation",
        "rated-fan", "simulation", "capacity", "fan", "electricity", "frame",
    )}
    monkeypatch.setattr(
        experiment_main,
        "_run_heating_calc_Q_UT_A",
        lambda *args: events.append(("calculate", args)) or (
            values["unprocessed"], values["outlet"], values["inlet"],
            values["supply"], values["ventilation"],
        ),
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_heating_fan_model",
        lambda *args: events.append(("fan-model", args))
        or (values["rated-fan"], values["simulation"]),
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_heating_capacity_and_HCM",
        lambda *args: events.append(("capacity", args))
        or (values["capacity"], "HCM"),
    )
    monkeypatch.setattr(
        experiment_main,
        "_select_heating_fan_power",
        lambda *args: events.append(("fan", args)) or values["fan"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_select_heating_electricity",
        lambda *args: events.append(("electricity", args)) or values["electricity"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_build_heating_output_dataframe",
        lambda *args: events.append(("frame", args)) or values["frame"],
    )
    inputs = experiment_main._HeatingPhaseInputs(
        injector="injector", case_name="case", climateFile="climate.csv",
        v_min_heating_input="minimum", house=SimpleNamespace(region=6),
        heat_ac_setting="setting", heat_CRAC="heat-crac", cool_CRAC="cool-crac",
        heat_denchu_catalog="catalog", heat_real_inner="inner", climate="climate",
        heat_quantity="heat-quantity", cool_quantity="cool-quantity",
        V_hs_dsgn_H="design",
    )

    result = experiment_main._run_heating_phase(inputs)

    assert [event[0] for event in events] == [
        "calculate", "fan-model", "capacity", "fan", "electricity", "frame",
    ]
    assert result == experiment_main._HeatingPhaseResult(
        values["unprocessed"], values["electricity"], values["fan"],
        values["capacity"], values["frame"],
    )


def test_run_cooling_phase_preserves_bind_order_and_result_context(monkeypatch):
    events = []
    values = {name: object() for name in (
        "unprocessed", "outlet", "inlet", "outlet-humidity", "inlet-humidity",
        "supply", "ventilation", "sensible", "latent", "capacity",
        "rated-fan", "simulation", "fan", "electricity",
    )}

    class Binder:
        def bind(self, *args, **kwargs):
            events.append(("bind", args, kwargs))

    injector = SimpleNamespace(binder=Binder())
    monkeypatch.setattr(
        experiment_main,
        "_bind_cooling_design_airflows",
        lambda *args: events.append(("design", args)) or ("design-H", "design-C"),
    )
    monkeypatch.setattr(
        experiment_main,
        "_get_cooling_fan_model",
        lambda *args: events.append(("fan-model", args))
        or (values["rated-fan"], values["simulation"]),
    )
    monkeypatch.setattr(
        experiment_main,
        "_run_cooling_calc_Q_UT_A",
        lambda *args: events.append(("calculate", args)) or (
            values["unprocessed"], values["outlet"], values["inlet"],
            values["outlet-humidity"], values["inlet-humidity"], values["supply"],
            values["ventilation"], values["sensible"], values["latent"],
            values["capacity"],
        ),
    )
    monkeypatch.setattr(
        experiment_main,
        "_select_cooling_fan_power",
        lambda *args: events.append(("fan", args)) or values["fan"],
    )
    monkeypatch.setattr(
        experiment_main,
        "_select_cooling_electricity",
        lambda *args: events.append(("electricity", args)) or values["electricity"],
    )
    monkeypatch.setattr("builtins.print", lambda *args: events.append(("print", args)))
    inputs = experiment_main._CoolingPhaseInputs(
        injector=injector, case_name="case", climateFile="climate.csv",
        v_min_cooling_input="minimum", house=SimpleNamespace(region=6),
        cool_ac_setting="setting", cool_CRAC="cool-crac",
        cool_denchu_catalog="catalog", cool_real_inner="inner", climate="climate",
        cool_quantity="cool-quantity",
    )

    result = experiment_main._run_cooling_phase(inputs)

    assert [event[0] for event in events] == [
        "print", "design", "bind", "fan-model", "calculate", "fan", "electricity",
    ]
    assert result == experiment_main._CoolingPhaseResult(
        values["unprocessed"], values["electricity"], values["fan"],
        values["sensible"], values["latent"], values["outlet"], values["inlet"],
        values["supply"], values["ventilation"],
    )
