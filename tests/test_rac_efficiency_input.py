"""UI-to-engine contract for independent RAC capacity and efficiency inputs."""
import json
from itertools import product

import pytest

from verification_core import build_input_data, load_compatible_input_json
from verification_app.form_model import load_form_model
from jjjexperiment.inputs.cooling import CRACSpecification as Cooling
from jjjexperiment.inputs.heating import CRACSpecification as Heating
from jjjexperiment import calculation_method

RAC = 'ルームエアコンディショナ活用型全館空調（現行省エネ法ルームエアコンモデル）'
DIRECT = '定格COPを直接入力〔検証用〕'
MODES = ('規定値を使用', '効率区分を指定', DIRECT)


def specs(data):
    cool = Cooling.from_dict(data['C_A'], data['A_A'])
    heat = Heating.from_dict(data['H_A'], cool.q_rtd, cool.q_max, cool.e_rtd)
    return heat, cool


@pytest.mark.parametrize('capacity,mode', tuple(product(
    ('面積から能力を算出', '性能を直接入力'), MODES)))
def test_capacity_and_efficiency_are_independent_and_inactive_fields_ignored(capacity, mode):
    values = {
        f'{s}_A_{key}__0': value
        for s in ('H', 'C')
        for key, value in [('type', RAC), ('input_rac_performance', capacity),
                           ('input_mode', mode), ('mode', 'い')]
    }
    values.update({
        'H_A_q_rac_rtd_H__0': 5000, 'H_A_q_rac_max_H__0': 7000,
        'C_A_q_rac_rtd_C__0': 4000, 'C_A_q_rac_max_C__0': 5000,
        'e_rac_rtd_H__0': 4.5 if mode == DIRECT else float('nan'),
        'e_rac_rtd_C__0': 4.0 if mode == DIRECT else float('nan'),
    })
    heat, cool = specs(build_input_data(values))
    q_c = 4000 if capacity == '性能を直接入力' else 5600
    assert cool.q_rtd == q_c
    assert heat.q_rtd == pytest.approx(5000 if capacity == '性能を直接入力' else 6685.3)
    if mode == DIRECT:
        assert (heat.e_rtd, cool.e_rtd) == (4.5, 4.0)
    else:
        expected = (-0.000553 * q_c + 6.34 if mode == '効率区分を指定'
                    else -0.000473 * q_c + 5.50)
        assert cool.e_rtd == pytest.approx(expected)
        assert heat.e_rtd == pytest.approx(0.77 * expected + 1.66)


@pytest.mark.parametrize('season,mode,capacity', tuple(product(
    ('H', 'C'), MODES, ('面積から能力を算出', '性能を直接入力'))))
def test_visibility_shows_only_the_selected_efficiency_method(season, mode, capacity):
    model = load_form_model()
    values = model.schema.defaults() | {
        f'{season}_A_type__0': RAC,
        f'{season}_A_input_mode__0': mode,
        f'{season}_A_input_rac_performance__0': capacity,
    }
    visible = model.visibility(values)
    assert visible[f'{season}_A_mode__0'] == (mode == '効率区分を指定')
    assert visible[f'e_rac_rtd_{season}__0'] == (mode == DIRECT)
    assert visible[f'{season}_A_q_rac_rtd_{season}__0'] == (capacity == '性能を直接入力')
    # A hidden Next selector must hide both dependent controls under TG.
    visible_tg = model.visibility(values | {'calculation_method__0': 'tg'})
    assert not visible_tg[f'{season}_A_mode__0']
    assert not visible_tg[f'e_rac_rtd_{season}__0']


def test_heating_and_cooling_can_choose_different_efficiency_methods():
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'H_A_input_mode__0': DIRECT, 'e_rac_rtd_H__0': 4.25,
        'C_A_input_mode__0': '効率区分を指定', 'C_A_mode__0': 'ろ',
    })
    heat, cool = specs(data)
    assert heat.e_rtd == 4.25
    assert cool.e_rtd == pytest.approx(3.0576)
    loaded = load_compatible_input_json(json.dumps(data))
    assert loaded.input_data == data
    assert loaded.supplemented_paths == ()


@pytest.mark.parametrize('capacity', ('面積から能力を算出', '性能を直接入力'))
@pytest.mark.parametrize('heating_selector', (True, False))
def test_old_saved_json_retains_its_numerical_behavior(capacity, heating_selector):
    old = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'H_A_input_rac_performance__0': capacity,
        'C_A_input_rac_performance__0': capacity,
        'H_A_input_mode__0': '入力する', 'H_A_mode__0': 'ろ',
        'C_A_input_mode__0': '入力する', 'C_A_mode__0': 'い',
        'H_A_q_rac_rtd_H__0': 5000, 'H_A_q_rac_max_H__0': 7000,
        'C_A_q_rac_rtd_C__0': 4000, 'C_A_q_rac_max_C__0': 5000,
        'e_rac_rtd_H__0': 4.5, 'e_rac_rtd_C__0': 4.0,
    }, version='261021_2')
    if not heating_selector:
        del old['H_A']['input_mode']
        del old['H_A']['mode']
    restored = load_compatible_input_json(json.dumps(old)).input_data
    assert 'rac_efficiency_mode' not in restored['H_A']
    assert specs(restored) == specs(old)
    if capacity == '性能を直接入力':
        assert tuple(s.e_rtd for s in specs(restored)) == (4.5, 4.0)


@pytest.mark.parametrize('season,bad', tuple(product(('H', 'C'), (0, -1, float('nan'), float('inf')))))
def test_direct_cop_requires_a_positive_finite_value(season, bad):
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        f'{season}_A_input_mode__0': DIRECT, f'e_rac_rtd_{season}__0': bad,
    })
    with pytest.raises(ValueError, match='COP'):
        specs(data)


@pytest.mark.parametrize('season', ('H', 'C'))
def test_direct_capacity_requires_maximum_at_least_rated(season):
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        f'{season}_A_input_rac_performance__0': '性能を直接入力',
        f'{season}_A_q_rac_rtd_{season}__0': 5000,
        f'{season}_A_q_rac_max_{season}__0': 4000,
    })
    with pytest.raises(ValueError, match='定格.*以上'):
        specs(data)


def test_tg_uses_its_own_cop_regardless_of_hidden_next_selections():
    data = build_input_data({
        'calculation_method__0': 'tg', 'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'H_A_input_mode__0': DIRECT, 'e_rac_rtd_H__0': 99,
        'C_A_input_mode__0': '規定値を使用',
    })
    prepared = calculation_method.prepare_input(data)
    heat, cool = specs(prepared)
    assert heat.e_rtd == prepared['H_A']['e_rac_rtd_H']
    assert cool.e_rtd == pytest.approx(3.2432)


def test_direct_efficiency_ignores_inactive_class_values():
    data = build_input_data({
        'H_A_type__0': RAC, 'C_A_type__0': RAC,
        'H_A_input_mode__0': DIRECT, 'e_rac_rtd_H__0': 4.25,
        'C_A_input_mode__0': DIRECT, 'e_rac_rtd_C__0': 4.0,
    })
    for season in ('H_A', 'C_A'):
        data[season]['input_mode'] = 2
        data[season]['mode'] = None
    assert tuple(item.e_rtd for item in specs(data)) == (4.25, 4.0)
