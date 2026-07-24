import json
from typing import NamedTuple
import numpy as np
from injector import Injector, inject
import pandas as pd
from datetime import datetime

from pyhees.section2_1_b import get_f_prim
from pyhees.section4_1 import calc_heating_load, calc_cooling_load, get_virtual_heating_devices
from pyhees.section4_1_a import calc_heating_mode

# ダクト式セントラル空調機
import pyhees.section4_2_a as dc_a
import pyhees.section4_2_b as dc_spec

# 床下
import pyhees.section3_1 as ld
from pyhees.section3_2 import calc_r_env, get_Q_dash, get_mu_H, get_mu_C

""" オーバーライドロジック """

import jjjexperiment.section4_2_jjj as jjj_dc
import jjjexperiment.section4_2_a_jjj as jjj_dc_a

""" 独自ロジック """

# 電中研モデルロジック
import jjjexperiment.denchu.denchu_1
import jjjexperiment.denchu.denchu_2
import jjjexperiment.denchu.inputs.heating as jjj_denchu_heat_ipt
import jjjexperiment.denchu.inputs.cooling as jjj_denchu_cool_ipt

import jjjexperiment.inputs.di_container as jjj_ipt_di
from jjjexperiment.inputs.options import (
    ファン消費電力から換気分を引く,
    最低電力直接入力,
    最低風量直接入力,
    計算モデル,
)
# データクラス
from jjjexperiment.inputs.common import HouseInfo, OuterSkin, HEX
from jjjexperiment.inputs.ac_setting import HeatingAcSetting, CoolingAcSetting
from jjjexperiment.inputs.heating import CRACSpecification as HeatCRACSpec
from jjjexperiment.inputs.cooling import CRACSpecification as CoolCRACSpec
# ドメインサービス
from jjjexperiment.inputs.climate_service import ClimateService
from jjjexperiment.inputs.ac_quantity_service import HeatQuantityService, CoolQuantityService

import jjjexperiment.constants as jjj_consts
import jjjexperiment.common as jjj_common
from jjjexperiment.result import ResultSummary, SutValues
from jjjexperiment.logger import LimitedLoggerAdapter as _logger  # デバッグ用ロガー
from jjjexperiment.common import Array8760
import jjjexperiment.underfloor_ac.inputs as jjj_ufac_ipt

# [F25-01] 最低風量の直接入力
import jjjexperiment.v_min_input as jjj_V_min_input


class _MinimumFanElectricityInputs(NamedTuple):
    E_E_fan_logic: object
    P_fan_rtd: object
    V_hs_vent_d_t: object
    V_hs_supply_d_t: object
    V_hs_dsgn: object
    E_E_fan_min: object
    region: object
    for_cooling: object


class _CoolingType4ElectricityInputs(NamedTuple):
    case_name: object
    type: object
    region: object
    climateFile: object
    E_E_fan_C_d_t: object
    q_hs_C_d_t: object
    V_hs_supply_d_t: object
    P_rac_fan_rtd_C: object
    simu_R_C: object
    spec: object
    real_inner: object


class _CoolingType2ElectricityInputs(NamedTuple):
    type: object
    region: object
    climateFile: object
    E_E_fan_C_d_t: object
    q_hs_CS_d_t: object
    q_hs_CL_d_t: object
    e_rtd_C: object
    q_rtd_C: object
    q_max_C: object
    input_C_af_C: object
    dualcompressor_C: object


class _CoolingType1And3ElectricityInputs(NamedTuple):
    type: object
    region: object
    E_E_fan_C_d_t: object
    Theta_hs_out_d_t: object
    Theta_hs_in_d_t: object
    Theta_ex_d_t: object
    V_hs_supply_d_t: object
    X_hs_out_d_t: object
    X_hs_in_d_t: object
    q_hs_min_C: object
    q_hs_mid_C: object
    P_hs_mid_C: object
    V_fan_mid_C: object
    P_fan_mid_C: object
    q_hs_rtd_C: object
    P_fan_rtd_C: object
    V_fan_rtd_C: object
    P_hs_rtd_C: object
    equipment_spec: object


class _HeatingType4ElectricityInputs(NamedTuple):
    case_name: object
    type: object
    region: object
    climateFile: object
    E_E_fan_H_d_t: object
    q_hs_H_d_t: object
    V_hs_supply_d_t: object
    P_rac_fan_rtd_H: object
    simu_R_H: object
    spec: object
    real_inner: object


class _HeatingType2ElectricityInputs(NamedTuple):
    type: object
    region: object
    climateFile: object
    E_E_fan_H_d_t: object
    q_hs_H_d_t: object
    e_rtd_H: object
    q_rtd_H: object
    q_rtd_C: object
    q_max_H: object
    q_max_C: object
    input_C_af_H: object
    dualcompressor_H: object


class _HeatingType1And3ElectricityInputs(NamedTuple):
    type: object
    E_E_fan_H_d_t: object
    q_hs_H_d_t: object
    Theta_hs_out_d_t: object
    Theta_hs_in_d_t: object
    Theta_ex_d_t: object
    V_hs_supply_d_t: object
    q_hs_rtd_C: object
    q_hs_min_H: object
    q_hs_mid_H: object
    P_hs_mid_H: object
    V_fan_mid_H: object
    P_fan_mid_H: object
    q_hs_rtd_H: object
    P_fan_rtd_H: object
    V_fan_rtd_H: object
    P_hs_rtd_H: object
    equipment_spec: object


def calc(input_data: dict, test_mode=False):
    case_name = input_data.get('case_name', 'default')
    with open(case_name + jjj_consts.version_info() + '_input.json', 'w') as f:
        json.dump(input_data, f, indent=4)

    # グローバル定数の設定
    # NOTE: 必要最小限に留めること
    jjj_consts.set_constants(input_data)

    injector = jjj_ipt_di.create_injector_from_json(input_data, test_mode)
    # NOTE: 引数全てを型解決できるようにする必要があった
    return injector.call_with_injection(calc_main)

