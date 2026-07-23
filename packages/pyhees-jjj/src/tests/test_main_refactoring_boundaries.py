import importlib
import numpy as np
import pandas as pd
import pytest

from types import SimpleNamespace

from jjjexperiment import main as experiment_main


def test_log_equipment_specs_preserves_print_and_log_order(monkeypatch):
    cool = SimpleNamespace(q_rtd=1.0, q_max=2.0, e_rtd=3.0)
    heat = SimpleNamespace(q_rtd=4.0, q_max=5.0, e_rtd=6.0)
    printed = []
    logged = []
    monkeypatch.setattr('builtins.print', lambda *args: printed.append(args))
    monkeypatch.setattr(experiment_main._logger, 'info', logged.append)

    experiment_main._log_equipment_specs(cool, heat)

    assert printed == [
        ("q_rtd_C, q_rtd_H, q_max_C, q_max_H, e_rtd_C, e_rtd_H",),
        (1.0, 4.0, 2.0, 5.0, 3.0, 6.0),
    ]
    assert logged == [
        "q_rtd_C [w]: 1.0",
        "q_max_C [w]: 2.0",
        "e_rtd_C [-]: 3.0",
        "q_rtd_H [w]: 4.0",
        "q_max_H [w]: 5.0",
        "e_rtd_H [-]: 6.0",
    ]

def test_create_domain_services_preserves_constructor_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main, 'ClimateService', lambda *args: calls.append(('climate', args)) or 'climate')
    monkeypatch.setattr(experiment_main, 'HeatQuantityService', lambda *args: calls.append(('heat', args)) or 'heat')
    monkeypatch.setattr(experiment_main, 'CoolQuantityService', lambda *args: calls.append(('cool', args)) or 'cool')
    house = SimpleNamespace(region=6, A_A=120.0)

    result = experiment_main._create_domain_services(house, 'ufac', 'climate.csv', 'heat-setting', 'cool-setting')

    assert result == ('climate', 'heat', 'cool')
    assert calls == [
        ('climate', (6, 'ufac', 'climate.csv')),
        ('heat', ('heat-setting', 6, 120.0)),
        ('cool', ('cool-setting', 6, 120.0)),
    ]

def test_get_virtual_heating_devices_and_modes_preserves_call_order(monkeypatch):
    calls = []
    monkeypatch.setattr(
        experiment_main,
        'get_virtual_heating_devices',
        lambda region, H_MR, H_OR: calls.append(('devices', region, H_MR, H_OR)) or ('spec-mr', 'spec-or'),
    )
    monkeypatch.setattr(
        experiment_main,
        'calc_heating_mode',
        lambda **kwargs: calls.append(('modes', kwargs)) or ('mode-mr', 'mode-or'),
    )

    result = experiment_main._get_virtual_heating_devices_and_modes(6)

    assert result == ('spec-mr', 'spec-or', 'mode-mr', 'mode-or')
    assert calls == [
        ('devices', 6, None, None),
        ('modes', {'region': 6, 'H_MR': 'spec-mr', 'H_OR': 'spec-or'}),
    ]

