from types import SimpleNamespace

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
