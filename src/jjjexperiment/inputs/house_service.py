from pyhees.section3_1 import get_A_HCZ_R_i
from pyhees.section3_1_e import get_r_A_uf_i


def get_r_A_NR_uf_1F_excl_bath() -> float:
    """非居室の床下から貫流する部分の面積の割合 (1F・浴室除く) [-]

    非居室ゾーン(i=6~12)のうち床下空間に接するゾーン(i=6,7,9)の有効面積合計と
    標準住戸の非居室合計面積の比率。ゾーン8(浴室)は除外する。
    この値は住戸面積(A_A, A_MR, A_OR)には依存しない構造定数。

    Returns:
        float: 非居室の1F(浴室除く)面積比 (≈ 0.404)
    """
    # 1F NR有効面積 (浴室=ゾーン8 を除く)
    A_NR_1F_excl_bath = sum(get_r_A_uf_i(i) * get_A_HCZ_R_i(i) for i in [6, 7, 9])
    # 標準住戸の非居室合計面積
    A_NR_R = sum(get_A_HCZ_R_i(i) for i in range(6, 13))
    return A_NR_1F_excl_bath / A_NR_R