def test_calc_standard_heating_load_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main, 'calc_heating_load', lambda *args: calls.append(args) or ('H', 'dash-H', 'dash-CS'))
    house = SimpleNamespace(region=6, sol_region=3, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(
        Q=2.0, mu_H=0.1, mu_C=0.2, NV_MR=1.0, NV_OR=2.0, TS='TS',
        r_A_ufvnt='ratio', underfloor_insulation='insulation', SHC='SHC',
    )
    heat = SimpleNamespace(mode=SimpleNamespace(name='heat-mode'))
    cool = SimpleNamespace(mode=SimpleNamespace(name='cool-mode'))
    hex_info = SimpleNamespace(to_dict=lambda: {'hex': True})

    result = experiment_main._calc_standard_heating_load(
        house, skin, hex_info, heat, cool, 'spec-mr', 'spec-or', 'mode-mr', 'mode-or'
    )

    assert result == ('H', 'dash-H', 'dash-CS')
    assert calls == [(
        6, 3, 120.0, 30.0, 50.0, 2.0, 0.1, 0.2, 1.0, 2.0, 'TS',
        'ratio', {'hex': True}, 'insulation', 'heat-mode', 'cool-mode',
        'spec-mr', 'spec-or', 'mode-mr', 'mode-or', 'SHC',
    )]

def test_override_heating_load_from_csv_preserves_first_twelve_columns(monkeypatch):
    load = pd.DataFrame(np.arange(60).reshape(2, 30))
    calls = []
    monkeypatch.setattr(experiment_main.pd, 'read_csv', lambda path, nrows: calls.append((path, nrows)) or load)

    result = experiment_main._override_heating_load_from_csv('calculated', 'loads.csv')

    np.testing.assert_array_equal(result, load.iloc[:, :12].T.values)
    assert calls == [('loads.csv', 8760)]


def test_override_heating_load_from_csv_preserves_calculated_load_without_file(monkeypatch):
    calculated = object()
    monkeypatch.setattr(experiment_main.pd, 'read_csv', lambda *args, **kwargs: pytest.fail('must not read CSV'))

    assert experiment_main._override_heating_load_from_csv(calculated, '-') is calculated

def test_calc_standard_cooling_load_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main, 'calc_cooling_load', lambda *args: calls.append(args) or ('CS', 'CL'))
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(
        Q=2.0, mu_H=0.1, mu_C=0.2, NV_MR=1.0, NV_OR=2.0,
        r_A_ufvnt='ratio', underfloor_insulation='insulation', TS='TS',
    )
    cool = SimpleNamespace(mode=SimpleNamespace(name='cool-mode'))
    heat = SimpleNamespace(mode=SimpleNamespace(name='heat-mode'))
    hex_info = SimpleNamespace(to_dict=lambda: {'hex': True})

    result = experiment_main._calc_standard_cooling_load(
        house, skin, hex_info, cool, heat, 'mode-mr', 'mode-or'
    )

    assert result == ('CS', 'CL')
    assert calls == [(
        6, 120.0, 30.0, 50.0, 2.0, 0.1, 0.2, 1.0, 2.0,
        'ratio', 'insulation', 'cool-mode', 'heat-mode',
        'mode-mr', 'mode-or', 'TS', {'hex': True},
    )]

def test_load_cooling_load_from_csv_preserves_sensible_and_latent_columns(monkeypatch):
    load = pd.DataFrame(np.arange(60).reshape(2, 30))
    calls = []
    monkeypatch.setattr(experiment_main.pd, 'read_csv', lambda path, nrows: calls.append((path, nrows)) or load)

    sensible, latent = experiment_main._load_cooling_load_from_csv('loads.csv')

    np.testing.assert_array_equal(sensible, load.iloc[:, 12:24].T.values)
    np.testing.assert_array_equal(latent, load.iloc[:, 24:].T.values)
    assert calls == [('loads.csv', 8760)]

def test_bind_load_dti_preserves_constructor_and_bind_order(monkeypatch):
    created = []

    class FakeLoadDTI:
        def __init__(self, *args):
            self.args = args
            created.append(self)

    bound = []
    injector = SimpleNamespace(binder=SimpleNamespace(bind=lambda key, to: bound.append((key, to))))
    monkeypatch.setattr(experiment_main.jjj_dc, 'Load_DTI', FakeLoadDTI)

    experiment_main._bind_load_dti(injector, 'H', 'CS', 'CL', 'dash-H', 'dash-CS')

    assert created[0].args == ('H', 'CS', 'CL', 'dash-H', 'dash-CS')
    assert bound == [(FakeLoadDTI, created[0])]

def test_sum_zone_loads_preserves_axis_zero_aggregation():
    heating = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    sensible = heating + 10.0
    latent = heating + 20.0

    result = experiment_main._sum_zone_loads(heating, sensible, latent)

    np.testing.assert_array_equal(result[0], np.array([5.0, 7.0, 9.0]))
    np.testing.assert_array_equal(result[1], np.array([25.0, 27.0, 29.0]))
    np.testing.assert_array_equal(result[2], np.array([45.0, 47.0, 49.0]))

