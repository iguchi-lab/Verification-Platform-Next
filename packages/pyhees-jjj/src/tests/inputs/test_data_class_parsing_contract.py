import pytest

from jjjexperiment.inputs.ac_setting import CoolingAcSetting, HeatingAcSetting
from jjjexperiment.inputs.common import HEX, HouseInfo, OuterSkin
from jjjexperiment.inputs.cooling import CRACSpecification as CoolingCRACSpecification
from jjjexperiment.inputs.heating import CRACSpecification as HeatingCRACSpecification
from jjjexperiment.inputs.options import (
    ファン消費電力から換気分を引く,
    全般換気機能,
    暖房方式,
    機器仕様手動入力タイプ,
    計算モデル,
)


def test_ac_setting_parses_all_common_input_fields():
    data = {
        "type": "2",
        "input": "3",
        "VAV": "2",
        "general_ventilation": str(全般換気機能.なし.value),
        "duct_insulation": "2",
        "subtract_ventilation_power": "2",
        "input_f_SFP": 2,
        "f_SFP": "0.21",
        "input_V_hs_dsgn": "2",
        "V_hs_dsgn": "1234.5",
        "q_hs_rtd": "1001",
        "P_hs_rtd": "1002",
        "V_fan_rtd": "1003",
        "P_fan_rtd": "1004",
        "q_hs_mid": "1005",
        "P_hs_mid": "1006",
        "V_fan_mid": "1007",
        "P_fan_mid": "1008",
    }

    actual = HeatingAcSetting.from_dict(data)

    assert actual.mode is 暖房方式.住戸全体を連続的に暖房する方式
    assert actual.type is 計算モデル.RAC活用型全館空調_現行省エネ法RACモデル
    assert actual.input_mode is 機器仕様手動入力タイプ.定格能力試験と中間能力試験の値を入力する
    assert actual.equipment_spec == 機器仕様手動入力タイプ.定格能力試験と中間能力試験の値を入力する.name
    assert actual.VAV is True
    assert actual.general_ventilation is False
    assert actual.duct_insulation == "全て断熱区画内である"
    assert actual.subtract_ventilation_power is ファン消費電力から換気分を引く.換気分を引かない
    assert actual.f_SFP == 0.21
    assert actual.V_hs_dsgn == 1234.5
    assert (
        actual.q_hs_rtd_input,
        actual.P_hs_rtd_input,
        actual.V_fan_rtd_input,
        actual.P_fan_rtd_input,
        actual.q_hs_mid_input,
        actual.P_hs_mid_input,
        actual.V_fan_mid_input,
        actual.P_fan_mid_input,
    ) == (1001.0, 1002.0, 1003.0, 1004.0, 1005.0, 1006.0, 1007.0, 1008.0)


def test_ac_setting_preserves_defaults_and_gate_conversion_rules():
    actual = CoolingAcSetting.from_dict({
        "input_f_SFP": "2",
        "f_SFP": "9.9",
        "input_V_hs_dsgn": "2",
        "V_hs_dsgn": "876.5",
    })

    assert actual.type is 計算モデル.ダクト式セントラル空調機
    assert actual.input_mode is 機器仕様手動入力タイプ.入力しない
    assert actual.VAV is False
    assert actual.general_ventilation is True
    assert actual.f_SFP == pytest.approx(0.4 * 0.36)
    assert actual.V_hs_dsgn == 876.5
    assert actual.q_hs_rtd_input is None


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("全てもしくは一部が断熱区画外である", "全てもしくは一部が断熱区画外である"),
        (1, "全てもしくは一部が断熱区画外である"),
        (2, "全て断熱区画内である"),
    ),
)
def test_ac_setting_preserves_duct_insulation_inputs(value, expected):
    assert HeatingAcSetting.from_dict({"duct_insulation": value}).duct_insulation == expected


def test_ac_setting_preserves_textual_inside_duct_insulation_error():
    with pytest.raises(ValueError, match="invalid literal for int"):
        HeatingAcSetting.from_dict({"duct_insulation": "全て断熱区画内である"})

def test_ac_setting_preserves_invalid_duct_insulation_error():
    with pytest.raises(ValueError, match="ダクトが通過する空間の入力が不正です。"):
        HeatingAcSetting.from_dict({"duct_insulation": 3})


def test_house_info_parses_scalar_fields_and_preserves_defaults():
    actual = HouseInfo.from_dict({
        "A_A": "101.1",
        "A_MR": "22.2",
        "A_OR": "33.3",
        "region": "7",
        "sol_region": "4",
    })

    assert actual.A_A == 101.1
    assert actual.A_MR == 22.2
    assert actual.A_OR == 33.3
    assert actual.region == 7
    assert actual.sol_region is None
    assert HouseInfo.from_dict({}) == HouseInfo()


