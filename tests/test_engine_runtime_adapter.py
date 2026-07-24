from jjjexperiment.inputs import options
from pyhees import jjj_runtime


def test_cross_boundary_enums_are_reexported_without_copying():
    assert options.計算モデル is jjj_runtime.計算モデル
    assert options.床下空調ロジック is jjj_runtime.床下空調ロジック
    assert (
        options.ファン消費電力から換気分を引く
        is jjj_runtime.ファン消費電力から換気分を引く
    )


def test_cross_boundary_enum_values_remain_stable():
    assert {member.value for member in options.計算モデル} == {1, 2, 3, 4}
    assert {member.value for member in options.床下空調ロジック} == {1, 2}
    assert {
        member.value for member in options.ファン消費電力から換気分を引く
    } == {1, 2}
