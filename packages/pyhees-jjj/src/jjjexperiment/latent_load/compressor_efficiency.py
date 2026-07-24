import jjjexperiment.constants as jjj_consts
from jjjexperiment.common import jjj_cloning


@jjj_cloning
def get_e_r_H_d_t(q_hs_H_d_t):
    """(9-1)(9-2)(9-3)(9-4) ルームエアコンディショナ活用型全館空調（新：潜熱評価モデル）対応_コンプレッサ効率特性

    Args:
      q_hs_H_d_t: 日付dの時刻tにおける1時間当たりの熱源機の平均暖房能力（W）
    Returns:
      日付dの時刻tにおける暖房時のヒートポンプサイクルの理論効率に対する熱源機の効率の比（-）
    """
    x = q_hs_H_d_t / 1000
    e_r_H_d_t = jjj_consts.a_r_H_t_t_a4 * x**4 + jjj_consts.a_r_H_t_t_a3 * x**3 + jjj_consts.a_r_H_t_t_a2 * x**2 + jjj_consts.a_r_H_t_t_a1 * x + jjj_consts.a_r_H_t_t_a0
    return e_r_H_d_t

@jjj_cloning
def get_e_r_C_d_t(q_hs_C_d_t):
    """(10-1)(10-2)(10-3)(10-4) _コンプレッサ効率特性

    Args:
      q_hs_C_d_t: 日付dの時刻tにおける1時間当たりの熱源機の平均冷房能力（W）
    Returns:
      日付dの時刻tにおける冷房時のヒートポンプサイクルの理論効率に対する熱源機の効率の比（-）
    """
    x = q_hs_C_d_t / 1000
    e_r_C_d_t = jjj_consts.a_r_C_t_t_a4 * x**4 + jjj_consts.a_r_C_t_t_a3 * x**3 + jjj_consts.a_r_C_t_t_a2 * x**2 + jjj_consts.a_r_C_t_t_a1 * x + jjj_consts.a_r_C_t_t_a0
    return e_r_C_d_t
