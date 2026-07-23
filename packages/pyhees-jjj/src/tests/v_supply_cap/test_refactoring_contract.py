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


def test_prepare_supply_cap_state_preserves_clip_totals_and_season_masks():
    H, C, _ = _seasons()
    state = sut._prepare_supply_cap_state(
        _hourly_zones([10, 30, 80, 120, 200]),
        _hourly_zones([20, 20, 20, 20, 20]),
        H,
        C,
        400,
        500,
    )

    np.testing.assert_array_equal(state.V_supply_d_t_i[:, 0], [20, 30, 80, 120, 200])
    assert state.V_supply_d_t[0] == 450
    assert state.overflow_mask_H_d_t[0]
    assert not state.overflow_mask_C_d_t[0]
    assert not state.overflow_mask_H_d_t[1]
    assert not state.overflow_mask_C_d_t[1]


def test_uniform_reduction_ratio_preserves_ceiling_rounding_and_default_one():
    totals = np.array([550.0001, 540.0])
    mask = np.array([True, False])

    result = sut._get_uniform_reduction_ratio(totals, 550.0, mask)

    np.testing.assert_array_equal(result, [550.0 / 550.001, 1.0])


def test_uniform_design_cap_preserves_heating_then_cooling_ratio_application():
    supply = np.array([[200.0, 200.0], [100.0, 100.0]])
    state = sut._SupplyCapState(
        supply,
        np.array([300.0, 300.0]),
        np.array([True, False]),
        np.array([False, True]),
    )

    result = sut._apply_uniform_design_cap(state, 270.0, 240.0)

    np.testing.assert_array_equal(
        result,
        supply * np.array([0.9, 0.8])[np.newaxis, :],
    )

def test_prepare_increment_only_cap_state_preserves_targets_overflow_and_sums():
    supply = np.array(
        [
            [200.0, 100.0],
            [90.0, 100.0],
            [120.0, 100.0],
            [80.0, 100.0],
            [100.0, 100.0],
        ]
    )
    state = sut._SupplyCapState(
        supply,
        np.sum(supply, axis=0),
        np.array([True, False]),
        np.array([False, True]),
    )

    result = sut._prepare_increment_only_cap_state(
        state,
        np.full((5, 2), 100.0),
        550.0,
        480.0,
    )

    np.testing.assert_array_equal(
        result.added_mask_d_t_i[:, 0],
        [True, False, True, False, False],
    )
    np.testing.assert_array_equal(
        result.target_mask_H_d_t_i[:, 0],
        [True, False, True, False, False],
    )
    assert not np.any(result.target_mask_C_d_t_i[:, 1])
    np.testing.assert_array_equal(result.overflow_values_H_d_t, [40.0, -50.0])
    np.testing.assert_array_equal(result.overflow_values_C_d_t, [110.0, 20.0])
    np.testing.assert_array_equal(result.masked_vs_H_d_t_i[:, 0], [200, 0, 120, 0, 0])
    np.testing.assert_array_equal(result.added_sums_H_d_t_i[:, 0], [320] * 5)
    np.testing.assert_array_equal(result.added_sums_C_d_t_i[:, 1], [0] * 5)

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
