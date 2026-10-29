"""Seasonal air-path, old JSON, and full-year numerical contracts."""
from copy import deepcopy
from itertools import product
import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from verification_core import build_input_data, load_compatible_input_json
from verification_app.form_model import load_form_model
from verification_app.json_form_import import load_json_into_form
from verification_app.services import _format_input_summary
from jjjexperiment import artifact_paths
from jjjexperiment.common import injector_context, underfloor_season_context
from jjjexperiment.csv_artifacts import capture_csv_exports
from jjjexperiment.inputs.common import OuterSkin
from jjjexperiment.inputs.di_container import create_injector_from_json
from jjjexperiment.main import calc
from jjjexperiment.underfloor_ac.inputs.common import UnderfloorAc
from pyhees.jjj_runtime import resolve_underfloor_context
from pyhees.section3_1 import calc_L_H_d_t_i


@pytest.mark.parametrize('heating,cooling', product((False, True), repeat=2))
def test_form_json_roundtrip_and_manual_constants(heating, cooling, tmp_path):
    values = {f'change_underfloor_temperature_{s}__0': value
              for s, value in (('H', heating), ('C', cooling))}
    values['input_ufac_consts__0'] = True
    data = build_input_data(values)
    assert data['change_underfloor_temperature_H'] == ('2' if heating else '1')
    assert data['change_underfloor_temperature_C'] == ('2' if cooling else '1')
    path = tmp_path / 'seasonal.json'
    path.write_text(json.dumps(data))
    restored = load_json_into_form(path)
    assert build_input_data(restored.values) == data
    visible = load_form_model().visibility(restored.values)
    assert visible['input_ufac_consts__0'] == (heating or cooling)
    assert visible['R_g__0'] == (heating or cooling)
    assert visible['phi__0'] == (heating or cooling)
    summary = '\n'.join(_format_input_summary(data))
    expected = ' / '.join('使用する' if v else '使用しない' for v in (heating, cooling))
    assert f'床下空調（暖房 / 冷房）: {expected}' in summary


@pytest.mark.parametrize('legacy', (1, 2, '1', '2'))
def test_legacy_json_copies_common_value_to_both_seasons(legacy, tmp_path):
    data = build_input_data({}, version='261027')
    data['change_underfloor_temperature'] = legacy
    path = tmp_path / 'old.json'
    path.write_text(json.dumps(data))
    compatible = load_compatible_input_json(path.read_bytes()).input_data
    engine = UnderfloorAc.from_dict(compatible)
    restored = load_json_into_form(path)
    for season in ('H', 'C'):
        assert engine.enabled_for(season) == (str(legacy) == '2')
        assert restored.values[f'change_underfloor_temperature_{season}__0'] == (str(legacy) == '2')


def test_explicit_season_overrides_legacy_and_other_season_inherits(tmp_path):
    data = build_input_data({}, version='261027')
    data.update(change_underfloor_temperature='2', change_underfloor_temperature_C='1')
    path = tmp_path / 'mixed-version.json'
    path.write_text(json.dumps(data))
    restored = load_json_into_form(path)
    assert restored.values['change_underfloor_temperature_H__0']
    assert not restored.values['change_underfloor_temperature_C__0']
    injector = create_injector_from_json(deepcopy(data))
    assert injector.get(UnderfloorAc).enabled_for('H')
    assert not injector.get(UnderfloorAc).enabled_for('C')


@pytest.mark.parametrize('season', ('H', 'C'))
@pytest.mark.parametrize('conflict', ('tg', 'carryover'))
def test_either_season_preserves_unsupported_combination_checks(season, conflict, tmp_path, monkeypatch):
    data = build_input_data({f'change_underfloor_temperature_{season}__0': True})
    if conflict == 'tg':
        data['calculation_method'] = 'tg'
    else:
        data['carry_over_heat'] = 2
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match='未対応|同時に使用できません'):
        calc(data)


@pytest.mark.parametrize('bad', (None, True, False, 0, 3, 'yes'))
def test_invalid_season_is_not_silently_disabled(bad):
    with pytest.raises(ValueError, match='change_underfloor_temperature_C'):
        UnderfloorAc.from_dict({'change_underfloor_temperature_H': '2',
                               'change_underfloor_temperature_C': bad})


def test_bypass_keeps_insulation_and_restores_ventilation_load_path():
    data = build_input_data({'change_underfloor_temperature_C__0': True,
                             'underfloor_ventilation__0': True, 'r_A_ufvnt__0': 40})
    injector = create_injector_from_json(data)
    skin = injector.get(OuterSkin)
    assert skin.for_season('H').underfloor_insulation
    assert skin.for_season('C').underfloor_insulation
    assert skin.for_season('H').r_A_ufvnt == 0.4
    assert skin.for_season('H').r_A_ufac is None
    assert skin.for_season('C').r_A_ufvnt == 0
    assert skin.for_season('C').r_A_ufac == 1
    with injector_context(injector):
        for season, expected in (('H', 1), ('C', 2), ('H', 1)):
            with underfloor_season_context(season):
                resolved, _ = resolve_underfloor_context(None, None)
                assert resolved.new_ufac_flg.value == expected
    assert injector.get(UnderfloorAc).new_ufac_flg.value == 2