def _log_equipment_specs(cool_CRAC, heat_CRAC):
    print("q_rtd_C, q_rtd_H, q_max_C, q_max_H, e_rtd_C, e_rtd_H")
    print(cool_CRAC.q_rtd, heat_CRAC.q_rtd, cool_CRAC.q_max, heat_CRAC.q_max, cool_CRAC.e_rtd, heat_CRAC.e_rtd)

    _logger.info(f"q_rtd_C [w]: {cool_CRAC.q_rtd}")
    _logger.info(f"q_max_C [w]: {cool_CRAC.q_max}")
    _logger.info(f"e_rtd_C [-]: {cool_CRAC.e_rtd}")
    _logger.info(f"q_rtd_H [w]: {heat_CRAC.q_rtd}")
    _logger.info(f"q_max_H [w]: {heat_CRAC.q_max}")
    _logger.info(f"e_rtd_H [-]: {heat_CRAC.e_rtd}")

def _create_domain_services(house, ufac, climateFile, heat_ac_setting, cool_ac_setting):
    climate = ClimateService(house.region, ufac, climateFile)
    heat_quantity = HeatQuantityService(heat_ac_setting, house.region, house.A_A)
    cool_quantity = CoolQuantityService(cool_ac_setting, house.region, house.A_A)
    return climate, heat_quantity, cool_quantity

def _get_virtual_heating_devices_and_modes(region):
    H_MR = None
    H_OR = None

    spec_MR, spec_OR = get_virtual_heating_devices(region, H_MR, H_OR)
    mode_MR, mode_OR = calc_heating_mode(region=region, H_MR=spec_MR, H_OR=spec_OR)
    return spec_MR, spec_OR, mode_MR, mode_OR

def _calc_standard_heating_load(house, skin, hex, heat_ac_setting, cool_ac_setting, spec_MR, spec_OR, mode_MR, mode_OR):
    return calc_heating_load(
        house.region, house.sol_region, house.A_A, house.A_MR, house.A_OR,
        skin.Q, skin.mu_H, skin.mu_C, skin.NV_MR, skin.NV_OR, skin.TS,
        skin.r_A_ufvnt, hex.to_dict(), skin.underfloor_insulation,
        heat_ac_setting.mode.name, cool_ac_setting.mode.name,
        spec_MR, spec_OR, mode_MR, mode_OR, skin.SHC,
    )

def _override_heating_load_from_csv(L_H_d_t_i, loadFile):
    if loadFile != '-':
        load = pd.read_csv(loadFile, nrows=24 * 365)
        return load.iloc[:, :12].T.values
    return L_H_d_t_i

def _calc_standard_cooling_load(house, skin, hex, cool_ac_setting, heat_ac_setting, mode_MR, mode_OR):
    return calc_cooling_load(
        house.region, house.A_A, house.A_MR, house.A_OR,
        skin.Q, skin.mu_H, skin.mu_C, skin.NV_MR, skin.NV_OR,
        skin.r_A_ufvnt, skin.underfloor_insulation,
        cool_ac_setting.mode.name, heat_ac_setting.mode.name,
        mode_MR, mode_OR, skin.TS, hex.to_dict(),
    )

def _load_cooling_load_from_csv(loadFile):
    load = pd.read_csv(loadFile, nrows=24 * 365)
    L_CS_d_t_i = load.iloc[:, 12:24].T.values
    L_CL_d_t_i = load.iloc[:, 24:].T.values
    return L_CS_d_t_i, L_CL_d_t_i

def _bind_load_dti(injector, L_H_d_t_i, L_CS_d_t_i, L_CL_d_t_i, L_dash_H_R_d_t_i, L_dash_CS_R_d_t_i):
    load_dti = jjj_dc.Load_DTI(
        L_H_d_t_i, L_CS_d_t_i, L_CL_d_t_i,
        L_dash_H_R_d_t_i, L_dash_CS_R_d_t_i,
    )
    injector.binder.bind(jjj_dc.Load_DTI, to=load_dti)

def _sum_zone_loads(L_H_d_t_i, L_CS_d_t_i, L_CL_d_t_i):
    L_H_d_t = np.sum(L_H_d_t_i, axis=0)
    L_CS_d_t = np.sum(L_CS_d_t_i, axis=0)
    L_CL_d_t = np.sum(L_CL_d_t_i, axis=0)
    return L_H_d_t, L_CS_d_t, L_CL_d_t

def _get_V_hs_dsgn_H(type: 計算モデル, v_fan_rtd, q_rtd_H):
    if type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_潜熱評価モデル,
    ]:
        V_fan_rtd_H = v_fan_rtd
    elif type in [
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        計算モデル.電中研モデル,
    ]:
        V_fan_rtd_H = dc_spec.get_V_fan_rtd_H(q_rtd_H)
    else:
        raise Exception("暖房方式が不正です。")

    return dc_spec.get_V_fan_dsgn_H(V_fan_rtd_H)

def _bind_heating_design_airflows(injector, heat_ac_setting, heat_quantity, heat_CRAC):
    V_hs_dsgn_H = (
        heat_ac_setting.V_hs_dsgn
        if heat_ac_setting.V_hs_dsgn > 0
        else _get_V_hs_dsgn_H(heat_ac_setting.type, heat_quantity.V_fan_rtd, heat_CRAC.q_rtd)
    )
    V_hs_dsgn_C = 0.0

    assert isinstance(V_hs_dsgn_H, float), "V_hs_dsgn_Hの型が不正"
    injector.binder.bind(jjj_dc.VHS_DSGN_H, to=V_hs_dsgn_H)
    assert isinstance(V_hs_dsgn_C, float), "V_hs_dsgn_Cの型が不正"
    injector.binder.bind(jjj_dc.VHS_DSGN_C, to=V_hs_dsgn_C)
    return V_hs_dsgn_H, V_hs_dsgn_C