def test_get_V_hs_dsgn_H_preserves_model_specific_rated_airflow(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main.dc_spec, 'get_V_fan_rtd_H', lambda q: calls.append(('rated', q)) or 300.0)
    monkeypatch.setattr(experiment_main.dc_spec, 'get_V_fan_dsgn_H', lambda v: calls.append(('design', v)) or v * 1.1)

    direct = experiment_main._get_V_hs_dsgn_H(
        experiment_main.計算モデル.ダクト式セントラル空調機, 200.0, 5000.0
    )
    calculated = experiment_main._get_V_hs_dsgn_H(
        experiment_main.計算モデル.電中研モデル, 200.0, 5000.0
    )

    assert direct == pytest.approx(220.0)
    assert calculated == pytest.approx(330.0)
    assert calls == [('design', 200.0), ('rated', 5000.0), ('design', 300.0)]
    with pytest.raises(Exception, match='暖房方式が不正です'):
        experiment_main._get_V_hs_dsgn_H(object(), 200.0, 5000.0)

def test_bind_heating_design_airflows_preserves_type_contract_and_bind_order():
    bound = []
    injector = SimpleNamespace(binder=SimpleNamespace(bind=lambda key, to: bound.append((key, to))))
    setting = SimpleNamespace(V_hs_dsgn=250.0)

    result = experiment_main._bind_heating_design_airflows(injector, setting, SimpleNamespace(), SimpleNamespace())

    assert result == (250.0, 0.0)
    assert bound == [
        (experiment_main.jjj_dc.VHS_DSGN_H, 250.0),
        (experiment_main.jjj_dc.VHS_DSGN_C, 0.0),
    ]


def test_bind_heating_design_airflows_rejects_non_float_override():
    injector = SimpleNamespace(binder=SimpleNamespace(bind=lambda key, to: None))
    setting = SimpleNamespace(V_hs_dsgn=250)
    with pytest.raises(AssertionError, match='V_hs_dsgn_Hの型が不正'):
        experiment_main._bind_heating_design_airflows(injector, setting, SimpleNamespace(), SimpleNamespace())

def test_run_heating_calc_Q_UT_A_preserves_bind_call_and_diagnostics(monkeypatch):
    events = []
    result = ('EUT', 'theta-out', 'theta-in', 'x-out', 'x-in', 'supply', 'vent')
    injector = SimpleNamespace(
        binder=SimpleNamespace(bind=lambda key, to: events.append(('bind', key, to))),
        call_with_injection=lambda func: events.append(('call', func)) or result,
    )
    monkeypatch.setattr(experiment_main._logger, 'NDdebug', lambda name, value: events.append(('debug', name, value)))

    actual = experiment_main._run_heating_calc_Q_UT_A(injector, 'heat-setting')

    assert actual == ('EUT', 'theta-out', 'theta-in', 'supply', 'vent')
    assert events == [
        ('bind', experiment_main.jjj_dc.ActiveAcSetting, 'heat-setting'),
        ('call', experiment_main.jjj_dc.calc_Q_UT_A),
        ('debug', 'V_hs_supply_d_t', 'supply'),
        ('debug', 'V_hs_vent_d_t', 'vent'),
    ]

def test_get_heating_fan_model_preserves_standard_fan_power(monkeypatch):
    logged = []
    monkeypatch.setattr(experiment_main._logger, 'info', logged.append)
    setting = SimpleNamespace(type=experiment_main.計算モデル.ダクト式セントラル空調機, f_SFP=0.5)

    result = experiment_main._get_heating_fan_model(setting, 200.0, None, None, 'case')

    assert result == (100.0, None)
    assert logged == ['P_rac_fan_rtd_H [W]: 100.0']