def test_unused_season_has_no_airflow_but_keeps_ground_history(monkeypatch):
    from jjjexperiment.underfloor_ac import hourly_solver as solver

    reference = SimpleNamespace(
        theta_ex_d_t=np.full(8760, 10.0), theta_g_avg=10.0, r_g=0.15,
        v_dash_supply_d_t_i=np.full((5, 8760), 100.0),
        u_s_supply=2.223, a_s_ufac_a=60.0, phi=0.85, l_uf=32.0,
        phi_a_0=solver.PHI_A_0,
    )
    heating_hours = np.arange(8760) < 24
    cooling_hours = ~heating_hours
    calls = []

    def heated_floor(inputs, hour, response):
        calls.append(hour)
        return 30.0

    monkeypatch.setattr(solver, '_mode_floor_temperature', heated_floor)
    floor, response = solver.solve_shared_ground_sequential(
        reference, None, heating_hours, cooling_hours, True)
    assert calls == list(range(24))
    reference.v_dash_supply_d_t_i[:] = 100000.0
    changed_flow, _ = solver.solve_shared_ground_sequential(
        reference, None, heating_hours, cooling_hours, True)
    np.testing.assert_array_equal(floor, changed_flow)
    # Warmed ground remains warmer just after the air path is bypassed.
    unheated, _ = solver.solve_shared_ground_sequential(
        reference, None, np.zeros(8760, bool), cooling_hours, True)
    assert floor[24] > unheated[24]
    assert np.isfinite(floor).all() and np.isfinite(response).all()


@pytest.fixture(scope='module')
def annual_cases(tmp_path_factory):
    results = {}
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path_factory.mktemp('seasonal-underfloor'))
        for name, legacy, heating, cooling in (
            ('legacy_off', True, False, False), ('legacy_on', True, True, True),
            ('off', False, False, False), ('both', False, True, True),
            ('heating', False, True, False), ('cooling', False, False, True),
        ):
            data = build_input_data({'underfloor_insulation__0': True}, version='261027')
            data['case_name'] = name
            if legacy:
                data['change_underfloor_temperature'] = '2' if heating else '1'
            else:
                data.pop('change_underfloor_temperature')
                data.update(change_underfloor_temperature_H='2' if heating else '1',
                            change_underfloor_temperature_C='2' if cooling else '1')
            # The BRI load cache suppresses intermediate diagnostic exports on
            # repeated runs; compare both paths with the same cold cache.
            calc_L_H_d_t_i.cache_clear()
            with capture_csv_exports() as exports:
                result = calc(deepcopy(data), test_mode=True)
            results[name] = (result['TValue'], exports, data)
    return results


def _hourly(case, name):
    # Captured paths are absolute and refer to the fixture's temporary directory.
    return next(item.frame for path, item in case[1]._items.items()
                if path.name == artifact_paths.main_output_csv_path(name, 2))


def test_common_season_choices_preserve_all_8760_hour_values(annual_cases):
    for old, new in (('legacy_off', 'off'), ('legacy_on', 'both')):
        assert annual_cases[old][0].E_H == annual_cases[new][0].E_H
        assert annual_cases[old][0].E_C == annual_cases[new][0].E_C
        old_frames = {path.name.replace(old, '', 1): item.frame
                      for path, item in annual_cases[old][1]._items.items()}
        new_frames = {path.name.replace(new, '', 1): item.frame
                      for path, item in annual_cases[new][1]._items.items()}
        assert old_frames.keys() == new_frames.keys()
        for key in old_frames:
            pd.testing.assert_frame_equal(old_frames[key], new_frames[key], check_exact=True)


@pytest.mark.parametrize('name,enabled,disabled', [('heating', 'H', 'C'), ('cooling', 'C', 'H')])
def test_bypassed_season_matches_normal_air_path(annual_cases, name, enabled, disabled):
    actual = _hourly(annual_cases[name], name)
    baseline = _hourly(annual_cases['off'], 'off')
    assert len(actual) == 8760
    columns = [column for column in baseline if f'_{disabled}_' in column]
    assert columns
    pd.testing.assert_frame_equal(actual[columns], baseline[columns], check_exact=True)
    # The enabled season actually uses the new path, rather than merely saving a flag.
    assert not np.array_equal(actual[f'E_E_{enabled}_d_t [kWh/h]'],
                              baseline[f'E_E_{enabled}_d_t [kWh/h]'])
    energy = actual[[column for column in actual if column.startswith('E_')]]
    assert np.isfinite(energy).all().all()
