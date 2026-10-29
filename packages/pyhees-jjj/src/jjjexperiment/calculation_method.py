"""Opt-in TG calculation contract; no replacement of upstream module functions.

See docs/tg_calculation_method.md for the scope and accounting conventions.
The context is local to one calc invocation and is reset even on failure.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field

import numpy as np
import pyhees.section4_2 as dc
import pyhees.section4_2_b as dc_spec
import pyhees.section4_3 as rac
import pyhees.section4_3_a as rac_spec

from jjjexperiment.v_min_input.validation import require_positive_finite

TG_SPECIFICATION = 'tg-2026-10-v2'
TG_PROFILES = {
    'standard': 'TG総合（従来のTG・ダクト／RAC）',
    'baseline': '現行式（比較基準）',
    'outlet_temperature': '出口温度だけを修正',
    'minimum_airflow': '最低風量の式だけを変更',
    'fan_accounting': '最低風量・送風機の計上方法を修正（n＝1）',
    'fan_characteristic': '送風機特性を比較（指数nを選択）',
    'ventilation_lower_bound': '全般換気なし：換気量下限あり・停止なし（参考）',
    'ventilation_no_stop': '全般換気なし：換気量下限なし・停止なし',
    'ventilation_stop': '全般換気なし：換気量下限なし・中間期停止',
    'partition_sign': '冷房の間仕切り熱移動の符号だけを修正',
}
ISOLATED_PROFILES = frozenset({'baseline', 'outlet_temperature', 'minimum_airflow', 'partition_sign'})
_current = ContextVar('calculation_method', default=None)
_comparison = ContextVar('tg_comparison', default=None)
_minimum_override = ContextVar('tg_minimum_override', default=None)


def current():
    return _current.get()


def isolated_comparison():
    data = _comparison.get()
    return data is not None and data.get('tg_profile', 'standard') in ISOLATED_PROFILES


def record_minimum_airflow(v_min_input):
    """Keep the formula (39) override local to this calculation and season."""
    data = _comparison.get()
    value = None
    if data is not None and data.get('tg_profile') == 'minimum_airflow':
        if int(v_min_input.input_V_hs_min.value) == 2:
            value = v_min_input.V_hs_min
    _minimum_override.set(value)


def minimum_airflow(original):
    value = _minimum_override.get()
    return original if value is None else value


def _prepare_profile(result):
    profile = result.get('tg_profile', 'standard')
    if profile not in TG_PROFILES:
        raise ValueError('TGの比較する修正内容が不正です。')
    result['tg_profile'] = profile
    if profile == 'standard':
        return
    # Focused comparisons isolate the named change from other optional corrections.
    result.update(change_supply_volume_before_vav_adjust='1', change_V_supply_d_t_i_max=1,
                  change_heat_source_outlet_required_temperature='2' if profile == 'outlet_temperature' else '1')
    if profile != 'fan_characteristic':
        result['tg_fan_exponent'] = 1.0
    for season in ('H', 'C'):
        equipment = result[f'{season}_A']
        if int(equipment.get('type', 1)) != 1:
            raise ValueError('TGの個別比較はダクト式を選択してください。RACはTG総合で比較できます。')
        equipment.update(correct_cooling_partition_heat_transfer=2 if profile == 'partition_sign' else 1,
                         correct_no_general_ventilation_airflow=1, subtract_ventilation_power=1,
                         input_E_E_fan_min=1, input_f_SFP=1)
        if profile in ('baseline', 'outlet_temperature', 'partition_sign'):
            equipment['input_V_hs_min'] = 1
        if profile.startswith('ventilation_'):
            equipment['general_ventilation'] = 2
        elif profile != 'baseline':
            equipment['general_ventilation'] = 1


def prepare_input(data):
    """Validate before creating any artifacts; leave Next input byte-for-byte compatible."""
    method = data.get('calculation_method', 'next')
    if method not in ('next', 'tg'):
        raise ValueError('計算方式は next または tg を指定してください。')
    if method == 'next':
        return data
    result = deepcopy(data)
    _prepare_profile(result)
    from jjjexperiment.underfloor_ac.selection import underfloor_enabled
    if underfloor_enabled(data):
        raise ValueError('TG方式と床下空調の併用は未対応です。')
    for key, label in (
        ('carry_over_heat', '熱の繰越'),
        ('hs_CAV', 'Next方式の熱源機定風量制御'),
    ):
        if int(data.get(key, 1)) == 2:
            raise ValueError(f'TG方式と{label}の併用は未対応です。')
    if int(data.get('underfloor_air_conditioning_air_supply', 1)) == 2:
        raise ValueError('TG方式と床下空調の併用は未対応です。')
    n = float(result.get('tg_fan_exponent', 1.0))
    if n not in (1.0, 1.5, 2.0, 3.0):
        raise ValueError('TGのファン指数は 1、1.5、2、3 から選択してください。')
    result['tg_fan_exponent'] = n
    result['calculation_method'] = 'tg'
    result['tg_specification'] = TG_SPECIFICATION
    gv = []
    for season in ('H', 'C'):
        equipment = result[f'{season}_A']
        kind = int(equipment.get('type', 1))
        if kind not in (1, 2):
            raise ValueError('TG方式はダクト式（方式1）とRAC活用型（方式2）に対応しています。')
        ventilation = int(equipment.get('general_ventilation', 1))
        if ventilation not in (1, 2):
            raise ValueError('全般換気機能は 1（あり）または 2（なし）を指定してください。')
        equipment['type'] = kind
        equipment['general_ventilation'] = ventilation
        gv.append(ventilation)
        # These Next fan controls do not define the TG power curve.
        equipment['input_E_E_fan_min'] = 1
        if kind == 2:
            q = require_positive_finite(data.get(f'tg_q_rtd_{season}', 6700 if season == 'H' else 5600), f'TG 定格{season}能力')
            efficiency_class = data.get('tg_rac_class', 'い')
            if efficiency_class not in ('い', 'ろ', 'は'):
                raise ValueError('TGのRAC効率区分は い・ろ・は から選択してください。')
            equivalent_cooling = (q + 85.1) / 1.2090 if season == 'H' else q
            q_max_c = rac_spec.get_q_max_C(equivalent_cooling)
            e_c = rac_spec.get_e_rtd_C(efficiency_class, equivalent_cooling)
            equipment.update({
                'input_rac_performance': 2,
                f'q_rac_rtd_{season}': q,
                f'q_rac_max_{season}': rac_spec.get_q_max_H(q, q_max_c) if season == 'H' else q_max_c,
                f'e_rac_rtd_{season}': rac_spec.get_e_rtd_H(e_c) if season == 'H' else e_c,
                f'input_C_af_{season}2': 2,
                f'C_af_{season}2': 0.8 if season == 'H' else 0.85,
                'input': 1,
            })
            # TG owns these specifications, regardless of the hidden Next selector.
            equipment.pop('rac_efficiency_mode', None)
            result[f'tg_q_rtd_{season}'] = q
            result['tg_rac_class'] = efficiency_class
    if gv[0] != gv[1]:
        raise ValueError('TG方式では暖房・冷房の全般換気機能を同じ設定にしてください。')
    # Fixed BRI RAC corrections used by the TG reference. Duct defrost and
    # outlet/partition switches remain explicit common inputs.
    result.update(C_df_H_d_t_defrost_rac=0.77, defrost_temp_rac=5.0,
                  defrost_humid_rac=80.0, C_hm_C=1.15)
    return result


@dataclass
class TGCalculation:
    data: dict
    designs: dict = field(default_factory=dict)
    fan_rated: dict = field(default_factory=dict)
    minima: tuple = ()
    ratios: object = None
    supply: dict = field(default_factory=dict)
    temperature: object = None

    @property
    def region(self):
        return int(self.data['region'])

    @property
    def general_ventilation(self):
        return int(self.data['H_A'].get('general_ventilation', 1)) == 1

    @property
    def ventilation_lower_bound(self):
        return self.general_ventilation or self.data.get('tg_profile') == 'ventilation_lower_bound'

    @property
    def stop_midseason(self):
        return not self.general_ventilation and self.data.get('tg_profile') not in (
            'ventilation_lower_bound', 'ventilation_no_stop')

    @property
    def exponent(self):
        return self.data['tg_fan_exponent']

    def configure(self, house, heat_quantity, cool_quantity, climate):
        self.temperature = climate.get_Theta_ex_d_t()
        for season, quantity in (('H', heat_quantity), ('C', cool_quantity)):
            equipment = self.data[f'{season}_A']
            if int(equipment['type']) == 2:
                capacity = getattr(dc_spec, f'get_q_hs_rtd_{season}')(house.region, house.A_A)
                fan_flow = getattr(dc_spec, f'get_V_fan_rtd_{season}')(capacity)
                power = getattr(dc_spec, f'get_P_fan_rtd_{season}')(fan_flow)
            else:
                fan_flow, power = quantity.V_fan_rtd, quantity.P_fan_rtd
            design = (require_positive_finite(equipment['V_hs_dsgn'], f'{season} 設計風量')
                      if int(equipment.get('input_V_hs_dsgn', 1)) == 2
                      else getattr(dc_spec, f'get_V_fan_dsgn_{season}')(fan_flow))
            self.designs[season] = float(design)
            self.fan_rated[season] = float(power)

    def cooling_unprocessed_design(self, house):
        """Reproduce BRI 3.10's cooling-UT use of the heating fan default.

        With the TG RAC replacement, get_V_fan_rtd_H ignores its capacity
        argument and uses the area-based duct heating capacity. Electricity
        still uses the cooling fan default. An explicit design overrides both.
        """
        equipment = self.data['C_A']
        if int(equipment['type']) != 2 or int(equipment.get('input_V_hs_dsgn', 1)) == 2:
            return None
        q_h = dc_spec.get_q_hs_rtd_H(house.region, house.A_A)
        return float(dc_spec.get_V_fan_dsgn_C(dc_spec.get_V_fan_rtd_H(q_h)))

    def set_ventilation(self, ventilation):
        values = []
        for season in ('H', 'C'):
            equipment = self.data[f'{season}_A']
            minimum = (require_positive_finite(equipment['V_hs_min'], f'{season} 最低風量')
                       if int(equipment.get('input_V_hs_min', 1)) == 2
                       else self.designs[season])
            if self.ventilation_lower_bound:
                minimum = max(minimum, float(np.sum(ventilation)))
            if minimum > self.designs[season]:
                raise ValueError(f'TGの{season}最低風量（換気下限適用後）が設計風量を超えています。')
            values.append(minimum)
        self.minima = (*values, max(values))

    def combine_seasons(self, values):
        heating, cooling, _ = dc.get_season_array_d_t(self.region)
        return np.where(heating, values[0], np.where(cooling, values[1], values[2]))

    def pre_vav_airflow(self, inputs):
        values = [dc.get_V_dash_hs_supply_d_t(
            minimum,
            inputs.V_hs_dsgn_H if inputs.Q_hs_rtd_H is not None else None,
            inputs.V_hs_dsgn_C if inputs.Q_hs_rtd_C is not None else None,
            inputs.Q_hs_rtd_H, inputs.Q_hs_rtd_C, inputs.Q_hat_hs_d_t,
            inputs.house.region,
        ) for minimum in self.minima]
        return self.combine_seasons(values)

    def supply_airflow(self, inputs):
        ventilation = inputs.V_vent_g_i if self.ventilation_lower_bound else np.zeros(5)
        raw_values, bounded_values = [], []
        for minimum in self.minima:
            lower = np.maximum(self.ratios * minimum, ventilation)
            raw = dc.get_V_supply_d_t_i(
                inputs.L_star_H_d_t_i, inputs.L_star_CS_d_t_i,
                inputs.Theta_sur_d_t_i, inputs.l_duct_i,
                inputs.Theta_star_HBR_d_t, lower, inputs.V_dash_supply_d_t_i,
                inputs.ac_setting.VAV, inputs.house.region, inputs.Theta_hs_out_d_t,
            )
            raw_values.append(raw)
            bounded_values.append(np.clip(raw, lower[:, None], inputs.V_dash_supply_d_t_i))
        return self.combine_seasons(raw_values), self.combine_seasons(bounded_values)

    def power(self, season, flow):
        return self.fan_rated[season] * (np.asarray(flow) / self.designs[season]) ** self.exponent

    def fan_hvac(self, season, flow):
        self.supply[season] = np.array(flow, copy=True)
        index = 0 if season == 'H' else 1
        mask = dc.get_season_array_d_t(self.region)[index]
        result = (self.power(season, flow) - self.power(season, np.minimum(flow, self.minima[index]))) * 0.001
        return np.where(mask, result, 0.0)

    def exclude_midseason(self, *arrays):
        if self.stop_midseason:
            middle = dc.get_season_array_d_t(self.region)[2]
            for array in arrays:
                array[middle] = 0.0

    def ventilation_electricity(self):
        heating, cooling, middle = dc.get_season_array_d_t(self.region)
        flow = np.where(heating, self.supply['H'], self.supply['C'])
        part = np.where(middle, flow, np.minimum(flow, np.where(heating, self.minima[0], self.minima[1])))
        ph, pc = self.power('H', part), self.power('C', part)
        result = np.where(heating, ph, np.where(cooling, pc, np.maximum(ph, pc))) * 0.001
        self.exclude_midseason(result)
        return result

    def write_accounting(self, annual, hourly, heating_mj, cooling_mj):
        ventilation = self.ventilation_electricity()
        sfp = 0.7 * 0.455 if self.general_ventilation else 0.4
        chapter5 = sfp * float(self.data['A_A']) * 2.4 * 0.5 * 1.1 * 0.001
        fan_mj = float(np.sum(ventilation)) * 9.76
        chapter5_mj = chapter5 * 8760 * 9.76
        annual['calculation_method'] = 'tg'
        annual['E_fan_vent [MJ/year]'] = fan_mj
        annual['E_vent_ch5 [MJ/year]'] = chapter5_mj
        annual['E_total_TG [MJ/year]'] = heating_mj + cooling_mj + fan_mj + chapter5_mj
        hourly['E_E_fan_vent_d_t [kWh/h]'] = ventilation
        hourly['E_E_vent_ch5_d_t [kWh/h]'] = chapter5
        hourly['E_total_TG_d_t [MJ/h]'] = (
            hourly['E_H_d_t [MJ/h]'] + hourly['E_C_d_t [MJ/h]']
            + (ventilation + chapter5) * 9.76
        )
        print(f'TG換気相当分 [MJ/year]: {fan_mj}; 第五章換気相当分: {chapter5_mj}')
        print(f'TG比較合計 [MJ/year]: {heating_mj + cooling_mj + fan_mj + chapter5_mj}')


def rac_electricity(season, output, specification, temperature):
    """BRI RAC efficiency curve evaluated at duct output, without a second load cap."""
    q, q_max, efficiency = specification.q_rtd, specification.q_max, specification.e_rtd
    if season == 'H':
        equivalent_cooling = (q + 85.1) / 1.2090
        corrected = np.maximum(output, 0.0) * 0.0036 / 0.8
        numerator = rac.calc_f_H_Theta(corrected / (q_max * 0.0036), equivalent_cooling, specification.dualcompressor, temperature)
        denominator = rac.calc_f_H_Theta(q / q_max, equivalent_cooling, specification.dualcompressor, np.full_like(temperature, 7.0))
    else:
        corrected = np.maximum(output, 0.0) * 0.0036 / (1.15 * 0.85)
        numerator = rac.calc_f_C_Theta(corrected / (q_max * 0.0036), temperature, q, specification.dualcompressor)
        denominator = rac.calc_f_C_Theta(q / q_max, np.full_like(temperature, 35.0), q, specification.dualcompressor)
    return np.where(corrected == 0.0, 0.0, numerator / denominator * q / efficiency * 0.001)


@contextmanager
def calculation_scope(data):
    comparison = data if data.get('calculation_method', 'next') == 'tg' else None
    comparison_token = _comparison.set(comparison)
    minimum_token = _minimum_override.set(None)
    context = TGCalculation(data) if comparison is not None and not isolated_comparison() else None
    token = _current.set(context)
    try:
        yield context
    finally:
        _current.reset(token)
        _minimum_override.reset(minimum_token)
        _comparison.reset(comparison_token)


def write_comparison_accounting(annual, hourly, heating_mj, cooling_mj):
    data = _comparison.get()
    if data is None:
        return
    profile = data.get('tg_profile', 'standard')
    annual['calculation_method'] = 'tg'
    annual['tg_profile'] = profile
    if current() is not None:
        current().write_accounting(annual, hourly, heating_mj, cooling_mj)
    elif profile == 'baseline':
        # The baseline keeps original HVAC accounting and adds the separate
        # ventilation system only to the optional HVAC + ventilation comparison.
        sfp = .7 if int(data['H_A'].get('general_ventilation', 1)) == 1 else .4
        chapter5 = sfp * float(data['A_A']) * 2.4 * .5 * 1.1 * .001
        annual['E_fan_vent [MJ/year]'] = 0.0
        annual['E_vent_ch5 [MJ/year]'] = chapter5 * 8760 * 9.76
        annual['E_total_TG [MJ/year]'] = heating_mj + cooling_mj + chapter5 * 8760 * 9.76
        hourly['E_E_fan_vent_d_t [kWh/h]'] = 0.0
        hourly['E_E_vent_ch5_d_t [kWh/h]'] = chapter5
        hourly['E_total_TG_d_t [MJ/h]'] = hourly['E_H_d_t [MJ/h]'] + hourly['E_C_d_t [MJ/h]'] + chapter5 * 9.76
