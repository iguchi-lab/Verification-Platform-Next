"""Compensated temperatures retain unmet load and do not carry deficits twice."""
import json

import numpy as np
import pytest

from jjjexperiment import section4_2_jjj as engine
from jjjexperiment.carryover_heat.inputs.carryover_heat_dto import CarryoverHeatDto
from jjjexperiment.carryover_heat.temperature_policy import (
    TEMPERATURE_POLICIES, compensate_room_temperature,
)
from verification_app.form_app import _annual_summary_html
from verification_app.form_model import load_form_model
from verification_app.json_form_import import load_json_into_form
from verification_app.services import AnnualMetrics, AnnualSummary
from verification_core import build_input_data, load_compatible_input_json


@pytest.mark.parametrize('mode', ('signed', 'setpoint'))
def test_form_json_round_trip_and_visibility(tmp_path, mode):
    form = load_form_model()
    values = form.schema.defaults() | {
        'carry_over_heat__0': True,
        'carryover_temperature_policy__0': TEMPERATURE_POLICIES[mode],
    }
    key = 'carryover_temperature_policy__0'
    assert form.visibility(values)[key]
    assert not form.visibility(values | {'carry_over_heat__0': False})[key]
    assert not form.visibility(values | {'calculation_method__0': 'tg'})[key]
    data = build_input_data(values)
    assert data['carryover_temperature_policy'] == mode
    path = tmp_path / 'input.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    restored = load_json_into_form(path)
    assert restored.values[key] == TEMPERATURE_POLICIES[mode]
    assert build_input_data(restored.values) == data
    assert CarryoverHeatDto.from_dict(data).carryover_temperature_policy == mode
    metrics = AnnualMetrics(1, 1, 0, 0)
    summary = AnnualSummary(metrics, metrics, carryover_temperature_policy=mode)
    assert TEMPERATURE_POLICIES[mode] in _annual_summary_html(summary)


def test_old_json_and_default_dto_keep_signed_convention():
    data = build_input_data({'carry_over_heat__0': True}, version='261023')
    assert 'carryover_temperature_policy' not in data
    assert CarryoverHeatDto.from_dict(data).carryover_temperature_policy == 'signed'
    compatible = load_compatible_input_json(json.dumps(data)).input_data
    assert compatible == data | {
        'carryover_temperature_policy': 'signed',
        'change_underfloor_temperature_H': '1', 'change_underfloor_temperature_C': '1',
    }


@pytest.mark.parametrize('bad', ('unknown', None, 0, True, []))
def test_invalid_json_policy_is_rejected(bad):
    with pytest.raises(ValueError, match='carryover_temperature_policy'):
        CarryoverHeatDto.from_dict({'carryover_temperature_policy': bad})


def test_intermediate_season_is_unchanged():
    rooms = np.array([[17.0], [29.0]])
    assert compensate_room_temperature(rooms, 24, False, False) is rooms


@pytest.mark.parametrize('heating', (True, False))
def test_compensation_reaches_nonroom_unmet_energy_and_next_hour(heating):
    """Exercise actual equation 46 -> compensation -> 48 -> 5/6 -> 2/3 -> energy."""
    region = 6
    H, C, M = engine.dc.get_season_array_d_t(region)
    t = int(np.flatnonzero(H if heating else C)[1])
    setpoint = 20.0 if heating else 27.0
    volume = np.full((5, 8760), 100.0)
    supply = np.full((5, 8760), setpoint + (5 if heating else -5))
    zero = np.zeros((5, 8760))
    load = np.zeros((5, 8760))
    load[:, t] = [4, 0.3, 4, 0.3, 4]  # Deficits and surplus coexist.
    heat_load, cool_load = (load, zero) if heating else (zero, load)
    areas = np.array([engine.ld.get_A_HCZ_R_i(i) for i in range(1, 6)])
    results = {}
    for policy in ('signed', 'setpoint'):
        rooms = np.full((5, 8760), setpoint)
        nonrooms = np.full(8760, setpoint - 2 if heating else setpoint + 2)
        inputs = engine._CarryoverActualTemperatureInputs(
            t, False, H, C, M, np.full(8760, setpoint), volume, supply,
            2.17, np.full(5, 20.0), 2.6, areas, heat_load, cool_load, rooms,
            np.full(8760, setpoint - 2 if heating else setpoint + 2), 38.93,
            np.zeros(8760), volume, nonrooms, policy,
        )
        engine._update_carryover_actual_temperature_state(inputs)
        # Non-room calculation must use the compensated room state immediately.
        expected_nr = engine._get_actual_non_room_temperature_at_hour(
            engine._ActualNonRoomTemperatureHourInputs(
                t, False, H, C, M, inputs.Theta_star_NR_d_t,
                inputs.Theta_star_HBR_d_t, rooms, 38.93, np.zeros(8760),
                volume, volume, 2.17, np.full(5, 20.0), 2.6, nonrooms,
            )
        )
        assert nonrooms[t] == pytest.approx(expected_nr)
        dto = CarryoverHeatDto.from_dict({
            'carry_over_heat': 2, 'carryover_temperature_policy': policy,
        })
        actual = engine._get_actual_loads(engine._ActualLoadsInputs(
            dto, volume, zero, zero, supply, rooms, region,
        ))
        unmet = engine._get_unprocessed_loads(engine._UnprocessedLoadsInputs(
            zero, actual.L_dash_CL_d_t_i, cool_load, actual.L_dash_CS_d_t_i,
            heat_load, actual.L_dash_H_d_t_i,
        ))
        setting = engine.HeatingAcSetting.from_dict({}) if heating else engine.CoolingAcSetting.from_dict({})
        energy, _ = engine._get_unprocessed_energy(engine._UnprocessedEnergyInputs(
            setting, unmet.Q_UT_CL_d_t_i, unmet.Q_UT_CS_d_t_i,
            unmet.Q_UT_H_d_t_i, region,
        ))
        carry = engine._get_carryover_at_hour(engine._CarryoverAtHourInputs(
            t + 1, H, C, areas, rooms, np.full(8760, setpoint),
        ))
        results[policy] = rooms[:, t].copy(), nonrooms[t], energy[t], carry
    raw, bounded = results['signed'], results['setpoint']
    np.testing.assert_array_equal(bounded[0][[0, 2, 4]], setpoint)
    np.testing.assert_array_equal(bounded[0][[1, 3]], raw[0][[1, 3]])
    assert np.all(raw[0][[0, 2, 4]] < setpoint) if heating else np.all(
        raw[0][[0, 2, 4]] > setpoint)
    assert bounded[1] != raw[1]  # Not merely a display clamp.
    assert bounded[2] >= raw[2] > 0  # Unmet-load energy is retained.
    assert np.any(raw[3] < 0)
    assert np.all(bounded[3] >= 0)
    np.testing.assert_array_equal(bounded[3][[0, 2, 4]], 0)
