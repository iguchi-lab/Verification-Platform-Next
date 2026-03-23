import numpy as np
import pyhees.section3_1_e as algo
# JJJ
from jjjexperiment.common import jjj_cloning
from jjjexperiment.logger import log_res

@jjj_cloning
def get_Theta_uf_d_t_runup() -> np.ndarray:
    """新床下空調ロジック用の助走計算床下温度 (℃) の時系列を返す

    標準住戸の新床下空調ロジックにおける助走計算に用いる
    床下温度の代表値を季節区分ごとに並べた定数配列。
    合計 8760 時間 (= 24 × 365)。

    Returns:
        ndarray: shape (8760,) の床下温度時系列 [℃]
    """
    THETA_UF_WARM = 27.69   # 冬・春・秋期の床下温度 [℃]
    THETA_UF_COOL = 25.62   # 夏期の床下温度 [℃]
    N_HOURS_WARM_1 = 2664   # 第1期間（年始〜春）[h]
    N_HOURS_COOL   = 3721   # 第2期間（夏）[h]
    N_HOURS_WARM_2 = 2375   # 第3期間（秋〜年末）[h]
    assert N_HOURS_WARM_1 + N_HOURS_COOL + N_HOURS_WARM_2 == 24 * 365
    return np.array(
        [THETA_UF_WARM] * N_HOURS_WARM_1
        + [THETA_UF_COOL] * N_HOURS_COOL
        + [THETA_UF_WARM] * N_HOURS_WARM_2,
        dtype=float
    )


@log_res(['Theta_uf_d_t'])
def calc_Theta_uf_d_t_2023(L_star_H_d_t_i, L_star_CS_d_t_i, A_A, A_MR, A_OR, r_A_ufvnt, V_dash_supply_d_t_i, Theta_ex_d_t):
    """定常状態での床下温度を求める

    Args:
      L_star_H_d_t_i(ndarray): 暖冷房区画iの1時間当たりの暖房負荷 (MJ/h)
      L_star_CS_d_t_i(ndarray): 暖冷房区画iの1時間当たりの冷房顕熱負荷 (MJ/h)
      A_A(float): 床面積の合計 (m2)
      A_MR(float): 主たる居室の床面積 (m2)
      A_OR(float): その他の居室の床面積 (m2)
      r_A_ufvnt(list[float]): 当該住戸において、床下空間全体の面積に対する空気を供給する床下空間の面積の比 (-)
      V_dash_supply_d_t_i(ndarray): 日付dの時刻tにおける暖冷房区画iのVAV調整前の熱源機の風量（m3/h）
      Theta_ex_d_t(ndarray): 外気温度 (℃)

    Returns:
      日付dの時刻tにおける暖冷房区画iの1時間当たりの床下温度

    """

    ro_air = algo.get_ro_air()    # 空気密度 [kg/m3]
    c_p_air = algo.get_c_p_air()  # 空気の比熱 [kJ/kgK]
    U_s = algo.get_U_s()          # 床の熱貫流率 [W/m2K]

    H_floor = 0.7  # 床の温度差係数 [-]
    Theta_in_C = 27.0  # 冷房時の室温 [℃]
    Theta_in_H = 20.0  # 暖房時の室温 [℃]

    # 事前条件: 床下空調を使用しているので 有効な値が存在する
    if (r_A_ufvnt is None or r_A_ufvnt == 0):
        raise ValueError("床下空調に使用する面積の割合が有効な値になっていない.")

    """NOTE: 床下空調(新ロジック)計算仕様"""
    # 床下利用は1階のみとする(2F居室は通常の空調)
    # ここでは隣室の貫流による損失は考慮していません
    endi=2  # 1F居室分(i=1,2) のみ

    """NOTE: 式の導出"""
    # (暖冷房負荷 - 床下への損失 = 床下からの吹出 + 床下からの貫流) で θuf について解く

    # 当該住戸の暖冷房区画iの空気を供給する床下空間に接する床の面積 (m2) (7)
    A_s_ufvnt = sum([algo.calc_A_s_ufvnt_i(i, r_A_ufvnt, A_A, A_MR, A_OR) for i in range(1, endi+1)])

    # 暖冷房区画iの床面積のうち床下空間に接する床面積の割合 (-)
    r_A_uf_i = np.array([algo.get_r_A_uf_i(i) for i in range(1, endi+1)])
    # 床下への供給風量の合計
    V_dash_supply_flr1st_d_t  \
      = np.sum(r_A_uf_i[:endi, np.newaxis] * V_dash_supply_d_t_i[:endi, :], axis=0)

    H = Theta_ex_d_t < Theta_in_H
    C = Theta_ex_d_t > Theta_in_C
    M = np.logical_not(np.logical_or(H, C))

    # TODO: 冷房が 暖房と同じでよいかは要検討
    L_star_H_flr1st_d_t = np.zeros(24 * 365)
    L_star_H_flr1st_d_t[H]  \
      = np.sum(r_A_uf_i[:endi, np.newaxis] * L_star_H_d_t_i[:endi, H], axis=0)  \
        * 1000  # [kJ/h]
    L_star_CS_flr1st_d_t = np.zeros(24 * 365)
    L_star_CS_flr1st_d_t[C]  \
      = np.sum(r_A_uf_i[:endi, np.newaxis] * L_star_CS_d_t_i[:endi, C], axis=0)  \
        * 1000  # [kJ/h]

    assert L_star_H_flr1st_d_t.shape == (24 * 365,)
    assert L_star_CS_flr1st_d_t.shape == (24 * 365,)

    # upper2_H = U_s * A_s_ufvnt * ((Theta_in_H - Theta_ex_d_t[H]) * H_floor - Theta_in_H) * 3.6
    # upper2_C = U_s * A_s_ufvnt * ((Theta_in_C - Theta_ex_d_t[C]) * H_floor - Theta_in_C) * 3.6

    Q1_H_d_t = np.zeros(24 * 365)
    Q1_H_d_t[H] = ro_air * c_p_air * V_dash_supply_flr1st_d_t[H]
    Q1_C_d_t = np.zeros(24 * 365)
    Q1_C_d_t[C] = ro_air * c_p_air * V_dash_supply_flr1st_d_t[C]
    Q2 = U_s * A_s_ufvnt * 3.6

    assert Q1_H_d_t.shape == (24 * 365,)
    assert Q1_C_d_t.shape == (24 * 365,)

    Theta_uf_d_t = np.zeros(24 * 365)  # NOTE: 床下はつながっているので d_t_i にならない
    Theta_uf_d_t[H] = ((L_star_H_flr1st_d_t + Theta_in_H * (Q1_H_d_t + Q2)) / (Q1_H_d_t + Q2))[H]
    Theta_uf_d_t[C] = ((-1 * L_star_CS_flr1st_d_t + Theta_in_C * (Q1_C_d_t + Q2)) / (Q1_C_d_t + Q2))[C]
    Theta_uf_d_t[M] = Theta_ex_d_t[M]

    return Theta_uf_d_t
