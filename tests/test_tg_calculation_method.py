"""Public contract tests for the opt-in TG implementation (no private sources)."""
from copy import deepcopy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from verification_core import build_input_data, load_compatible_input_json
from verification_app.form_model import load_form_model
from jjjexperiment import calculation_method as method
from pyhees.section4_2 import get_season_array_d_t


def tg_input():
    return build_input_data({'calculation_method__0': 'tg'})


def test_old_json_defaults_to_next_and_next_input_is_unchanged():
    old = build_input_data({}, version='260812')
    assert method.prepare_input(old) is old
    restored = load_compatible_input_json(json.dumps(old)).input_data
    assert restored['calculation_method'] == 'next'
    assert method.prepare_input(restored) == restored


@pytest.mark.parametrize('key', [
    'change_underfloor_temperature', 'underfloor_air_conditioning_air_supply',
    'carry_over_heat', 'hs_CAV',
])
def test_tg_rejects_unsupported_combinations_before_writing(key, tmp_path, monkeypatch):
    from jjjexperiment.main import calc
    monkeypatch.chdir(tmp_path)
    data = tg_input()
    data[key] = '2'
    with pytest.raises(ValueError, match='未対応'):
        calc(data)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('exponent', [0, -1, 1.2, float('nan'), float('inf')])
def test_tg_rejects_invalid_exponent(exponent):
    data = tg_input()
    data['tg_fan_exponent'] = exponent
    with pytest.raises(ValueError, match='指数'):
        method.prepare_input(data)


def test_tg_rac_heating_uses_independent_capacity_and_preserves_caller_input():
    data = tg_input()
    data['H_A']['type'] = data['C_A']['type'] = 2
    data.update(tg_q_rtd_H=5000, tg_q_rtd_C=4000, tg_rac_class='い')
    original = deepcopy(data)
    prepared = method.prepare_input(data)
    assert data == original
    assert prepared['H_A']['q_rac_rtd_H'] == 5000
    assert prepared['C_A']['q_rac_rtd_C'] == 4000
    heating = deepcopy(prepared['H_A'])
    data['tg_q_rtd_C'] = 8000
    assert method.prepare_input(data)['H_A'] == heating


def test_tg_scope_is_restored_on_exception_and_nested_next_call():
    with method.calculation_scope(method.prepare_input(tg_input())) as context:
        assert method.current() is context
        with method.calculation_scope({}):
            assert method.current() is None
        assert method.current() is context
        with pytest.raises(RuntimeError), method.calculation_scope(tg_input()):
            raise RuntimeError('failed run')
        assert method.current() is context
    assert method.current() is None


@pytest.mark.parametrize('exponent', [1, 1.5, 2, 3])
@pytest.mark.parametrize('ventilation', [True, False])
def test_fan_accounting_conserves_total_power_including_thermo_off(exponent, ventilation):
    data = method.prepare_input(tg_input())
    data['tg_fan_exponent'] = exponent
    data['H_A']['general_ventilation'] = 1 if ventilation else 2
    context = method.TGCalculation(data, designs={'H': 1000., 'C': 1000.},
                                   fan_rated={'H': 200., 'C': 200.}, minima=(300, 300, 300))
    flow = np.full(8760, 600.)
    heating = context.fan_hvac('H', flow)
    cooling = context.fan_hvac('C', flow)
    vent = context.ventilation_electricity()
    total = heating + cooling + vent
    h, c, middle = get_season_array_d_t(6)
    np.testing.assert_allclose(total[h | c], 0.2 * 0.6 ** exponent)
    np.testing.assert_allclose(total[middle], 0.2 * 0.6 ** exponent if ventilation else 0)
    np.testing.assert_allclose(vent[h | c], 0.2 * 0.3 ** exponent)
    assert (heating[~h] == 0).all()
    assert (cooling[~c] == 0).all()


def test_minimum_flow_uses_original_ventilation_and_seasonal_design():
    data = method.prepare_input(tg_input())
    context = method.TGCalculation(data, designs={'H': 1000., 'C': 1200.})
    ventilation = np.array([60., 20., 40., 20., 20.])
    context.set_ventilation(ventilation)
    assert context.minima == (1000, 1200, 1200)
    for season in ('H', 'C'):
        data[season+'_A'].update(input_V_hs_min=2, V_hs_min=100)
    context.set_ventilation(ventilation)
    assert context.minima == (160, 160, 160)
    data['H_A']['general_ventilation'] = 2
    context.set_ventilation(ventilation)
    assert context.minima == (100, 100, 100)
    np.testing.assert_array_equal(ventilation, [60, 20, 40, 20, 20])


def test_tg_minimum_supply_is_area_based_and_clipped_per_room():
    context = method.TGCalculation(method.prepare_input(tg_input()),
                                   minima=(300, 300, 300),
                                   ratios=np.array([.4, .2, .2, .1, .1]))
    upper = np.full((5, 8760), 200.)
    z = np.zeros((5, 8760))
    inputs = SimpleNamespace(
        V_vent_g_i=np.array([60, 20, 40, 20, 20]),
        L_star_H_d_t_i=z, L_star_CS_d_t_i=z,
        Theta_sur_d_t_i=np.full_like(z, 20.), l_duct_i=np.zeros(5),
        Theta_star_HBR_d_t=np.full(8760, 20.),
        Theta_hs_out_d_t=np.full(8760, 20.),
        V_dash_supply_d_t_i=upper, ac_setting=SimpleNamespace(VAV=True),
        house=SimpleNamespace(region=6),
    )
    bounded = context.supply_airflow(inputs)[1]
    np.testing.assert_allclose(bounded, np.broadcast_to(np.array([120, 60, 60, 30, 30])[:, None], bounded.shape))


