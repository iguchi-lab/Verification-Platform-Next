from pyhees.section4_2 import get_V_vent_g_i


# 暖冷房区画iの全般換気量（最低風量を反映）
def get_V_vent_g_i_with_V_hs_min(A_HCZ_i, A_HCZ_R_i, V_hs_min):
    """(62)

    Args:
      A_HCZ_i: 暖冷房区画iの床面積 (m2)
      A_HCZ_R_i: 標準住戸における暖冷房区画iの床面積（m2）
      V_hs_min: 最低風量 (m3/h)

    Returns:
      ndarray[5]: 暖冷房区画iの機械換気量 (m3/h)

    """
    # 既存ロジックの暖冷房区画iの全般換気量 [m3/h]
    V_vent_g_i_before = get_V_vent_g_i(A_HCZ_i, A_HCZ_R_i)

    # 全般換気量の暖冷房区画iごとの比率を維持したまま、合計を最低風量にする
    return V_hs_min * V_vent_g_i_before / V_vent_g_i_before.sum()