def _run_heating_calc_Q_UT_A(injector, heat_ac_setting):
    injector.binder.bind(jjj_dc.ActiveAcSetting, to=heat_ac_setting)
    E_UT_H_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, _, _, V_hs_supply_d_t, V_hs_vent_d_t = (
        injector.call_with_injection(jjj_dc.calc_Q_UT_A)
    )
    _logger.NDdebug("V_hs_supply_d_t", V_hs_supply_d_t)
    _logger.NDdebug("V_hs_vent_d_t", V_hs_vent_d_t)
    return E_UT_H_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, V_hs_supply_d_t, V_hs_vent_d_t

def _get_heating_fan_model(heat_ac_setting, V_hs_dsgn_H, heat_denchu_catalog, heat_real_inner, case_name):
    simu_R_H = None
    if heat_ac_setting.type == 計算モデル.電中研モデル:
        R2, R1, R0, P_rac_fan_rtd_H = jjjexperiment.denchu.denchu_1.calc_R_and_Pc_H(heat_denchu_catalog)
        P_rac_fan_rtd_H = 1000 * P_rac_fan_rtd_H
        simu_R_H = jjjexperiment.denchu.denchu_2.simu_R(R2, R1, R0)
        df_denchu_consts = jjjexperiment.denchu.denchu_1.get_DataFrame_denchu_modeling_consts(
            heat_denchu_catalog, R2, R1, R0, heat_real_inner, P_rac_fan_rtd_H
        )
        df_denchu_consts.to_csv(
            case_name + jjj_consts.version_info() + '_denchu_consts_H_output.csv',
            encoding='cp932',
        )
    else:
        P_rac_fan_rtd_H = V_hs_dsgn_H * heat_ac_setting.f_SFP
    _logger.info(f"P_rac_fan_rtd_H [W]: {P_rac_fan_rtd_H}")
    return P_rac_fan_rtd_H, simu_R_H

def _get_heating_capacity_and_HCM(Theta_hs_out_d_t, Theta_hs_in_d_t, V_hs_supply_d_t, climate, region):
    q_hs_H_d_t = dc_a.get_q_hs_H_d_t(
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        V_hs_supply_d_t,
        climate.get_C_df_H_d_t(),
        region,
    )
    HCM = climate.get_HCM_d_t()
    return q_hs_H_d_t, HCM

def _get_latent_heating_fan_power(heat_ac_setting, V_hs_vent_d_t, q_hs_H_d_t):
    print(heat_ac_setting.type)
    import jjjexperiment.latent_load.fan_power as latent_fan_power
    return latent_fan_power.get_E_E_fan_H_d_t(
        V_hs_vent_d_t, q_hs_H_d_t, heat_ac_setting.f_SFP
    )

def _get_standard_heating_fan_power(heat_ac_setting, heat_quantity, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, q_hs_H_d_t, region):
    print(最低風量直接入力.入力しない)
    P_fan_rtd = (
        P_rac_fan_rtd_H
        if heat_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else heat_quantity.P_fan_rtd
    )
    return dc_a.get_E_E_fan_H_d_t(
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_H,
        q_hs_H_d_t,
        region,
        heat_ac_setting.f_SFP,
        heat_ac_setting.subtract_ventilation_power,
    )

def _get_minimum_volume_heating_fan_power(heat_ac_setting, heat_quantity, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, q_hs_H_d_t, region):
    print(最低電力直接入力.入力しない)
    P_fan_rtd = (
        P_rac_fan_rtd_H
        if heat_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else heat_quantity.P_fan_rtd
    )
    return dc_a.get_E_E_fan_H_d_t(
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_H,
        q_hs_H_d_t,
        region,
        heat_ac_setting.f_SFP,
        ファン消費電力から換気分を引く.換気分を引かない,
    )

def _get_minimum_power_heating_fan(heat_ac_setting, heat_quantity, v_min_heating_input, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, region):
    print(最低電力直接入力.入力する)
    P_fan_rtd = (
        P_rac_fan_rtd_H
        if heat_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else heat_quantity.P_fan_rtd
    )
    from jjjexperiment.v_min_input.fan_power import get_E_E_fan_d_t
    return get_E_E_fan_d_t(*_MinimumFanElectricityInputs(
        v_min_heating_input.E_E_fan_logic,
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_H,
        v_min_heating_input.E_E_fan_min,
        region,
        False,
    ))

def _get_heating_electricity_type1_and_type3(heat_ac_setting, E_E_fan_H_d_t, q_hs_H_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, climate, V_hs_supply_d_t, cool_quantity, heat_quantity):
    return jjj_dc_a.calc_E_E_H_d_t_type1_and_type3(
        *_HeatingType1And3ElectricityInputs(
            heat_ac_setting.type,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            Theta_hs_out_d_t,
            Theta_hs_in_d_t,
            climate.get_Theta_ex_d_t(),
            V_hs_supply_d_t,
            cool_quantity.q_hs_rtd,
            heat_quantity.q_hs_min,
            heat_quantity.q_hs_mid,
            heat_quantity.P_hs_mid,
            heat_quantity.V_fan_mid,
            heat_quantity.P_fan_mid,
            heat_quantity.q_hs_rtd,
            heat_quantity.P_fan_rtd,
            heat_quantity.V_fan_rtd,
            heat_quantity.P_hs_rtd,
            heat_ac_setting.equipment_spec,
        )
    )

