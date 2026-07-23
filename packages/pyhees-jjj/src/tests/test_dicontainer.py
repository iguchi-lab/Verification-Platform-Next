import pytest
from injector import Injector
from jjjexperiment.underfloor_ac.inputs.common import UfVarsDataFrame

from jjjexperiment.inputs.common import OuterSkin
from jjjexperiment.inputs.di_container import JJJExperimentModule
from jjjexperiment.inputs.options import 床下空調ロジック, 過剰熱量繰越計算


def _underfloor_inputs(**updates):
    inputs = {
        "r_A_ufvnt": 0,
        "change_underfloor_temperature": 床下空調ロジック.変更しない.value,
        "carry_over_heat": 過剰熱量繰越計算.行わない.value,
    }
    inputs.update(updates)
    return inputs


def test_removed_legacy_underfloor_input_fails_immediately():
    with pytest.raises(
        ValueError,
        match="underfloor_air_conditioning_air_supply=2 の旧床下空調計算は削除",
    ):
        JJJExperimentModule(_underfloor_inputs(
            underfloor_air_conditioning_air_supply=2))


def test_disabled_legacy_underfloor_tombstone_remains_accepted():
    module = JJJExperimentModule(_underfloor_inputs(
        underfloor_air_conditioning_air_supply=1))

    assert module._input["underfloor_air_conditioning_air_supply"] == 1


def test_new_underfloor_input_sets_only_new_underfloor_state():
    module = JJJExperimentModule(_underfloor_inputs(
        change_underfloor_temperature=床下空調ロジック.変更する.value))

    assert module._input["r_A_ufac"] == 100.0
    assert "underfloor_air_conditioning_air_supply" not in module._input
    skin = OuterSkin.from_dict(module._input)
    assert skin.r_A_ufac == 1.0
    assert skin.r_A_ufvnt == 0.0
    assert skin.underfloor_insulation is True


def test_new_underfloor_and_carryover_fail_instead_of_falling_back():
    with pytest.raises(ValueError, match="新床下空調と過剰熱量繰越計算は同時に使用できません"):
        JJJExperimentModule(_underfloor_inputs(
            change_underfloor_temperature=床下空調ロジック.変更する.value,
            carry_over_heat=過剰熱量繰越計算.行う.value,
        ))


# NOTE: DIコンテナライブラリ Injector 導入の目的:
# 現時点では、出力用データフレームの操作のみ、行っているが、
# 将来的には、建研さまロジックのカスタマイズによる
# 引数・返り値のいくつもの追加を解消するため

class Test_DIコンテナ:

    @pytest.mark.skip(reason="本ロジックとは無関係のため")
    def test_Injector(self):
        """ DIコンテナの挙動テスト """
        di = Injector(JJJExperimentModule())
        df_holder = di.get(UfVarsDataFrame)
        df_holder.update_df({'x':[1,2,3], 'y':[2,3,4]})
        df_holder.export_to_csv("di_test.csv")
