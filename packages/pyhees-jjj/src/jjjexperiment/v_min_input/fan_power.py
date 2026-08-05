import numpy as np

# JJJ
from jjjexperiment.common import Array8760, jjj_cloning
from jjjexperiment.inputs.options import ファン消費電力算定方法
from pyhees.section4_2 import get_season_array_d_t


# ============================================================================
# A.6 送風機
# ============================================================================

@jjj_cloning
def get_E_E_fan_d_t(
        E_E_fan_logic: ファン消費電力算定方法,
        P_fan_rtd: float,
        V_hs_vent_d_t: Array8760,
        V_hs_supply_d_t: Array8760,
        V_hs_dsgn: float,
        E_E_fan_min: float,
        region: int,
        for_cooling: bool
        ) -> Array8760:
    """(37)改 日付dの時刻tにおける1時間当たり 送風機の消費電力量のうちの暖房設備への付加分 [kWh/h]

    Args:
        E_E_fan_logic: ファン消費電力算定方法
        P_fan_rtd: 定格暖房能力運転時の送風機の消費電力 [W]
        V_hs_vent_d_t: 設備最低風量 ``V_hs_min`` の8760時間配列 [m3/h]。
            公開API互換のため引数名を保持しているが、全般換気風量ではない。
        V_hs_supply_d_t: 日付dの時刻tにおける熱源機の風量 [m3/h]
        V_hs_dsgn: 設計風量 [m3/h]
        E_E_fan_min: 最低電力直接入力値 [W]
        region: 地域区分
        for_cooling: 冷房計算の場合はTrue、暖房の場合はFalse

    Returns:
        単時点 送風機の消費電力量のうちの暖冷房設備への付加分 [kWh/h]
    """
    # NOTE: 本式の利用は 最低風量・最低電力 ともに直接入力ありに限られる

    if E_E_fan_logic not in (
        ファン消費電力算定方法.直線近似法,
        ファン消費電力算定方法.風量三乗近似法,
    ):
        raise ValueError("Invalid E_E_fan_logic")

    # 最低。全般換気の有無に依存しない設備側の補間点を使う。
    x1_d_t = np.asarray(V_hs_vent_d_t, dtype=float)
    y1 = E_E_fan_min
    # 定格
    x2 = V_hs_dsgn
    y2 = P_fan_rtd
    if (
        not np.all(np.isfinite(x1_d_t))
        or np.any(x1_d_t <= 0.0)
        or not np.isfinite(x2)
        or np.any(x1_d_t >= x2)
    ):
        raise ValueError(
            "最低電力補間では V_hs_min を正の有限値かつ "
            "V_hs_dsgn 未満にしてください。"
        )
    if (
        not np.isfinite(y1)
        or y1 < 0.0
        or not np.isfinite(y2)
        or y2 <= 0.0
        or y1 > y2
    ):
        raise ValueError(
            "最低電力補間では 0 <= E_E_fan_min <= P_fan_rtd を満たす"
            "有限値を入力してください。"
        )

    # 冷房期と中間期のファン消費電力は冷房消費電力、暖房期のファン消費電力は暖房消費電力とする
    H, C, M = get_season_array_d_t(region)
    # 全般換気なしの中間期など、実際の熱源機風量が0なら送風機も停止する。
    f = ((C | M) if for_cooling else H) & (V_hs_supply_d_t > 0.0)

    match E_E_fan_logic:
        case ファン消費電力算定方法.直線近似法:
            a, b = _solve_linear_system(x1_d_t, x2, y1, y2)
            E_E_fan = np.zeros_like(V_hs_supply_d_t)
            E_E_fan[f] = a[f] * V_hs_supply_d_t[f] + b[f]
            return np.maximum(E_E_fan * 1e-3, 0.0)  # [kW]

        case ファン消費電力算定方法.風量三乗近似法:
            a, b = _solve_cubic_system(x1_d_t, x2, y1, y2)
            E_E_fan = np.zeros_like(V_hs_supply_d_t)
            E_E_fan[f] = a[f] * V_hs_supply_d_t[f]**3 + b[f]
            return np.maximum(E_E_fan * 1e-3, 0.0)  # [kW]

        case _:
            raise AssertionError("validated fan power calculation method")

def _solve_linear_system(x1, x2, y1, y2):
    """連立方程式 y = a*x + b を解く"""
    a = (y2 - y1) / (x2 -x1)
    b = y1 - a * x1
    return a, b

def _solve_cubic_system(x1, x2, y1, y2):
    """連立方程式 y = a*x^3 + b を解く"""
    a = (y2 - y1) / (x2**3 - x1**3)
    b = y1 - a * (x1**3)
    return a, b