def _get_heating_electricity_type2(heat_ac_setting, house, climateFile, E_E_fan_H_d_t, q_hs_H_d_t, heat_CRAC, cool_CRAC):
    return jjj_dc_a.calc_E_E_H_d_t_type2(
        *_HeatingType2ElectricityInputs(
            heat_ac_setting.type,
            house.region,
            climateFile,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            heat_CRAC.e_rtd,
            heat_CRAC.q_rtd,
            cool_CRAC.q_rtd,
            heat_CRAC.q_max,
            cool_CRAC.q_max,
            heat_CRAC.input_C_af,
            heat_CRAC.dualcompressor,
        )
    )
def _get_heating_electricity_type4(case_name, heat_ac_setting, house, climateFile, E_E_fan_H_d_t, q_hs_H_d_t, V_hs_supply_d_t, P_rac_fan_rtd_H, simu_R_H, heat_denchu_catalog, heat_real_inner):
    return jjj_dc_a.calc_E_E_H_d_t_type4(
        *_HeatingType4ElectricityInputs(
            case_name,
            heat_ac_setting.type,
            house.region,
            climateFile,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            V_hs_supply_d_t,
            P_rac_fan_rtd_H,
            simu_R_H,
            heat_denchu_catalog,
            heat_real_inner,
        )
    )
def _build_heating_output_dataframe(E_UT_H_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, climate, V_hs_supply_d_t, V_hs_vent_d_t):
    _logger.NDdebug("E_UT_H_d_t", E_UT_H_d_t)
    df_output2 = pd.DataFrame(
        index=pd.date_range(datetime(2023, 1, 1, 1, 0, 0), datetime(2024, 1, 1, 0, 0, 0), freq='h')
    )
    df_output2['Q_UT_H_d_A_t [MJ/h]'] = np.full(len(df_output2), np.nan)
    df_output2['Theta_hs_H_out_d_t [℃]'] = Theta_hs_out_d_t
    df_output2['Theta_hs_H_in_d_t [℃]'] = Theta_hs_in_d_t
    df_output2['Theta_ex_d_t [℃]'] = climate.get_Theta_ex_d_t()
    df_output2['V_hs_supply_H_d_t [m3/h]'] = V_hs_supply_d_t
    df_output2['V_hs_vent_H_d_t [m3/h]'] = V_hs_vent_d_t
    df_output2['C_df_H_d_t [-]'] = climate.get_C_df_H_d_t()
    return df_output2
def _get_V_hs_dsgn_C(type: 計算モデル, v_fan_rtd: float, q_rtd_C: float):
    if type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_潜熱評価モデル,
    ]:
        V_fan_rtd_C = v_fan_rtd
    elif type in [
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        計算モデル.電中研モデル,
    ]:
        V_fan_rtd_C = dc_spec.get_V_fan_rtd_C(q_rtd_C)
    else:
        raise Exception("冷房方式が不正です。")

    return dc_spec.get_V_fan_dsgn_C(V_fan_rtd_C)


def _bind_cooling_design_airflows(injector, cool_ac_setting, cool_quantity, cool_CRAC):
    V_hs_dsgn_C = (
        cool_ac_setting.V_hs_dsgn
        if cool_ac_setting.V_hs_dsgn > 0
        else _get_V_hs_dsgn_C(cool_ac_setting.type, cool_quantity.V_fan_rtd, cool_CRAC.q_rtd)
    )
    V_hs_dsgn_H = 0.0

    assert isinstance(V_hs_dsgn_H, float), "V_hs_dsgn_Hの型が不正"
    injector.binder.bind(jjj_dc.VHS_DSGN_H, to=V_hs_dsgn_H)
    assert isinstance(V_hs_dsgn_C, float), "V_hs_dsgn_Cの型が不正"
    injector.binder.bind(jjj_dc.VHS_DSGN_C, to=V_hs_dsgn_C)
    return V_hs_dsgn_H, V_hs_dsgn_C
def _get_cooling_fan_model(cool_ac_setting, V_hs_dsgn_C, cool_denchu_catalog, cool_real_inner, case_name):
    simu_R_C = None
    if cool_ac_setting.type == 計算モデル.電中研モデル:
        R2, R1, R0, P_rac_fan_rtd_C = jjjexperiment.denchu.denchu_1.calc_R_and_Pc_C(cool_denchu_catalog)
        P_rac_fan_rtd_C = 1000 * P_rac_fan_rtd_C
        simu_R_C = jjjexperiment.denchu.denchu_2.simu_R(R2, R1, R0)
        df_denchu_consts = jjjexperiment.denchu.denchu_1.get_DataFrame_denchu_modeling_consts(
            cool_denchu_catalog, R2, R1, R0, cool_real_inner, P_rac_fan_rtd_C
        )
        df_denchu_consts.to_csv(
            case_name + jjj_consts.version_info() + '_denchu_consts_C_output.csv',
            encoding='cp932',
        )
    else:
        P_rac_fan_rtd_C = V_hs_dsgn_C * cool_ac_setting.f_SFP
    _logger.info(f"P_rac_fan_rtd_C [W]: {P_rac_fan_rtd_C}")
    return P_rac_fan_rtd_C, simu_R_C
def _run_cooling_calc_Q_UT_A(injector, cool_ac_setting, region):
    E_UT_C_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, X_hs_out_d_t, X_hs_in_d_t, V_hs_supply_d_t, V_hs_vent_d_t = (
        injector.call_with_injection(jjj_dc.calc_Q_UT_A)
    )
    _logger.NDdebug("V_hs_supply_d_t", V_hs_supply_d_t)
    _logger.NDdebug("V_hs_vent_d_t", V_hs_vent_d_t)
    q_hs_CS_d_t, q_hs_CL_d_t = dc_a.get_q_hs_C_d_t(
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        X_hs_out_d_t,
        X_hs_in_d_t,
        V_hs_supply_d_t,
        region,
    )
    q_hs_C_d_t = q_hs_CS_d_t + q_hs_CL_d_t
    return (
        E_UT_C_d_t,
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        X_hs_out_d_t,
        X_hs_in_d_t,
        V_hs_supply_d_t,
        V_hs_vent_d_t,
        q_hs_CS_d_t,
        q_hs_CL_d_t,
        q_hs_C_d_t,
    )
