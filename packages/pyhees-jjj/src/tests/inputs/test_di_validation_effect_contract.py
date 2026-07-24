from copy import deepcopy

import pytest

from jjjexperiment.inputs.di_container import JJJExperimentModule
from jjjexperiment.inputs.options import (
    ファン消費電力から換気分を引く,
    床下空調ロジック,
    最低風量直接入力,
    過剰熱量繰越計算,
)


def _inputs(**updates):
    data = {
        "r_A_ufvnt": 25.0,
        "change_underfloor_temperature": 床下空調ロジック.変更しない.value,
        "carry_over_heat": 過剰熱量繰越計算.行わない.value,
    }
    data.update(updates)
    return data


def test_disabled_underfloor_copies_ratio_then_logs(capsys):
    data = _inputs(r_A_ufvnt="35")

    module = JJJExperimentModule(data)

    assert module._input["r_A_ufac"] == "35"
    assert capsys.readouterr().out == "床下空調を使用しない\n"


def test_new_underfloor_updates_ratio_and_preserves_log_order(capsys):
    data = _inputs(
        change_underfloor_temperature=床下空調ロジック.変更する.value
    )

    module = JJJExperimentModule(data)

    assert module._input["r_A_ufac"] == 100.0
    assert capsys.readouterr().out == (
        "新・床下空調ロジックを使用\n"
        "r_A_ufac = 100.0 [%]\n"
        "空調空気を床下を通して給気する\n"
    )


def test_minimum_airflow_updates_heating_then_cooling_and_logs_in_order(capsys):
    data = _inputs(
        H_A={"input_V_hs_min": 最低風量直接入力.入力する.value},
        C_A={"input_V_hs_min": 最低風量直接入力.入力する.value},
    )

    module = JJJExperimentModule(data)

    expected = ファン消費電力から換気分を引く.換気分を引かない.value
    assert module._input["H_A"]["subtract_ventilation_power"] == expected
    assert module._input["C_A"]["subtract_ventilation_power"] == expected
    assert capsys.readouterr().out == (
        "床下空調を使用しない\n"
        "H_A: subtract_ventilation_power を強制オフ (最低風量直接入力有効)\n"
        "C_A: subtract_ventilation_power を強制オフ (最低風量直接入力有効)\n"
    )


def test_carryover_log_remains_last(capsys):
    JJJExperimentModule(
        _inputs(carry_over_heat=過剰熱量繰越計算.行う.value)
    )

    assert capsys.readouterr().out == (
        "床下空調を使用しない\n"
        "過剰熱量繰越を行う\n"
    )


def test_removed_underfloor_error_precedes_logs_and_mutation(capsys):
    data = _inputs(underfloor_air_conditioning_air_supply=2)
    before = deepcopy(data)

    with pytest.raises(ValueError, match="旧床下空調計算は削除"):
        JJJExperimentModule(data)

    assert data == before
    assert capsys.readouterr().out == ""


def test_feature_conflict_error_precedes_logs_and_mutation(capsys):
    data = _inputs(
        change_underfloor_temperature=床下空調ロジック.変更する.value,
        carry_over_heat=過剰熱量繰越計算.行う.value,
    )
    before = deepcopy(data)

    with pytest.raises(
        ValueError, match="新床下空調と過剰熱量繰越計算は同時に使用できません"
    ):
        JJJExperimentModule(data)

    assert data == before
    assert capsys.readouterr().out == ""


def test_missing_underfloor_ratio_logs_before_key_error(capsys):
    data = _inputs()
    del data["r_A_ufvnt"]

    with pytest.raises(KeyError, match="r_A_ufvnt が設定されていません"):
        JJJExperimentModule(data)

    assert "r_A_ufac" not in data
    assert capsys.readouterr().out == "床下空調を使用しない\n"


def test_disabled_minimum_airflow_preserves_existing_subtraction(capsys):
    data = _inputs(
        H_A={
            "input_V_hs_min": 最低風量直接入力.入力しない.value,
            "subtract_ventilation_power": 99,
        }
    )

    module = JJJExperimentModule(data)

    assert module._input["H_A"]["subtract_ventilation_power"] == 99
    assert capsys.readouterr().out == "床下空調を使用しない\n"


def test_invalid_minimum_airflow_occurs_after_underfloor_update(capsys):
    data = _inputs(H_A={"input_V_hs_min": 99})

    with pytest.raises(ValueError, match="99 is not a valid"):
        JJJExperimentModule(data)

    assert data["r_A_ufac"] == data["r_A_ufvnt"]
    assert "subtract_ventilation_power" not in data["H_A"]
    assert capsys.readouterr().out == "床下空調を使用しない\n"
