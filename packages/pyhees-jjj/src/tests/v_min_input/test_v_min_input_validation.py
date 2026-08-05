import math

import pytest

from jjjexperiment.inputs.ac_setting import HeatingAcSetting
from jjjexperiment.inputs.options import 最低電力直接入力, 最低風量直接入力
from jjjexperiment.v_min_input.inputs.heating import InputMinVolumeInput
from jjjexperiment.v_min_input.validation import (
    validate_minimum_airflow_relation,
    validate_minimum_fan_power_relation,
)


@pytest.mark.parametrize("value", (0, -1, math.inf, math.nan))
def test_minimum_airflow_input_rejects_nonpositive_or_nonfinite_values(value):
    with pytest.raises(ValueError, match="正の有限値"):
        InputMinVolumeInput.from_dict(
            {
                "input_V_hs_min": 最低風量直接入力.入力する.value,
                "V_hs_min": value,
            }
        )


@pytest.mark.parametrize("value", (-1, math.inf, math.nan))
def test_minimum_fan_power_input_rejects_negative_or_nonfinite_values(value):
    with pytest.raises(ValueError, match="0以上の有限値"):
        InputMinVolumeInput.from_dict(
            {
                "input_V_hs_min": 最低風量直接入力.入力する.value,
                "V_hs_min": 160,
                "input_E_E_fan_min": 最低電力直接入力.入力する.value,
                "E_E_fan_min": value,
                "E_E_fan_logic": 1,
            }
        )


def test_direct_design_airflow_rejects_nonpositive_value():
    with pytest.raises(ValueError, match="V_hs_dsgn は正の有限値"):
        HeatingAcSetting.from_dict(
            {"input_V_hs_dsgn": 2, "V_hs_dsgn": 0}
        )


def test_minimum_airflow_must_not_exceed_design_airflow():
    with pytest.raises(ValueError, match="V_hs_dsgn .* 以下"):
        validate_minimum_airflow_relation(1200.0, 500.0, "暖房")


def test_minimum_fan_power_must_not_exceed_rated_power():
    with pytest.raises(ValueError, match="P_fan_rtd .* 以下"):
        validate_minimum_fan_power_relation(301.0, 300.0, "冷房")
