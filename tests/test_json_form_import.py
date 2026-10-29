"""Saved inputs survive loading, editing and resubmission through the form."""
import json
from itertools import product
from pathlib import Path

import pytest

from jjjexperiment.calculation_method import TG_PROFILES, prepare_input
from jjjexperiment.inputs.cooling import CRACSpecification as Cooling
from jjjexperiment.inputs.heating import CRACSpecification as Heating
from verification_app.json_form_import import load_json_into_form
from verification_core import build_input_data, load_input_schema
from verification_core.form_import import restore_form_values

SCHEMA = load_input_schema()
FIELDS = {field.key: field for field in SCHEMA.fields}
RAC = FIELDS['H_A_type__0'].choices[1]
DIRECT = '定格COPを直接入力〔検証用〕'


def imported(tmp_path, data):
    path = tmp_path / 'input.json'
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return load_json_into_form(path)


def specs(data):
    cool = Cooling.from_dict(data['C_A'], data['A_A'])
    heat = Heating.from_dict(data['H_A'], cool.q_rtd, cool.q_max, cool.e_rtd)
    return [(s.q_rtd, s.q_max, s.e_rtd) for s in (heat, cool)]


@pytest.mark.parametrize('heating,cooling', tuple(product(range(4), repeat=2)))
def test_all_equipment_branches_and_coefficients_round_trip(tmp_path, heating, cooling):
    values = SCHEMA.defaults()
    values.update({
        'H_A_type__0': FIELDS['H_A_type__0'].choices[heating],
        'C_A_type__0': FIELDS['C_A_type__0'].choices[cooling],
        'A_A__0': 153.275, 'U_A__0': 0.365,
        'HEX_install__0': '設置する', 'etr_t__0': 73.25,
        'H_A_VAV__0': '採用する', 'C_A_VAV__0': '採用する',
        'correct_cooling_partition_heat_transfer__0': True,
        'input_ufac_consts__0': True, 'phi__0': 0.845957617838108,
    })
    # Use distinct values to catch swapped heating/cooling and polynomial slots.
    for index, field in enumerate(SCHEMA.fields):
        if field.key.startswith(('a0__', 'a1__', 'a2__', 'a3__', 'a4__', 'c1_BR_R_')):
            values[field.key] = (index + 1) / 1000
    data = build_input_data(values)
    result = imported(tmp_path, data)
    assert build_input_data(result.values) == data
    edited = build_input_data(result.values | {'U_A__0': 0.42})
    assert edited == data | {'U_A': 0.42}


@pytest.mark.parametrize('h_mode,c_mode', tuple(product(
    ('規定値を使用', '効率区分を指定', DIRECT), repeat=2)))
def test_independent_rac_efficiency_and_capacities(tmp_path, h_mode, c_mode):
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'H_A_input_mode__0': h_mode, 'C_A_input_mode__0': c_mode,
        'H_A_mode__0': 'ろ', 'C_A_mode__0': 'い',
        'H_A_input_rac_performance__0': '性能を直接入力',
        'C_A_input_rac_performance__0': '性能を直接入力',
        'H_A_q_rac_rtd_H__0': 5000.5, 'C_A_q_rac_rtd_C__0': 4000.5,
        'e_rac_rtd_H__0': 4.53, 'e_rac_rtd_C__0': 4.12,
    })
    result = imported(tmp_path, data)
    assert build_input_data(result.values) == data
    assert specs(build_input_data(result.values)) == specs(data)


@pytest.mark.parametrize('direct_capacity,heating_selector', tuple(product((False, True), (False, True))))
def test_legacy_rac_import_preserves_actual_performance(tmp_path, direct_capacity, heating_selector):
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'C_A_input_mode__0': '効率区分を指定', 'C_A_mode__0': 'ろ',
        'H_A_input_mode__0': '効率区分を指定', 'H_A_mode__0': 'い',
        'C_A_input_rac_performance__0': '性能を直接入力' if direct_capacity else '面積から能力を算出',
        'e_rac_rtd_C__0': 4.25,
    })
    for season in ('H', 'C'):
        data[f'{season}_A'].pop('rac_efficiency_mode')
    if not heating_selector:
        data['H_A'].pop('input_mode')
        data['H_A'].pop('mode')
    result = imported(tmp_path, data)
    assert specs(build_input_data(result.values)) == specs(data)
    assert result.notes
    if direct_capacity and not heating_selector:
        assert result.values['H_A_input_mode__0'] == DIRECT


@pytest.mark.parametrize('profile', TG_PROFILES)
def test_tg_profiles_preserve_effective_calculation_input(tmp_path, profile):
    data = prepare_input(build_input_data({
        'calculation_method__0': 'tg', 'tg_profile__0': profile,
        'tg_rac_class__0': 'ろ', 'tg_q_rtd_H__0': 5000, 'tg_q_rtd_C__0': 4000,
        **({'H_A_type__0': RAC, 'C_A_type__0': RAC} if profile == 'standard' else {}),
    }))
    result = imported(tmp_path, data)
    restored = prepare_input(build_input_data(result.values))
    assert restored == data


def test_missing_keys_and_bom_are_supplemented(tmp_path):
    path = tmp_path / 'old.json'
    path.write_text(json.dumps({'A_A': 130.125, 'case_name': '旧条件'}), encoding='utf-8-sig')
    result = load_json_into_form(path)
    assert result.values['A_A__0'] == 130.125
    assert result.values['case_name__0'] == '旧条件'
    assert '初期値で補完' in result.notes[0]


