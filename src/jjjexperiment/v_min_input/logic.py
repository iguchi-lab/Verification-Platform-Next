import numpy as np
# JJJ
from jjjexperiment.common import *


def normalize_V_vent_g_i(
        V_vent_g_i: np.ndarray,
        V_hs_min: float
    ) -> np.ndarray:
    """暖冷房区画iごとの全般換気量の比率を維持したまま、合計を最低風量に調整する。

    Args:
        V_vent_g_i: 正規化前の全般換気量 [m3/h]
        V_hs_min: 最低風量 [m3/h]

    Returns:
        正規化された全般換気量 [m3/h]
    """

    """事前条件"""
    assert isinstance(V_vent_g_i, np.ndarray) and V_vent_g_i.shape in [(5,), (5, 1)]  \
        , f"配列の形状が想定外: type={type(V_vent_g_i)}, shape={getattr(V_vent_g_i, 'shape', 'N/A')}"
    assert np.all(V_vent_g_i >= 0)  \
        , "全般換気量は非負値である必要があります"
    assert V_hs_min > 0  \
        , "最低風量は正の値である必要があります"
    total = V_vent_g_i.sum()
    assert total > 0  \
        , f"全般換気量の合計が0です: {V_vent_g_i}"

    # 計算実行
    result = V_hs_min * V_vent_g_i / total

    """事後条件"""
    assert result.shape == V_vent_g_i.shape  \
        , f"配列の形状が変わっています: 入力={V_vent_g_i.shape}, 出力={result.shape}"

    return result