def _get_latent_cooling_fan_power(cool_ac_setting, V_hs_vent_d_t, q_hs_C_d_t):
    print(cool_ac_setting.type)
    import jjjexperiment.latent_load.fan_power as latent_fan_power
    return latent_fan_power.get_E_E_fan_C_d_t(
        V_hs_vent_d_t, q_hs_C_d_t, cool_ac_setting.f_SFP
    )
def _get_standard_cooling_fan_power(cool_ac_setting, cool_quantity, P_rac_fan_rtd_C, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_C, q_hs_C_d_t, region):
    print(最低風量直接入力.入力しない)
    P_fan_rtd = (
        P_rac_fan_rtd_C
        if cool_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else cool_quantity.P_fan_rtd
    )
    return dc_a.get_E_E_fan_C_d_t(
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_C,
        q_hs_C_d_t,
        region,
        cool_ac_setting.f_SFP,
        cool_ac_setting.subtract_ventilation_power,
    )
def _get_minimum_volume_cooling_fan_power(cool_ac_setting, cool_quantity, P_rac_fan_rtd_C, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_C, q_hs_C_d_t, region):
    print(最低電力直接入力.入力しない)
    P_fan_rtd = (
        P_rac_fan_rtd_C
        if cool_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else cool_quantity.P_fan_rtd
    )
    return dc_a.get_E_E_fan_C_d_t(
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_C,
        q_hs_C_d_t,
        region,
        cool_ac_setting.f_SFP,
        ファン消費電力から換気分を引く.換気分を引かない,
    )
def _get_minimum_power_cooling_fan(cool_ac_setting, cool_quantity, v_min_cooling_input, P_rac_fan_rtd_C, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_C, region):
    print(最低電力直接入力.入力する)
    P_fan_rtd = (
        P_rac_fan_rtd_C
        if cool_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
        else cool_quantity.P_fan_rtd
    )
    from jjjexperiment.v_min_input.fan_power import get_E_E_fan_d_t
    return get_E_E_fan_d_t(*_MinimumFanElectricityInputs(
        v_min_cooling_input.E_E_fan_logic,
        P_fan_rtd,
        V_hs_vent_d_t,
        V_hs_supply_d_t,
        V_hs_dsgn_C,
        v_min_cooling_input.E_E_fan_min,
        region,
        True,
    ))
def _raise_invalid_cooling_fan_input():
    raise ValueError

def _get_cooling_electricity_type1_and_type3(cool_ac_setting, house, E_E_fan_C_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, climate, V_hs_supply_d_t, X_hs_out_d_t, X_hs_in_d_t, cool_quantity):
    return jjj_dc_a.calc_E_E_C_d_t_type1_and_type3(
        *_CoolingType1And3ElectricityInputs(
            cool_ac_setting.type,
            house.region,
            E_E_fan_C_d_t,
            Theta_hs_out_d_t,
            Theta_hs_in_d_t,
            climate.get_Theta_ex_d_t(),
            V_hs_supply_d_t,
            X_hs_out_d_t,
            X_hs_in_d_t,
            cool_quantity.q_hs_min,
            cool_quantity.q_hs_mid,
            cool_quantity.P_hs_mid,
            cool_quantity.V_fan_mid,
            cool_quantity.P_fan_mid,
            cool_quantity.q_hs_rtd,
            cool_quantity.P_fan_rtd,
            cool_quantity.V_fan_rtd,
            cool_quantity.P_hs_rtd,
            cool_ac_setting.equipment_spec,
        )
    )
def _get_cooling_electricity_type2(cool_ac_setting, house, climateFile, E_E_fan_C_d_t, q_hs_CS_d_t, q_hs_CL_d_t, cool_CRAC):
    return jjj_dc_a.calc_E_E_C_d_t_type2(
        *_CoolingType2ElectricityInputs(
            cool_ac_setting.type,
            house.region,
            climateFile,
            E_E_fan_C_d_t,
            q_hs_CS_d_t,
            q_hs_CL_d_t,
            cool_CRAC.e_rtd,
            cool_CRAC.q_rtd,
            cool_CRAC.q_max,
            cool_CRAC.input_C_af,
            cool_CRAC.dualcompressor,
        )
    )
def _get_cooling_electricity_type4(case_name, cool_ac_setting, house, climateFile, E_E_fan_C_d_t, q_hs_CS_d_t, q_hs_CL_d_t, V_hs_supply_d_t, P_rac_fan_rtd_C, simu_R_C, cool_denchu_catalog, cool_real_inner):
    return jjj_dc_a.calc_E_E_C_d_t_type4(
        *_CoolingType4ElectricityInputs(
            case_name,
            cool_ac_setting.type,
            house.region,
            climateFile,
            E_E_fan_C_d_t,
            q_hs_CS_d_t + q_hs_CL_d_t,
            V_hs_supply_d_t,
            P_rac_fan_rtd_C,
            simu_R_C,
            cool_denchu_catalog,
            cool_real_inner,
        )
    )
