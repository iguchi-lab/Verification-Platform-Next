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