@pytest.mark.parametrize('payload', ('[]', '{', '{"A_A": NaN}', '{"A_A": null}', '{"region": 99}', '{"H_A": {"type": 1.5}}'))
def test_invalid_json_does_not_produce_partial_form_values(tmp_path, payload):
    path = tmp_path / 'bad.json'
    path.write_text(payload)
    with pytest.raises((ValueError, TypeError)):
        load_json_into_form(path)


def test_shared_switch_conflict_is_not_silently_overwritten(tmp_path):
    data = build_input_data({})
    data['H_A']['correct_cooling_partition_heat_transfer'] = 2
    with pytest.raises(ValueError, match='反映できません'):
        imported(tmp_path, data)


def test_unrepresented_settings_are_reported(tmp_path):
    data = build_input_data({})
    data['custom_calculation_setting'] = 10
    with pytest.raises(ValueError, match='custom_calculation_setting'):
        imported(tmp_path, data)


def test_coefficient_length_and_nonfinite_numbers_are_rejected():
    data = build_input_data({})
    data['C1_BR_R_i'] = [0.1]
    with pytest.raises(ValueError, match='要素数'):
        restore_form_values(data)
    data = build_input_data({})
    data['U_A'] = float('inf')
    with pytest.raises(ValueError, match='有限'):
        restore_form_values(data)


def test_import_callback_updates_form_visibility_and_clears_previous_results(tmp_path):
    from verification_app.form_app import build_app
    from verification_app.services import CalculationService
    demo = build_app(service=CalculationService(lambda _: pytest.fail('Import ran calculation'), lambda: 'test'))
    fn = next(block.fn for block in demo.fns.values() if block.fn and block.fn.__name__ == 'import_uploaded_json')
    path = tmp_path / 'tg.json'
    path.write_text(json.dumps(build_input_data({
        'calculation_method__0': 'tg', 'C_A_type__0': RAC,
        'tg_q_rtd_C__0': 4000, 'tg_rac_class__0': 'ろ',
    })))
    result = fn(str(path))
    assert 'まだ計算' in result[0]
    fields = dict(zip((f.key for f in SCHEMA.fields), result[1:1 + len(SCHEMA.fields)], strict=True))
    assert fields['tg_q_rtd_C__0']['value'] == 4000
    assert fields['tg_q_rtd_C__0']['visible'] is True
    assert fields['tg_q_rtd_H__0']['visible'] is False
    assert fields['tg_rac_class__0']['value'] == 'ろ'
    assert fields['H_A_type__0']['choices'] == list(FIELDS['H_A_type__0'].choices[:2])
    assert result[-1] is None  # previous calculation result cannot be exported
    # Invalid imports preserve every current field and every existing result.
    path.write_text('{} broken')
    failed = fn(str(path))
    assert failed[0].startswith('❌')
    assert all(update == {'__type__': 'update'} for update in failed[1:])
    # Programmatic batch updates must not invoke callbacks that reset imported values.
    for block in demo.fns.values():
        if block.fn and block.fn.__name__ in ('apply_comparison_profile', 'reset_unsupported_mode_inputs'):
            assert all(event == 'input' for _, event in block.targets)


@pytest.mark.parametrize('kind', (1, 2, 3, 4))
def test_real_pre_next_saved_inputs_load(tmp_path, kind):
    path = Path(__file__).resolve().parents[1] / f'packages/pyhees-jjj/src/test_utils/input_sample_type{kind}.json'
    result = load_json_into_form(path)
    data = build_input_data(result.values)
    assert data['H_A']['type'] == kind
    assert data['C_A']['type'] == kind


def test_import_profile_lock_is_released_by_next_import(tmp_path):
    from verification_app.form_app import build_app
    from verification_app.services import CalculationService
    demo = build_app(service=CalculationService(lambda _: None, lambda: 'test'))
    callbacks = {b.fn.__name__: b.fn for b in demo.fns.values() if b.fn}
    fn = callbacks['import_uploaded_json']
    path = tmp_path / 'profile.json'
    path.write_text(json.dumps(build_input_data({
        'calculation_method__0': 'tg', 'tg_profile__0': 'outlet_temperature',
    })))
    result = fn(str(path))
    fields = dict(zip((f.key for f in SCHEMA.fields), result[1:1 + len(SCHEMA.fields)], strict=True))
    assert fields['change_heat_source_outlet_required_temperature__0']['value'] is True
    assert fields['change_heat_source_outlet_required_temperature__0']['interactive'] is False
    path.write_text(json.dumps(build_input_data({'change_underfloor_temperature_H__0': True})))
    result = fn(str(path))
    fields = dict(zip((f.key for f in SCHEMA.fields), result[1:1 + len(SCHEMA.fields)], strict=True))
    assert fields['change_underfloor_temperature_H__0']['value'] is True
    assert fields['change_heat_source_outlet_required_temperature__0']['interactive'] is True
    assert fields['H_A_type__0']['choices'] == list(FIELDS['H_A_type__0'].choices)
    assert all(update['interactive'] for update in callbacks['reset_inputs']()[:len(SCHEMA.fields)])