def test_get_heating_fan_model_preserves_denchu_csv_and_unit_conversion(monkeypatch):
    events = []
    frame = SimpleNamespace(to_csv=lambda path, encoding: events.append(('csv', path, encoding)))
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_1, 'calc_R_and_Pc_H', lambda catalog: (2.0, 1.0, 0.0, 0.3))
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_2, 'simu_R', lambda *args: events.append(('simu', args)) or 'simu')
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_1, 'get_DataFrame_denchu_modeling_consts', lambda *args: events.append(('frame', args)) or frame)
    monkeypatch.setattr(experiment_main.jjj_consts, 'version_info', lambda: '_v')
    monkeypatch.setattr(experiment_main._logger, 'info', lambda message: events.append(('log', message)))
    setting = SimpleNamespace(type=experiment_main.計算モデル.電中研モデル, f_SFP=0.5)

    result = experiment_main._get_heating_fan_model(setting, 200.0, 'catalog', 'inner', 'case')

    assert result == (300.0, 'simu')
    assert events == [
        ('simu', (2.0, 1.0, 0.0)),
        ('frame', ('catalog', 2.0, 1.0, 0.0, 'inner', 300.0)),
        ('csv', 'case_v_denchu_consts_H_output.csv', 'cp932'),
        ('log', 'P_rac_fan_rtd_H [W]: 300.0'),
    ]

def test_get_heating_capacity_and_HCM_preserves_call_order(monkeypatch):
    events = []
    climate = SimpleNamespace(
        get_C_df_H_d_t=lambda: events.append('C_df') or 'C-df',
        get_HCM_d_t=lambda: events.append('HCM') or 'hcm',
    )
    monkeypatch.setattr(
        experiment_main.dc_a,
        'get_q_hs_H_d_t',
        lambda *args: events.append(('capacity', args)) or 'q-h',
    )

    result = experiment_main._get_heating_capacity_and_HCM('out', 'in', 'supply', climate, 6)

    assert result == ('q-h', 'hcm')
    assert events == ['C_df', ('capacity', ('out', 'in', 'supply', 'C-df', 6)), 'HCM']

def test_get_latent_heating_fan_power_preserves_model_call(monkeypatch):
    latent = importlib.import_module('jjjexperiment.latent_load.section4_2_a')
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(latent, 'get_E_E_fan_H_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル, f_SFP=0.4)

    result = experiment_main._get_latent_heating_fan_power(setting, 'vent', 'q-h')

    assert result == 'fan'
    assert events == [('print', setting.type), ('call', ('vent', 'q-h', 0.4))]

def test_get_standard_heating_fan_power_preserves_rac_fan_and_ventilation_option(monkeypatch):
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(experiment_main.dc_a, 'get_E_E_fan_H_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(
        type=experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        f_SFP=0.4,
        subtract_ventilation_power='subtract',
    )

    result = experiment_main._get_standard_heating_fan_power(
        setting, SimpleNamespace(P_fan_rtd=100.0), 200.0, 'vent', 'supply', 300.0, 'q-h', 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低風量直接入力.入力しない),
        ('call', (200.0, 'vent', 'supply', 300.0, 'q-h', 6, 0.4, 'subtract')),
    ]

def test_get_minimum_volume_heating_fan_power_preserves_fixed_ventilation_option(monkeypatch):
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(experiment_main.dc_a, 'get_E_E_fan_H_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.ダクト式セントラル空調機, f_SFP=0.4)

    result = experiment_main._get_minimum_volume_heating_fan_power(
        setting, SimpleNamespace(P_fan_rtd=100.0), 200.0, 'vent', 'supply', 300.0, 'q-h', 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低電力直接入力.入力しない),
        ('call', (
            100.0, 'vent', 'supply', 300.0, 'q-h', 6, 0.4,
            experiment_main.ファン消費電力から換気分を引く.換気分を引かない,
        )),
    ]

def test_get_minimum_power_heating_fan_preserves_input_tuple(monkeypatch):
    module = importlib.import_module('jjjexperiment.v_min_input.section4_2_a')
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(module, 'get_E_E_fan_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.電中研モデル)
    v_min = SimpleNamespace(E_E_fan_logic='logic', E_E_fan_min=0.2)

    result = experiment_main._get_minimum_power_heating_fan(
        setting, SimpleNamespace(P_fan_rtd=100.0), v_min, 200.0, 'vent', 'supply', 300.0, 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低電力直接入力.入力する),
        ('call', ('logic', 100.0, 'vent', 'supply', 300.0, 0.2, 6, False)),
    ]