def _summarize_primary_energy(E_E_H_d_t, E_UT_H_d_t, E_E_C_d_t, E_UT_C_d_t):
    f_prim = get_f_prim()
    E_H_d_t = E_E_H_d_t * f_prim / 1000 + E_UT_H_d_t
    E_C_d_t = E_E_C_d_t * f_prim / 1000 + E_UT_C_d_t
    E_H = np.sum(E_H_d_t)
    E_C = np.sum(E_C_d_t)

    _logger.info(f"E_H [MJ/year]: {E_H}")
    _logger.info(f"E_C [MJ/year]: {E_C}")
    print('E_H [MJ/year]: ', E_H, ', E_C [MJ/year]: ', E_C)
    return E_H_d_t, E_C_d_t, E_H, E_C
def _write_outputs_and_build_test_result(case_name, df_output2, climate, test_mode, cool_CRAC, heat_CRAC, E_C, E_H, E_H_d_t, E_C_d_t, E_E_H_d_t, E_E_C_d_t, E_UT_H_d_t, E_UT_C_d_t, L_H_d_t, L_CS_d_t, L_CL_d_t, E_E_fan_H_d_t, E_E_fan_C_d_t, q_hs_H_d_t, q_hs_CS_d_t, q_hs_CL_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, V_hs_supply_d_t, V_hs_vent_d_t):
    df_output1 = pd.DataFrame(index=['合計値'])
    df_output1['E_H [MJ/year]'] = E_H
    df_output1['E_C [MJ/year]'] = E_C
    df_output1.to_csv(
        case_name + jjj_consts.version_info() + '_output1.csv',
        encoding='cp932',
    )

    df_output2['Theta_hs_C_out_d_t [℃]'] = Theta_hs_out_d_t
    df_output2['Theta_hs_C_in_d_t [℃]'] = Theta_hs_in_d_t
    df_output2['Theta_ex_d_t [℃]'] = climate.get_Theta_ex_d_t()
    df_output2['V_hs_supply_C_d_t [m3/h]'] = V_hs_supply_d_t
    df_output2['V_hs_vent_C_d_t [m3/h]'] = V_hs_vent_d_t
    df_output2['E_H_d_t [MJ/h]'] = E_H_d_t
    df_output2['E_C_d_t [MJ/h]'] = E_C_d_t
    df_output2['E_E_H_d_t [kWh/h]'] = E_E_H_d_t
    df_output2['E_E_C_d_t [kWh/h]'] = E_E_C_d_t
    df_output2['E_UT_H_d_t [MJ/h]'] = E_UT_H_d_t
    df_output2['E_UT_C_d_t [MJ/h]'] = E_UT_C_d_t
    df_output2['L_H_d_t [MJ/h]'] = L_H_d_t
    df_output2['L_CS_d_t [MJ/h]'] = L_CS_d_t
    df_output2['L_CL_d_t [MJ/h]'] = L_CL_d_t
    df_output2['E_E_fan_H_d_t [kWh/h]'] = E_E_fan_H_d_t
    df_output2['E_E_fan_C_d_t [kWh/h]'] = E_E_fan_C_d_t
    df_output2['q_hs_H_d_t [Wh/h]'] = q_hs_H_d_t
    df_output2['q_hs_CS_d_t [Wh/h]'] = q_hs_CS_d_t
    df_output2['q_hs_CL_d_t [Wh/h]'] = q_hs_CL_d_t
    df_output2.to_csv(
        case_name + jjj_consts.version_info() + '_output2.csv',
        encoding='cp932',
    )

    if test_mode:
        i = SutValues(
            cool_CRAC.q_rtd,
            heat_CRAC.q_rtd,
            cool_CRAC.q_max,
            heat_CRAC.q_max,
            cool_CRAC.e_rtd,
            heat_CRAC.e_rtd,
        )
        r = ResultSummary(E_C, E_H)
        return {'TInput': i, 'TValue': r}
    return None
def _raise_invalid_heating_fan_input():
    raise ValueError

