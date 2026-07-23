from types import SimpleNamespace

import numpy as np
import pytest

from jjjexperiment.inputs.options import Vサプライの上限キャップ
from jjjexperiment.v_supply_cap import cap_V_supply_d_t_i as sut
from jjjexperiment.v_supply_cap.inputs.v_supply_cap_dto import VSupplyCapDto


HOURS = 24 * 365


def _hourly_zones(values):
    return np.repeat(np.asarray(values, dtype=float).reshape((5, 1)), HOURS, axis=1)


def _seasons():
    H = np.zeros(HOURS, dtype=bool)
    C = np.zeros(HOURS, dtype=bool)
    H[0] = True
    C[1] = True
    return H, C, np.logical_not(np.logical_or(H, C))


def test_public_orchestration_preserves_legacy_clip_season_lookup_and_inputs(monkeypatch):
    calls = []
    seasons = _seasons()
    monkeypatch.setattr(
        sut.dc,
        "get_season_array_d_t",
        lambda region: calls.append(region) or seasons,
    )
    supply = _hourly_zones([10, 30, 80, 120, 200])
    supply_before = supply.copy()
    dash_supply = _hourly_zones([100, 100, 100, 100, 100])
    ventilation = np.array([20, 20, 20, 20, 20], dtype=float)

    result = sut.cap_V_supply_d_t_i(
        VSupplyCapDto(Vサプライの上限キャップ.従来),
        supply,
        dash_supply,
        ventilation,
        6,
        550,
        580,
        print_exec=False,
    )

    np.testing.assert_array_equal(result[:, 0], [20, 30, 80, 100, 100])
    np.testing.assert_array_equal(supply, supply_before)
    np.testing.assert_array_equal(ventilation, [20, 20, 20, 20, 20])
    assert calls == [6]


@pytest.mark.parametrize(
    "logic",
    [
        Vサプライの上限キャップ.従来,
        Vサプライの上限キャップ.設計風量_全室で均一,
        Vサプライの上限キャップ.設計風量_風量増室のみ,
    ],
)
def test_public_orchestration_preserves_selected_logic_print(monkeypatch, capsys, logic):
    monkeypatch.setattr(sut.dc, "get_season_array_d_t", lambda region: _seasons())
    supply = _hourly_zones([20, 20, 20, 20, 20])

    sut.cap_V_supply_d_t_i(
        VSupplyCapDto(logic),
        supply,
        supply,
        np.array([20, 20, 20, 20, 20], dtype=float),
        6,
        None,
        None,
    )

    assert capsys.readouterr().out.strip() == str(logic)


def test_uniform_logic_preserves_none_design_airflow_as_unbounded(monkeypatch):
    monkeypatch.setattr(sut.dc, "get_season_array_d_t", lambda region: _seasons())
    supply = _hourly_zones([10, 30, 80, 120, 200])

    result = sut.cap_V_supply_d_t_i(
        VSupplyCapDto(Vサプライの上限キャップ.設計風量_全室で均一),
        supply,
        _hourly_zones([100, 100, 100, 100, 100]),
        np.array([20, 20, 20, 20, 20], dtype=float),
        6,
        None,
        None,
        print_exec=False,
    )

    np.testing.assert_array_equal(result[:, 0], [20, 30, 80, 120, 200])


def test_public_orchestration_preserves_invalid_logic_error_after_season_lookup(monkeypatch):
    calls = []
    monkeypatch.setattr(
        sut.dc,
        "get_season_array_d_t",
        lambda region: calls.append(region) or _seasons(),
    )

    with pytest.raises(ValueError, match="change_V_supply_d_t_i is out of range"):
        sut.cap_V_supply_d_t_i(
            SimpleNamespace(v_supply_cap_logic=object()),
            _hourly_zones([20, 20, 20, 20, 20]),
            _hourly_zones([20, 20, 20, 20, 20]),
            np.array([20, 20, 20, 20, 20], dtype=float),
            6,
            550,
            580,
            print_exec=False,
        )

    assert calls == [6]