def test_raise_invalid_heating_fan_input_preserves_value_error():
    with pytest.raises(ValueError):
        experiment_main._raise_invalid_heating_fan_input()

def test_get_heating_electricity_type1_and_type3_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(
        experiment_main.jjj_dc_a,
        'calc_E_E_H_d_t_type1_and_type3',
        lambda *args: calls.append(args) or 'electricity',
    )
    setting = SimpleNamespace(type='type', equipment_spec='spec')
    climate = SimpleNamespace(get_Theta_ex_d_t=lambda: 'theta-ex')
    cool = SimpleNamespace(q_hs_rtd='q-rtd-c')
    heat = SimpleNamespace(
        q_hs_min='q-min-h', q_hs_mid='q-mid-h', P_hs_mid='p-mid-h',
        V_fan_mid='v-mid-h', P_fan_mid='p-fan-mid-h', q_hs_rtd='q-rtd-h',
        P_fan_rtd='p-fan-rtd-h', V_fan_rtd='v-fan-rtd-h', P_hs_rtd='p-rtd-h',
    )

    result = experiment_main._get_heating_electricity_type1_and_type3(
        setting, 'fan', 'q-h', 'theta-out', 'theta-in', climate, 'supply', cool, heat
    )

    assert result == 'electricity'
    assert calls == [(
        'type', 'fan', 'q-h', 'theta-out', 'theta-in', 'theta-ex', 'supply',
        'q-rtd-c', 'q-min-h', 'q-mid-h', 'p-mid-h', 'v-mid-h', 'p-fan-mid-h',
        'q-rtd-h', 'p-fan-rtd-h', 'v-fan-rtd-h', 'p-rtd-h', 'spec',
    )]
def test_get_heating_electricity_type2_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(
        experiment_main.jjj_dc_a,
        'calc_E_E_H_d_t_type2',
        lambda *args: calls.append(args) or 'electricity',
    )
    setting = SimpleNamespace(type='type')
    house = SimpleNamespace(region=6)
    heat = SimpleNamespace(
        e_rtd='e-rtd-h', q_rtd='q-rtd-h', q_max='q-max-h',
        input_C_af='c-af-h', dualcompressor='dual-h',
    )
    cool = SimpleNamespace(q_rtd='q-rtd-c', q_max='q-max-c')

    result = experiment_main._get_heating_electricity_type2(
        setting, house, 'climate.csv', 'fan', 'q-h', heat, cool
    )

    assert result == 'electricity'
    assert calls == [(
        'type', 6, 'climate.csv', 'fan', 'q-h', 'e-rtd-h', 'q-rtd-h',
        'q-rtd-c', 'q-max-h', 'q-max-c', 'c-af-h', 'dual-h',
    )]
def test_get_heating_electricity_type4_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(
        experiment_main.jjj_dc_a,
        'calc_E_E_H_d_t_type4',
        lambda *args: calls.append(args) or 'electricity',
    )
    setting = SimpleNamespace(type='type')
    house = SimpleNamespace(region=6)

    result = experiment_main._get_heating_electricity_type4(
        'case', setting, house, 'climate.csv', 'fan', 'q-h', 'supply',
        'p-rac-fan', 'simu-r', 'catalog', 'inner'
    )

    assert result == 'electricity'
    assert calls == [(
        'case', 'type', 6, 'climate.csv', 'fan', 'q-h', 'supply',
        'p-rac-fan', 'simu-r', 'catalog', 'inner',
    )]