@inject
def calc_main(
    injector: Injector,
    # NOTE: 型解決するだけなら下記のみで充分だが、文脈の追加変更を行うため injector 自身も受取
    test_mode: jjj_ipt_di.TestMode,
    case_name: jjj_ipt_di.CaseName,
    climateFile: jjj_ipt_di.ClimateFile,
    loadFile: jjj_ipt_di.LoadFile,
    v_min_heating_input: jjj_V_min_input.inputs.heating.InputMinVolumeInput,
    v_min_cooling_input: jjj_V_min_input.inputs.cooling.InputMinVolumeInput,
    house: HouseInfo,
    skin: OuterSkin,
    hex: HEX,
    ufac: jjj_ufac_ipt.common.UnderfloorAc,
    heat_ac_setting: HeatingAcSetting,
    cool_ac_setting: CoolingAcSetting,
    heat_CRAC: HeatCRACSpec,
    cool_CRAC: CoolCRACSpec,
    heat_denchu_catalog: jjj_denchu_heat_ipt.DenchuCatalogSpecification,
    cool_denchu_catalog: jjj_denchu_cool_ipt.DenchuCatalogSpecification,
    heat_real_inner: jjj_denchu_heat_ipt.RealInnerCondition,
    cool_real_inner: jjj_denchu_cool_ipt.RealInnerCondition
    ) -> dict | None:
    _log_equipment_specs(cool_CRAC, heat_CRAC)

    # ドメインサービス
    climate, heat_quantity, cool_quantity = _create_domain_services(house, ufac, climateFile, heat_ac_setting, cool_ac_setting)

    spec_MR, spec_OR, mode_MR, mode_OR = _get_virtual_heating_devices_and_modes(house.region)

    ##### 暖房負荷の取得（MJ/h）
    L_H_d_t_i: np.ndarray
    """暖房負荷 [MJ/h]"""

    with jjj_common.injector_context(injector):  # ネスト内からの利用に備える
        # L_dash_H_R_d_t_i, L_dash_CS_R_d_t_iは負荷ファイルから読み取れないため自動計算する。
        # 読み込んだ負荷と整合性が取れないため、正しい実装ではない。
        L_H_d_t_i, L_dash_H_R_d_t_i, L_dash_CS_R_d_t_i = _calc_standard_heating_load(house, skin, hex, heat_ac_setting, cool_ac_setting, spec_MR, spec_OR, mode_MR, mode_OR)
        L_H_d_t_i = _override_heating_load_from_csv(L_H_d_t_i, loadFile)

        ##### 冷房負荷の取得（MJ/h）
        L_CS_d_t_i: np.ndarray
        """冷房顕熱負荷 [MJ/h]"""
        L_CL_d_t_i: np.ndarray
        """冷房潜熱負荷 [MJ/h]"""

        if loadFile == '-':
            L_CS_d_t_i, L_CL_d_t_i = _calc_standard_cooling_load(house, skin, hex, cool_ac_setting, heat_ac_setting, mode_MR, mode_OR)
        else:
            L_CS_d_t_i, L_CL_d_t_i = _load_cooling_load_from_csv(loadFile)

    # 負荷をあつめたデータクラス
    _bind_load_dti(injector, L_H_d_t_i, L_CS_d_t_i, L_CL_d_t_i, L_dash_H_R_d_t_i, L_dash_CS_R_d_t_i)

    # NOTE: 出力用の下記が計算できるのは、負荷が上書きされない前提
    L_H_d_t, L_CS_d_t, L_CL_d_t = _sum_zone_loads(L_H_d_t_i, L_CS_d_t_i, L_CL_d_t_i)

    ##### 暖房消費電力の計算（kWh/h）
    print("暖房消費電力の計算")

    def arr_summary(arr: np.ndarray):
        return {
            "MAX  ": max(arr),
            "ZEROS": arr.size - np.count_nonzero(arr),
            "AVG  ": np.average(arr[np.nonzero(arr)])
        }

    V_hs_dsgn_H, V_hs_dsgn_C = _bind_heating_design_airflows(injector, heat_ac_setting, heat_quantity, heat_CRAC)

    E_UT_H_d_t, Theta_hs_out_d_t, Theta_hs_in_d_t, V_hs_supply_d_t, V_hs_vent_d_t = _run_heating_calc_Q_UT_A(injector, heat_ac_setting)

    P_rac_fan_rtd_H, simu_R_H = _get_heating_fan_model(heat_ac_setting, V_hs_dsgn_H, heat_denchu_catalog, heat_real_inner, case_name)

    # (3) 日付dの時刻tにおける1時間当たりの熱源機の平均暖房能力(W)
    q_hs_H_d_t, HCM = _get_heating_capacity_and_HCM(Theta_hs_out_d_t, Theta_hs_in_d_t, V_hs_supply_d_t, climate, house.region)

    E_E_fan_H_d_t: Array8760
    # NOTE: 潜熱評価モデルはベース式が異なるため 最低風量・最低電力 直接入力ロジック反映から除外する
    if heat_ac_setting.type == 計算モデル.RAC活用型全館空調_潜熱評価モデル:
        E_E_fan_H_d_t = _get_latent_heating_fan_power(heat_ac_setting, V_hs_vent_d_t, q_hs_H_d_t)

    elif heat_ac_setting.type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        計算モデル.電中研モデル
    ]:
        print(heat_ac_setting.type)

        # [F25-01] 最低風量・最低電力 直接入力
        match v_min_heating_input.input_V_hs_min:
            case 最低風量直接入力.入力しない:
                E_E_fan_H_d_t = _get_standard_heating_fan_power(heat_ac_setting, heat_quantity, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, q_hs_H_d_t, house.region)

            case 最低風量直接入力.入力する:
                print(最低風量直接入力.入力する)

                match v_min_heating_input.input_E_E_fan_min:
                    case 最低電力直接入力.入力しない:
                        E_E_fan_H_d_t = _get_minimum_volume_heating_fan_power(heat_ac_setting, heat_quantity, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, q_hs_H_d_t, house.region)

                    case 最低電力直接入力.入力する:
                        E_E_fan_H_d_t = _get_minimum_power_heating_fan(heat_ac_setting, heat_quantity, v_min_heating_input, P_rac_fan_rtd_H, V_hs_vent_d_t, V_hs_supply_d_t, V_hs_dsgn_H, house.region)
                    case _:
                        _raise_invalid_heating_fan_input()
            case _:
                _raise_invalid_heating_fan_input()
    else:
        _raise_invalid_heating_fan_input()

    E_E_H_d_t: np.ndarray
    """日付dの時刻tにおける1時間当たり 暖房時の消費電力量 [kWh/h]"""

    if heat_ac_setting.type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_潜熱評価モデル
    ]:
        E_E_H_d_t = _get_heating_electricity_type1_and_type3(
            heat_ac_setting,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            Theta_hs_out_d_t,
            Theta_hs_in_d_t,
            climate,
            V_hs_supply_d_t,
            cool_quantity,
            heat_quantity,
        )
    elif heat_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル:
        E_E_H_d_t = _get_heating_electricity_type2(
            heat_ac_setting,
            house,
            climateFile,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            heat_CRAC,
            cool_CRAC,
        )
    elif heat_ac_setting.type == 計算モデル.電中研モデル:
        E_E_H_d_t = _get_heating_electricity_type4(
            case_name,
            heat_ac_setting,
            house,
            climateFile,
            E_E_fan_H_d_t,
            q_hs_H_d_t,
            V_hs_supply_d_t,
            P_rac_fan_rtd_H,
            simu_R_H,
            heat_denchu_catalog,
            heat_real_inner,
        )
    else:
        raise Exception("暖房方式が不正です。")

    df_output2 = _build_heating_output_dataframe(
        E_UT_H_d_t,
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        climate,
        V_hs_supply_d_t,
        V_hs_vent_d_t,
    )
    ##### 冷房消費電力の計算（kWh/h）
    print("冷房消費電力の計算")

    V_hs_dsgn_H, V_hs_dsgn_C = _bind_cooling_design_airflows(
        injector,
        cool_ac_setting,
        cool_quantity,
        cool_CRAC,
    )
    injector.binder.bind(jjj_dc.ActiveAcSetting, to=cool_ac_setting)
    P_rac_fan_rtd_C, simu_R_C = _get_cooling_fan_model(
        cool_ac_setting,
        V_hs_dsgn_C,
        cool_denchu_catalog,
        cool_real_inner,
        case_name,
    )
    (
        E_UT_C_d_t,
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        X_hs_out_d_t,
        X_hs_in_d_t,
        V_hs_supply_d_t,
        V_hs_vent_d_t,
        q_hs_CS_d_t,
        q_hs_CL_d_t,
        q_hs_C_d_t,
    ) = _run_cooling_calc_Q_UT_A(injector, cool_ac_setting, house.region)
    if cool_ac_setting.type == 計算モデル.RAC活用型全館空調_潜熱評価モデル:
        E_E_fan_C_d_t = _get_latent_cooling_fan_power(
            cool_ac_setting, V_hs_vent_d_t, q_hs_C_d_t
        )
    elif cool_ac_setting.type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        計算モデル.電中研モデル
    ]:
        print(cool_ac_setting.type)

        # [F25-01] 最低風量・最低電力 直接入力
        match v_min_cooling_input.input_V_hs_min:
            case 最低風量直接入力.入力しない:
                E_E_fan_C_d_t = _get_standard_cooling_fan_power(
                    cool_ac_setting,
                    cool_quantity,
                    P_rac_fan_rtd_C,
                    V_hs_vent_d_t,
                    V_hs_supply_d_t,
                    V_hs_dsgn_C,
                    q_hs_C_d_t,
                    house.region,
                )
            case 最低風量直接入力.入力する:
                print(最低風量直接入力.入力する)

                match v_min_cooling_input.input_E_E_fan_min:
                    case 最低電力直接入力.入力しない:
                        E_E_fan_C_d_t = _get_minimum_volume_cooling_fan_power(
                            cool_ac_setting,
                            cool_quantity,
                            P_rac_fan_rtd_C,
                            V_hs_vent_d_t,
                            V_hs_supply_d_t,
                            V_hs_dsgn_C,
                            q_hs_C_d_t,
                            house.region,
                        )
                    case 最低電力直接入力.入力する:
                        E_E_fan_C_d_t = _get_minimum_power_cooling_fan(
                            cool_ac_setting,
                            cool_quantity,
                            v_min_cooling_input,
                            P_rac_fan_rtd_C,
                            V_hs_vent_d_t,
                            V_hs_supply_d_t,
                            V_hs_dsgn_C,
                            house.region,
                        )
                    case _:
                        _raise_invalid_cooling_fan_input()
            case _:
                _raise_invalid_cooling_fan_input()
    else:
        _raise_invalid_cooling_fan_input()

    E_E_C_d_t: np.ndarray
    """日付dの時刻tにおける1時間当たりの冷房時の消費電力量(kWh/h)"""

    if cool_ac_setting.type in [
        計算モデル.ダクト式セントラル空調機,
        計算モデル.RAC活用型全館空調_潜熱評価モデル
    ]:
        E_E_C_d_t = _get_cooling_electricity_type1_and_type3(
            cool_ac_setting,
            house,
            E_E_fan_C_d_t,
            Theta_hs_out_d_t,
            Theta_hs_in_d_t,
            climate,
            V_hs_supply_d_t,
            X_hs_out_d_t,
            X_hs_in_d_t,
            cool_quantity,
        )
    elif cool_ac_setting.type == 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル:
        E_E_C_d_t = _get_cooling_electricity_type2(
            cool_ac_setting,
            house,
            climateFile,
            E_E_fan_C_d_t,
            q_hs_CS_d_t,
            q_hs_CL_d_t,
            cool_CRAC,
        )
    elif cool_ac_setting.type == 計算モデル.電中研モデル:
        E_E_C_d_t = _get_cooling_electricity_type4(
            case_name,
            cool_ac_setting,
            house,
            climateFile,
            E_E_fan_C_d_t,
            q_hs_CS_d_t,
            q_hs_CL_d_t,
            V_hs_supply_d_t,
            P_rac_fan_rtd_C,
            simu_R_C,
            cool_denchu_catalog,
            cool_real_inner,
        )
    else:
        raise Exception("冷房方式が不正です。")

    ##### 計算結果のまとめ

    E_H_d_t, E_C_d_t, E_H, E_C = _summarize_primary_energy(
        E_E_H_d_t,
        E_UT_H_d_t,
        E_E_C_d_t,
        E_UT_C_d_t,
    )
    return _write_outputs_and_build_test_result(
        case_name,
        df_output2,
        climate,
        test_mode,
        cool_CRAC,
        heat_CRAC,
        E_C,
        E_H,
        E_H_d_t,
        E_C_d_t,
        E_E_H_d_t,
        E_E_C_d_t,
        E_UT_H_d_t,
        E_UT_C_d_t,
        L_H_d_t,
        L_CS_d_t,
        L_CL_d_t,
        E_E_fan_H_d_t,
        E_E_fan_C_d_t,
        q_hs_H_d_t,
        q_hs_CS_d_t,
        q_hs_CL_d_t,
        Theta_hs_out_d_t,
        Theta_hs_in_d_t,
        V_hs_supply_d_t,
        V_hs_vent_d_t,
    )