def test_tg_visibility_hides_next_only_controls_and_underfloor_descendants():
    model = load_form_model()
    values = model.schema.defaults()
    values.update(calculation_method__0='tg', change_underfloor_temperature__0=True,
                  input_ufac_consts__0=True)
    visible = model.visibility(values)
    assert visible['tg_fan_exponent__0']
    for key in ('change_underfloor_temperature__0', 'input_ufac_consts__0', 'R_g__0',
                'phi__0', 'H_A_input_E_E_fan_min__0', 'correct_no_general_ventilation_airflow__0'):
        assert not visible[key]
    values['calculation_method__0'] = 'next'
    assert not model.visibility(values)['tg_fan_exponent__0']
    assert model.visibility(values)['change_underfloor_temperature__0']


@pytest.mark.parametrize('kind, ventilation, minimum, vav', [
    (1, 1, None, 1), (1, 2, 300, 2), (2, 1, 300, 2), (2, 2, None, 1),
])
def test_tg_full_year_accounting_and_metadata(kind, ventilation, minimum, vav, tmp_path, monkeypatch):
    from jjjexperiment.main import calc
    from jjjexperiment.csv_artifacts import capture_csv_exports
    from jjjexperiment import artifact_paths
    from verification_app.services import CalculationService
    from verification_app.form_app import _annual_summary_html

    monkeypatch.chdir(tmp_path)
    data = tg_input()
    for season in ('H', 'C'):
        data[season+'_A'].update(type=kind, general_ventilation=ventilation, VAV=vav,
                                input_V_hs_min=1 if minimum is None else 2,
                                V_hs_min=minimum)
    with capture_csv_exports() as exports:
        calc(data)
    annual = exports.dataframe(artifact_paths.main_output_csv_path('default', 1)).iloc[0]
    hourly = exports.dataframe(artifact_paths.main_output_csv_path('default', 2))
    assert len(hourly) == 8760
    energy = hourly[[column for column in hourly if column.startswith('E_')]]
    assert np.isfinite(energy).all().all()
    # Inactive-season temperatures are undefined when the heat source carries
    # no ventilation. Check each calculation's active season.
    for season, mask in zip(('H', 'C'), get_season_array_d_t(data['region'])[:2]):
        assert np.isfinite(hourly.loc[mask, f'Theta_hs_{season}_out_d_t [℃]']).all()
    assert annual['calculation_method'] == 'tg'
    reference_totals = {
        (1, 1, None, 1): 63584.17884531444,
        (1, 2, 300, 2): 58222.904222805184,
        (2, 1, 300, 2): 55969.00543402867,
        (2, 2, None, 1): 66196.597954212,
    }
    assert annual['E_total_TG [MJ/year]'] == pytest.approx(
        reference_totals[kind, ventilation, minimum, vav], rel=1e-9, abs=1e-8,
    )
    assert annual['E_total_TG [MJ/year]'] == pytest.approx(hourly['E_total_TG_d_t [MJ/h]'].sum())
    assert annual['E_total_TG [MJ/year]'] == pytest.approx(sum(annual[key] for key in (
        'E_H [MJ/year]', 'E_C [MJ/year]', 'E_fan_vent [MJ/year]', 'E_vent_ch5 [MJ/year]',
    )))
    if ventilation == 2:
        middle = get_season_array_d_t(data['region'])[2]
        assert (hourly.loc[middle, 'E_E_fan_vent_d_t [kWh/h]'] == 0).all()
    manifest = json.loads((tmp_path / artifact_paths.metadata_json_path('default')).read_text())
    assert manifest['calculation_method'] == 'tg'
    assert manifest['tg_specification'] == method.TG_SPECIFICATION
    from jjjexperiment.release import input_sha256
    saved = json.loads((tmp_path / artifact_paths.input_json_path('default')).read_text())
    assert manifest['input_sha256'] == input_sha256(saved)
    service = CalculationService(lambda data: None, lambda: '_v1.5.2')
    summary = service._annual_summary(data, tmp_path, exports)
    assert summary.tg_total_mj == annual['E_total_TG [MJ/year]']
    assert 'TG比較合計' in _annual_summary_html(summary)
    assert method.current() is None


def test_mode_switch_resets_unsupported_inputs_and_restores_equipment_choices():
    from verification_app.form_app import build_app
    from verification_app.services import CalculationService
    model = load_form_model()
    fields = {field.key: field for field in model.schema.fields}
    app = build_app(service=CalculationService(lambda data: None, lambda: 'test'), model=model)
    callback = next(fn.fn for fn in app.fns.values()
                    if fn.fn and fn.fn.__name__ == 'reset_unsupported_mode_inputs')
    heat_choices = fields['H_A_type__0'].choices
    cool_choices = fields['C_A_type__0'].choices
    tg = callback('tg', heat_choices[3], cool_choices[1])
    assert all(update['value'] is False for update in tg[:3])
    assert tg[3]['choices'] == list(heat_choices[:2])
    assert tg[3]['value'] == heat_choices[0]
    assert tg[4]['value'] == cool_choices[1]
    next_updates = callback('next', heat_choices[0], cool_choices[1])
    assert next_updates[3]['choices'] == list(heat_choices)
    assert next_updates[4]['choices'] == list(cool_choices)


def test_tg_rejects_unknown_method_model_and_mismatched_ventilation():
    data = tg_input()
    data['calculation_method'] = 'typo'
    with pytest.raises(ValueError, match='計算方式'):
        method.prepare_input(data)
    data = tg_input()
    data['H_A']['type'] = 3
    with pytest.raises(ValueError, match='方式1'):
        method.prepare_input(data)
    data = tg_input()
    data['C_A']['general_ventilation'] = 2
    with pytest.raises(ValueError, match='同じ設定'):
        method.prepare_input(data)
