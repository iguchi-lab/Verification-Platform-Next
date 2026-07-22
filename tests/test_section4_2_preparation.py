from types import SimpleNamespace

import numpy as np
import pytest

import jjjexperiment.section4_2_jjj as sut


def _setting(setting_type):
    return object.__new__(setting_type)


def test_output_suffix_matches_heating_and_cooling():
    assert sut._get_output_suffix(_setting(sut.HeatingAcSetting)) == "_H"
    assert sut._get_output_suffix(_setting(sut.CoolingAcSetting)) == "_C"


def test_heating_rated_capacity_service_is_called_each_time(monkeypatch):
    calls = []
    heating = _setting(sut.HeatingAcSetting)
    house = SimpleNamespace(region=6, A_A=120.0)

    class StubHeatQuantityService:
        def __init__(self, ac_setting, region, area):
            calls.append((ac_setting, region, area))
            self.q_hs_rtd = 1234.0

    monkeypatch.setattr(sut, "HeatQuantityService", StubHeatQuantityService)

    assert sut._get_q_hs_rtd_H(heating, house) == 1234.0
    assert sut._get_q_hs_rtd_H(heating, house) == 1234.0
    assert calls == [(heating, 6, 120.0), (heating, 6, 120.0)]
    assert sut._get_q_hs_rtd_C(heating, house) is None


def test_cooling_rated_capacity_service_is_called_each_time(monkeypatch):
    calls = []
    cooling = _setting(sut.CoolingAcSetting)
    house = SimpleNamespace(region=7, A_A=90.0)

    class StubCoolQuantityService:
        def __init__(self, ac_setting, region, area):
            calls.append((ac_setting, region, area))
            self.q_hs_rtd = 5678.0

    monkeypatch.setattr(sut, "CoolQuantityService", StubCoolQuantityService)

    assert sut._get_q_hs_rtd_C(cooling, house) == 5678.0
    assert sut._get_q_hs_rtd_C(cooling, house) == 5678.0
    assert calls == [(cooling, 7, 90.0), (cooling, 7, 90.0)]
    assert sut._get_q_hs_rtd_H(cooling, house) is None


@pytest.mark.parametrize(
    "helper",
    (sut._get_output_suffix, sut._get_q_hs_rtd_H, sut._get_q_hs_rtd_C),
)
def test_season_helpers_reject_unknown_setting(helper):
    if helper is sut._get_output_suffix:
        with pytest.raises(ValueError):
            helper(object())
    else:
        with pytest.raises(ValueError):
            helper(object(), SimpleNamespace(region=6, A_A=120.0))


def test_normalize_design_airflows_preserves_heating_selection():
    assert sut._normalize_design_airflows(0, 1500.0) == (None, 1500.0)


def test_normalize_design_airflows_preserves_cooling_selection():
    assert sut._normalize_design_airflows(1200.0, 0) == (1200.0, None)


def test_normalize_design_airflows_preserves_both_zero_match_priority():
    assert sut._normalize_design_airflows(0, 0) == (None, 0)


def test_normalize_design_airflows_rejects_two_nonzero_values():
    with pytest.raises(ValueError, match="暖房・冷房の判別がつかない"):
        sut._normalize_design_airflows(1200.0, 1500.0)


def test_select_minimum_airflow_input_matches_season():
    heat_input = object()
    cool_input = object()

    assert sut._select_minimum_airflow_input(
        _setting(sut.HeatingAcSetting), heat_input, cool_input
    ) is heat_input
    assert sut._select_minimum_airflow_input(
        _setting(sut.CoolingAcSetting), heat_input, cool_input
    ) is cool_input


def test_select_minimum_airflow_input_rejects_unknown_setting():
    with pytest.raises(ValueError):
        sut._select_minimum_airflow_input(object(), object(), object())


@pytest.mark.parametrize(
    "model",
    (
        sut.計算モデル.ダクト式セントラル空調機,
        sut.計算モデル.RAC活用型全館空調_潜熱評価モデル,
    ),
)
def test_rated_heat_source_capacities_use_quantity_services(monkeypatch, model):
    calls = []
    setting = SimpleNamespace(type=model)
    house = object()

    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda ac, value: 200.0)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda ac, value: 100.0)
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_C",
        lambda value: calls.append(("C", value)) or value + 2.0,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_H",
        lambda value: calls.append(("H", value)) or value + 1.0,
    )

    result = sut._get_rated_heat_source_capacities(
        setting,
        house,
        SimpleNamespace(q_rtd=300.0),
        SimpleNamespace(q_rtd=400.0),
    )

    assert result == (101.0, 202.0)
    assert calls == [("C", 200.0), ("H", 100.0)]