def test_build_heating_output_dataframe_preserves_columns_values_and_diagnostics(monkeypatch):
    size = 24 * 365
    values = np.arange(size, dtype=float)
    events = []
    climate = SimpleNamespace(
        get_Theta_ex_d_t=lambda: values + 2.0,
        get_C_df_H_d_t=lambda: values + 5.0,
    )
    monkeypatch.setattr(
        experiment_main._logger,
        'NDdebug',
        lambda name, value: events.append((name, value)),
    )

    result = experiment_main._build_heating_output_dataframe(
        values, values + 1.0, values + 3.0, climate, values + 4.0, values + 6.0
    )

    assert list(result.columns) == [
        'Q_UT_H_d_A_t [MJ/h]',
        'Theta_hs_H_out_d_t [℃]',
        'Theta_hs_H_in_d_t [℃]',
        'Theta_ex_d_t [℃]',
        'V_hs_supply_H_d_t [m3/h]',
        'V_hs_vent_H_d_t [m3/h]',
        'C_df_H_d_t [-]',
    ]
    assert len(result) == size
    assert result.index[0] == pd.Timestamp('2023-01-01 01:00:00')
    assert result.index[-1] == pd.Timestamp('2024-01-01 00:00:00')
    assert result['Q_UT_H_d_A_t [MJ/h]'].isna().all()
    np.testing.assert_array_equal(result['Theta_hs_H_out_d_t [℃]'], values + 1.0)
    np.testing.assert_array_equal(result['Theta_hs_H_in_d_t [℃]'], values + 3.0)
    np.testing.assert_array_equal(result['Theta_ex_d_t [℃]'], values + 2.0)
    np.testing.assert_array_equal(result['V_hs_supply_H_d_t [m3/h]'], values + 4.0)
    np.testing.assert_array_equal(result['V_hs_vent_H_d_t [m3/h]'], values + 6.0)
    np.testing.assert_array_equal(result['C_df_H_d_t [-]'], values + 5.0)
    assert events[0][0] == 'E_UT_H_d_t'
    assert events[0][1] is values
def test_get_V_hs_dsgn_C_preserves_model_specific_rated_airflow(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main.dc_spec, 'get_V_fan_rtd_C', lambda q: calls.append(('rated', q)) or 300.0)
    monkeypatch.setattr(experiment_main.dc_spec, 'get_V_fan_dsgn_C', lambda v: calls.append(('design', v)) or v * 1.1)

    direct = experiment_main._get_V_hs_dsgn_C(
        experiment_main.計算モデル.ダクト式セントラル空調機, 200.0, 5000.0
    )
    calculated = experiment_main._get_V_hs_dsgn_C(
        experiment_main.計算モデル.電中研モデル, 200.0, 5000.0
    )

    assert direct == pytest.approx(220.0)
    assert calculated == pytest.approx(330.0)
    assert calls == [('design', 200.0), ('rated', 5000.0), ('design', 300.0)]
    with pytest.raises(Exception, match='冷房方式が不正です。'):
        experiment_main._get_V_hs_dsgn_C(object(), 200.0, 5000.0)


def test_bind_cooling_design_airflows_preserves_type_contract_and_bind_order():
    bound = []
    injector = SimpleNamespace(binder=SimpleNamespace(bind=lambda key, to: bound.append((key, to))))
    setting = SimpleNamespace(V_hs_dsgn=250.0)

    result = experiment_main._bind_cooling_design_airflows(
        injector, setting, SimpleNamespace(), SimpleNamespace()
    )

    assert result == (0.0, 250.0)
    assert bound == [
        (experiment_main.jjj_dc.VHS_DSGN_H, 0.0),
        (experiment_main.jjj_dc.VHS_DSGN_C, 250.0),
    ]
def test_get_cooling_fan_model_preserves_denchu_csv_and_unit_conversion(monkeypatch):
    events = []
    frame = SimpleNamespace(to_csv=lambda path, encoding: events.append(('csv', path, encoding)))
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_1, 'calc_R_and_Pc_C', lambda catalog: (2.0, 1.0, 0.0, 0.3))
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_2, 'simu_R', lambda *args: events.append(('simu', args)) or 'simu')
    monkeypatch.setattr(experiment_main.jjjexperiment.denchu.denchu_1, 'get_DataFrame_denchu_modeling_consts', lambda *args: events.append(('frame', args)) or frame)
    monkeypatch.setattr(experiment_main.jjj_consts, 'version_info', lambda: '_v')
    monkeypatch.setattr(experiment_main._logger, 'info', lambda message: events.append(('log', message)))
    setting = SimpleNamespace(type=experiment_main.計算モデル.電中研モデル, f_SFP=0.5)

    result = experiment_main._get_cooling_fan_model(setting, 200.0, 'catalog', 'inner', 'case')

    assert result == (300.0, 'simu')
    assert events == [
        ('simu', (2.0, 1.0, 0.0)),
        ('frame', ('catalog', 2.0, 1.0, 0.0, 'inner', 300.0)),
        ('csv', 'case_v_denchu_consts_C_output.csv', 'cp932'),
        ('log', 'P_rac_fan_rtd_C [W]: 300.0'),
    ]