def test_outer_skin_parses_scalar_and_underfloor_fields():
    actual = OuterSkin.from_dict({
        "A_env": "250.5",
        "A_A": "100.2",
        "U_A": "0.61",
        "eta_A_H": "2.1",
        "eta_A_C": "3.2",
        "underfloor_ventilation": "2",
        "r_A_ufvnt": "35",
        "underfloor_insulation": "1",
        "change_underfloor_temperature": "2",
        "r_A_ufac": "75",
        "hs_CAV": "2",
    })

    assert actual.A_env == 250.5
    assert actual.A_A == 100.2
    assert actual.U_A == 0.61
    assert actual.eta_A_H == 2.1
    assert actual.eta_A_C == 3.2
    assert actual.r_A_ufvnt == 0.0
    assert actual.r_A_ufac == 0.75
    assert actual.underfloor_insulation is True
    assert actual.hs_CAV is True
    assert actual.r_env is not None
    assert actual.Q is not None
    assert actual.mu_H is not None
    assert actual.mu_C is not None


def test_hex_preserves_nested_input_contract_and_to_dict():
    actual = HEX.from_dict({"HEX": {"install": "2", "etr_t": "0.83"}})

    assert actual.to_dict() == {
        "hex": True,
        "etr_t": 0.83,
        "e_bal": 0.9,
        "e_leak": 1.0,
    }
    assert HEX.from_dict({}).to_dict() is None


@pytest.mark.parametrize(
    ("specification_type", "suffix"),
    ((2, "2"), (3, "3"), (4, "4")),
)
def test_heating_airflow_correction_uses_type_specific_keys(
    monkeypatch, specification_type, suffix
):
    import pyhees.section4_3_a as section4_3_a

    monkeypatch.setattr(section4_3_a, "get_q_rtd_H", lambda _q_rtd_C: 1000.0)
    monkeypatch.setattr(section4_3_a, "get_q_max_H", lambda _q_rtd, _q_max_C: 2000.0)
    monkeypatch.setattr(section4_3_a, "get_e_rtd_H", lambda _e_rtd_C: 3.0)
    data = {
        "type": specification_type,
        f"input_C_af_H{suffix}": "2",
        f"C_af_H{suffix}": "1.23",
        f"dedicated_chamber{suffix}": "2",
        f"fixed_fin_direction{suffix}": "2",
    }
    if specification_type == 2:
        data.update({
            "input_rac_performance": 2,
            "q_rac_rtd_H": 1000,
            "q_rac_max_H": 2000,
            "e_rac_rtd_H": 3,
        })
    elif specification_type == 4:
        data.update({"q_rac_pub_rtd": 1, "q_rac_pub_max": 2})

    actual = HeatingCRACSpecification.from_dict(data, 1000.0, 2000.0, 3.0)

    assert actual.input_C_af == {
        "input_mode": 2,
        "dedicated_chamber": True,
        "fixed_fin_direction": True,
        "C_af_H": 1.23,
    }


@pytest.mark.parametrize(
    ("specification_type", "suffix"),
    ((2, "2"), (3, "3"), (4, "4")),
)
def test_cooling_airflow_correction_uses_type_specific_keys(
    monkeypatch, specification_type, suffix
):
    import pyhees.section4_3_a as section4_3_a

    monkeypatch.setattr(section4_3_a, "get_q_rtd_C", lambda _A_A: 1000.0)
    monkeypatch.setattr(section4_3_a, "get_q_max_C", lambda _q_rtd: 2000.0)
    monkeypatch.setattr(section4_3_a, "get_e_rtd_C", lambda _e_class, _q_rtd: 3.0)
    data = {
        "type": specification_type,
        f"input_C_af_C{suffix}": "2",
        f"C_af_C{suffix}": "1.23",
        f"dedicated_chamber{suffix}": "2",
        f"fixed_fin_direction{suffix}": "2",
    }
    if specification_type == 2:
        data.update({
            "input_rac_performance": 2,
            "q_rac_rtd_C": 1000,
            "q_rac_max_C": 2000,
            "e_rac_rtd_C": 3,
        })
    elif specification_type == 4:
        data.update({"q_rac_pub_rtd": 1, "q_rac_pub_max": 2})

    actual = CoolingCRACSpecification.from_dict(data, 100.0)

    assert actual.input_C_af == {
        "input_mode": 2,
        "dedicated_chamber": True,
        "fixed_fin_direction": True,
        "C_af_C": 1.23,
    }


@pytest.mark.parametrize(
    ("specification", "args", "correction_key"),
    (
        (HeatingCRACSpecification, (1000.0, 2000.0, 3.0), "C_af_H"),
        (CoolingCRACSpecification, (100.0,), "C_af_C"),
    ),
)
def test_airflow_correction_preserves_defaults_for_duct_system(
    specification, args, correction_key
):
    actual = specification.from_dict({"type": 1}, *args)

    assert actual.input_C_af == {
        "input_mode": 2,
        "dedicated_chamber": False,
        "fixed_fin_direction": False,
        correction_key: 1.0,
    }