@pytest.mark.parametrize(
    "model",
    (
        sut.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        sut.計算モデル.電中研モデル,
    ),
)
def test_rated_heat_source_capacities_use_equipment_ratings(monkeypatch, model):
    calls = []
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_C",
        lambda value: calls.append(("C", value)) or value + 2.0,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_H",
        lambda value: calls.append(("H", value)) or value + 1.0,
    )

    result = sut._get_rated_heat_source_capacities(
        SimpleNamespace(type=model),
        object(),
        SimpleNamespace(q_rtd=300.0),
        SimpleNamespace(q_rtd=400.0),
    )

    assert result == (301.0, 402.0)
    assert calls == [("C", 400.0), ("H", 300.0)]


def test_rated_heat_source_capacities_reject_unknown_model():
    with pytest.raises(Exception, match="設備機器の種類の入力が不正です。"):
        sut._get_rated_heat_source_capacities(
            SimpleNamespace(type=object()),
            object(),
            SimpleNamespace(q_rtd=300.0),
            SimpleNamespace(q_rtd=400.0),
        )


@pytest.mark.parametrize(
    ("setting_type", "season", "representative_temperature", "runup_result"),
    (
        (sut.HeatingAcSetting, "H", sut.THETA_UF_WARM, 11.2224),
        (sut.CoolingAcSetting, "CS", sut.THETA_UF_COOL, 9.15940),
    ),
)
def test_prepare_underfloor_ground_response_preserves_order_and_season(
    monkeypatch,
    setting_type,
    season,
    representative_temperature,
    runup_result,
):
    calls = []
    theta_ex = object()
    theta_in = object()

    monkeypatch.setattr(
        sut.uf,
        "get_Theta_in_d_t",
        lambda value: calls.append(("indoor", value)) or theta_in,
    )
    monkeypatch.setattr(
        sut.algo,
        "get_Theta_g_avg",
        lambda value: calls.append(("ground", value)) or 15.5,
    )
    monkeypatch.setattr(
        sut,
        "calc_sum_Theta_dash_g_surf_A_m_runup",
        lambda temperature, average: calls.append(
            ("runup", temperature, average)
        ) or runup_result,
    )

    result = sut._prepare_underfloor_ground_response(
        _setting(setting_type),
        theta_ex,
    )

    assert result == (theta_in, 0.025504994, 15.5, runup_result)
    assert calls == [
        ("indoor", season),
        ("ground", theta_ex),
        ("runup", representative_temperature, 15.5),
    ]


def test_prepare_underfloor_ground_response_rejects_unknown_setting():
    with pytest.raises(ValueError):
        sut._prepare_underfloor_ground_response(object(), object())

@pytest.mark.parametrize(
    ("carryover", "expected"),
    (
        (sut.過剰熱量繰越計算.行う, [0.0, 2.0]),
        (sut.過剰熱量繰越計算.行わない, [-1.0, 2.0]),
    ),
)
def test_get_actual_loads_preserves_formula_order_and_clipping(
    monkeypatch,
    carryover,
    expected,
):
    calls = []
    inputs = [object() for _ in range(5)]

    def result(name, *args):
        calls.append((name, args))
        return np.array([-1.0, 2.0])

    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_CL_d_t_i",
        lambda *args: result("CL", *args),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_CS_d_t_i",
        lambda *args: result("CS", *args),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_H_d_t_i",
        lambda *args: result("H", *args),
    )

    actual = sut._get_actual_loads(
        SimpleNamespace(carry_over_heat=carryover),
        *inputs,
        6,
    )

    for value in actual:
        np.testing.assert_array_equal(value, expected)
    assert calls == [
        ("CL", (inputs[0], inputs[1], inputs[2], 6)),
        ("CS", (inputs[0], inputs[3], inputs[4], 6)),
        ("H", (inputs[0], inputs[3], inputs[4], 6)),
    ]