def test_run_cooling_calc_Q_UT_A_preserves_call_capacity_and_diagnostics(monkeypatch):
    events = []
    calculated = ('EUT', 'theta-out', 'theta-in', 'x-out', 'x-in', 'supply', 'vent')
    injector = SimpleNamespace(
        binder=SimpleNamespace(bind=lambda key, to: events.append(('bind', key, to))),
        call_with_injection=lambda func: events.append(('call', func)) or calculated,
    )
    monkeypatch.setattr(experiment_main._logger, 'NDdebug', lambda name, value: events.append(('debug', name, value)))
    monkeypatch.setattr(experiment_main.dc_a, 'get_q_hs_C_d_t', lambda *args: events.append(('capacity', args)) or (np.array([2.0]), np.array([3.0])))

    result = experiment_main._run_cooling_calc_Q_UT_A(injector, 'cool-setting', 6)

    assert result[:7] == calculated
    np.testing.assert_array_equal(result[7], np.array([2.0]))
    np.testing.assert_array_equal(result[8], np.array([3.0]))
    np.testing.assert_array_equal(result[9], np.array([5.0]))
    assert events == [
        ('call', experiment_main.jjj_dc.calc_Q_UT_A),
        ('debug', 'V_hs_supply_d_t', 'supply'),
        ('debug', 'V_hs_vent_d_t', 'vent'),
        ('capacity', ('theta-out', 'theta-in', 'x-out', 'x-in', 'supply', 6)),
    ]
def test_get_latent_cooling_fan_power_preserves_model_call(monkeypatch):
    latent = importlib.import_module('jjjexperiment.latent_load.section4_2_a')
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(latent, 'get_E_E_fan_C_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.RAC活用型全館空調_潜熱評価モデル, f_SFP=0.4)

    result = experiment_main._get_latent_cooling_fan_power(setting, 'vent', 'q-c')

    assert result == 'fan'
    assert events == [('print', setting.type), ('call', ('vent', 'q-c', 0.4))]
def test_get_standard_cooling_fan_power_preserves_rac_fan_and_ventilation_option(monkeypatch):
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(experiment_main.dc_a, 'get_E_E_fan_C_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(
        type=experiment_main.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        f_SFP=0.4,
        subtract_ventilation_power='subtract',
    )

    result = experiment_main._get_standard_cooling_fan_power(
        setting, SimpleNamespace(P_fan_rtd=100.0), 200.0, 'vent', 'supply', 300.0, 'q-c', 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低風量直接入力.入力しない),
        ('call', (200.0, 'vent', 'supply', 300.0, 'q-c', 6, 0.4, 'subtract')),
    ]
def test_get_minimum_volume_cooling_fan_power_preserves_fixed_ventilation_option(monkeypatch):
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(experiment_main.dc_a, 'get_E_E_fan_C_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.ダクト式セントラル空調機, f_SFP=0.4)

    result = experiment_main._get_minimum_volume_cooling_fan_power(
        setting, SimpleNamespace(P_fan_rtd=100.0), 200.0, 'vent', 'supply', 300.0, 'q-c', 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低電力直接入力.入力しない),
        ('call', (
            100.0, 'vent', 'supply', 300.0, 'q-c', 6, 0.4,
            experiment_main.ファン消費電力から換気分を引く.換気分を引かない,
        )),
    ]
