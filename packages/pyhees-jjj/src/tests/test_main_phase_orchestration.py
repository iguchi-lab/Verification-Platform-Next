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