def test_get_minimum_power_cooling_fan_preserves_input_tuple(monkeypatch):
    module = importlib.import_module('jjjexperiment.v_min_input.section4_2_a')
    events = []
    monkeypatch.setattr('builtins.print', lambda value: events.append(('print', value)))
    monkeypatch.setattr(module, 'get_E_E_fan_d_t', lambda *args: events.append(('call', args)) or 'fan')
    setting = SimpleNamespace(type=experiment_main.計算モデル.電中研モデル)
    v_min = SimpleNamespace(E_E_fan_logic='logic', E_E_fan_min=0.2)

    result = experiment_main._get_minimum_power_cooling_fan(
        setting, SimpleNamespace(P_fan_rtd=100.0), v_min, 200.0, 'vent', 'supply', 300.0, 6
    )

    assert result == 'fan'
    assert events == [
        ('print', experiment_main.最低電力直接入力.入力する),
        ('call', ('logic', 100.0, 'vent', 'supply', 300.0, 0.2, 6, True)),
    ]
def test_raise_invalid_cooling_fan_input_preserves_value_error():
    with pytest.raises(ValueError):
        experiment_main._raise_invalid_cooling_fan_input()
def test_get_cooling_electricity_type1_and_type3_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main.jjj_dc_a, 'calc_E_E_C_d_t_type1_and_type3', lambda *args: calls.append(args) or 'electricity')
    setting = SimpleNamespace(type='type', equipment_spec='spec')
    house = SimpleNamespace(region=6)
    climate = SimpleNamespace(get_Theta_ex_d_t=lambda: 'theta-ex')
    cool = SimpleNamespace(
        q_hs_min='q-min-c', q_hs_mid='q-mid-c', P_hs_mid='p-mid-c',
        V_fan_mid='v-mid-c', P_fan_mid='p-fan-mid-c', q_hs_rtd='q-rtd-c',
        P_fan_rtd='p-fan-rtd-c', V_fan_rtd='v-fan-rtd-c', P_hs_rtd='p-rtd-c',
    )

    result = experiment_main._get_cooling_electricity_type1_and_type3(
        setting, house, 'fan', 'theta-out', 'theta-in', climate, 'supply', 'x-out', 'x-in', cool
    )

    assert result == 'electricity'
    assert calls == [(
        'type', 6, 'fan', 'theta-out', 'theta-in', 'theta-ex', 'supply', 'x-out', 'x-in',
        'q-min-c', 'q-mid-c', 'p-mid-c', 'v-mid-c', 'p-fan-mid-c', 'q-rtd-c',
        'p-fan-rtd-c', 'v-fan-rtd-c', 'p-rtd-c', 'spec',
    )]
def test_get_cooling_electricity_type2_preserves_argument_order(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main.jjj_dc_a, 'calc_E_E_C_d_t_type2', lambda *args: calls.append(args) or 'electricity')
    setting = SimpleNamespace(type='type')
    house = SimpleNamespace(region=6)
    cool = SimpleNamespace(e_rtd='e-rtd-c', q_rtd='q-rtd-c', q_max='q-max-c', input_C_af='c-af-c', dualcompressor='dual-c')

    result = experiment_main._get_cooling_electricity_type2(
        setting, house, 'climate.csv', 'fan', 'q-cs', 'q-cl', cool
    )

    assert result == 'electricity'
    assert calls == [(
        'type', 6, 'climate.csv', 'fan', 'q-cs', 'q-cl', 'e-rtd-c',
        'q-rtd-c', 'q-max-c', 'c-af-c', 'dual-c',
    )]
def test_get_cooling_electricity_type4_preserves_argument_order_and_capacity_sum(monkeypatch):
    calls = []
    monkeypatch.setattr(experiment_main.jjj_dc_a, 'calc_E_E_C_d_t_type4', lambda *args: calls.append(args) or 'electricity')
    setting = SimpleNamespace(type='type')
    house = SimpleNamespace(region=6)

    result = experiment_main._get_cooling_electricity_type4(
        'case', setting, house, 'climate.csv', 'fan', 2.0, 3.0, 'supply',
        'p-rac-fan', 'simu-r', 'catalog', 'inner'
    )

    assert result == 'electricity'
    assert calls == [(
        'case', 'type', 6, 'climate.csv', 'fan', 5.0, 'supply',
        'p-rac-fan', 'simu-r', 'catalog', 'inner',
    )]
