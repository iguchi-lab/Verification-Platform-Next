from typing import NamedTuple

import numpy as np
import pyhees.section4_2 as dc

from .inputs.v_supply_cap_dto import VSupplyCapDto
from jjjexperiment.inputs.options import Vサプライの上限キャップ


def _expand_ventilation_airflow(V_vent_g_i: np.ndarray) -> np.ndarray:
    V_vent_g_i = np.reshape(V_vent_g_i, (5, 1))
    return V_vent_g_i.repeat(24 * 365, axis=1)


def _get_season_arrays(region: int):
    return dc.get_season_array_d_t(region)


def _cap_legacy_supply_airflow(
        V_supply_d_t_i: np.ndarray,
        V_dash_supply_d_t_i: np.ndarray,
        V_vent_g_i: np.ndarray,
) -> np.ndarray:
    # 吹き出し風量V_(supply,d,t,i)は、VAV調整前の吹き出し風量V_(supply,d,t,i)^'を上回る場合はVAV調整前の
    # 吹き出し風量V_(supply,d,t,i)^'に等しいとし、全般換気量V_(vent,g,i)を下回る場合は全般換気量V_(vent,g,i)に等しいとする
    return np.clip(V_supply_d_t_i, V_vent_g_i, V_dash_supply_d_t_i)


class _SupplyCapState(NamedTuple):
    V_supply_d_t_i: np.ndarray
    V_supply_d_t: np.ndarray
    overflow_mask_H_d_t: np.ndarray
    overflow_mask_C_d_t: np.ndarray


def _normalize_design_airflows(V_hs_dsgn_H, V_hs_dsgn_C):
    V_hs_dsgn_C = V_hs_dsgn_C if V_hs_dsgn_C is not None else float("inf")
    V_hs_dsgn_H = V_hs_dsgn_H if V_hs_dsgn_H is not None else float("inf")
    return V_hs_dsgn_H, V_hs_dsgn_C


def _prepare_supply_cap_state(
        V_supply_d_t_i: np.ndarray,
        V_vent_g_i: np.ndarray,
        H: np.ndarray,
        C: np.ndarray,
        V_hs_dsgn_H: float,
        V_hs_dsgn_C: float,
) -> _SupplyCapState:
    V_supply_d_t_i = np.clip(V_supply_d_t_i, V_vent_g_i, None)
    V_supply_d_t = np.sum(V_supply_d_t_i, axis=0)
    overflow_mask_H_d_t = np.logical_and(H, V_supply_d_t > V_hs_dsgn_H)
    overflow_mask_C_d_t = np.logical_and(C, V_supply_d_t > V_hs_dsgn_C)
    return _SupplyCapState(
        V_supply_d_t_i,
        V_supply_d_t,
        overflow_mask_H_d_t,
        overflow_mask_C_d_t,
    )


def _get_uniform_reduction_ratio(
        V_supply_d_t: np.ndarray,
        V_hs_dsgn: float,
        overflow_mask_d_t: np.ndarray,
) -> np.ndarray:
    return np.divide(
        np.full(len(V_supply_d_t), V_hs_dsgn, dtype=float),
        np.ceil(V_supply_d_t * 1000) / 1000,
        where=overflow_mask_d_t,
        out=np.ones_like(V_supply_d_t, dtype=float),
    )


def _apply_uniform_design_cap(
        state: _SupplyCapState,
        V_hs_dsgn_H: float,
        V_hs_dsgn_C: float,
) -> np.ndarray:
    ratios_H = _get_uniform_reduction_ratio(
        state.V_supply_d_t, V_hs_dsgn_H, state.overflow_mask_H_d_t,
    )
    ratios_C = _get_uniform_reduction_ratio(
        state.V_supply_d_t, V_hs_dsgn_C, state.overflow_mask_C_d_t,
    )
    return (
        state.V_supply_d_t_i
        * ratios_H[np.newaxis, :]
        * ratios_C[np.newaxis, :]
    )


def _assert_design_airflow_caps(
        new_V_supply_d_t_i: np.ndarray,
        H: np.ndarray,
        C: np.ndarray,
        V_hs_dsgn_H: float,
        V_hs_dsgn_C: float,
) -> None:
    check = np.sum(new_V_supply_d_t_i, axis=0)
    assert all(check[H] <= V_hs_dsgn_H)
    assert all(check[C] <= V_hs_dsgn_C)

class _IncrementOnlyCapState(NamedTuple):
    added_mask_d_t_i: np.ndarray
    target_mask_H_d_t_i: np.ndarray
    target_mask_C_d_t_i: np.ndarray
    overflow_values_H_d_t: np.ndarray
    overflow_values_C_d_t: np.ndarray
    masked_vs_H_d_t_i: np.ndarray
    masked_vs_C_d_t_i: np.ndarray
    added_sums_H_d_t_i: np.ndarray
    added_sums_C_d_t_i: np.ndarray


def _prepare_increment_only_cap_state(
        state: _SupplyCapState,
        V_dash_supply_d_t_i: np.ndarray,
        V_hs_dsgn_H: float,
        V_hs_dsgn_C: float,
) -> _IncrementOnlyCapState:
    overflow_mask_H_d_t_i = np.tile(state.overflow_mask_H_d_t, (5, 1))
    overflow_mask_C_d_t_i = np.tile(state.overflow_mask_C_d_t, (5, 1))

    added_mask_d_t_i = state.V_supply_d_t_i > V_dash_supply_d_t_i
    target_mask_H_d_t_i = np.logical_and(added_mask_d_t_i, overflow_mask_H_d_t_i)
    target_mask_C_d_t_i = np.logical_and(added_mask_d_t_i, overflow_mask_C_d_t_i)

    overflow_values_H_d_t = np.nan_to_num(
        state.V_supply_d_t - V_hs_dsgn_H, nan=0.0,
    )
    overflow_values_C_d_t = np.nan_to_num(
        state.V_supply_d_t - V_hs_dsgn_C, nan=0.0,
    )

    masked_vs_H_d_t_i = np.where(
        target_mask_H_d_t_i, state.V_supply_d_t_i, 0,
    )
    added_sums_H_d_t = np.sum(masked_vs_H_d_t_i, axis=0)
    added_sums_H_d_t_i = np.tile(added_sums_H_d_t, (5, 1))

    masked_vs_C_d_t_i = np.where(
        target_mask_C_d_t_i, state.V_supply_d_t_i, 0,
    )
    added_sums_C_d_t = np.sum(masked_vs_C_d_t_i, axis=0)
    added_sums_C_d_t_i = np.tile(added_sums_C_d_t, (5, 1))

    return _IncrementOnlyCapState(
        added_mask_d_t_i,
        target_mask_H_d_t_i,
        target_mask_C_d_t_i,
        overflow_values_H_d_t,
        overflow_values_C_d_t,
        masked_vs_H_d_t_i,
        masked_vs_C_d_t_i,
        added_sums_H_d_t_i,
        added_sums_C_d_t_i,
    )

# NOTE: 過剰熱量ループ内でも使用しているため
# @log_res(['V_supply_d_t_i'])
def cap_V_supply_d_t_i(
        V_supply_cap_dto: VSupplyCapDto,
        V_supply_d_t_i: np.ndarray,
        V_dash_supply_d_t_i: np.ndarray,
        V_vent_g_i: np.ndarray,
        region: int,
        V_hs_dsgn_H: float,
        V_hs_dsgn_C: float,
        print_exec=True):
    """
    Args:
        V_supply_d_t_i: 未キャップ 日付dの時刻tにおける 暖冷房区画iの吹き出し風量 [m3/h]
        V_dash_supply_d_t_i: 日付dの時刻tにおける 暖冷房区画iのVAV調整前の吹き出し風量 [m3/h]
        V_vent_g_i: 暖冷房区画iの全般換気量 [m3/h]
        region: 地域区分
        V_hs_dsgn_H: 暖房時の設計風量 [m3/h]
        V_hs_dsgn_C: 冷房時の設計風量 [m3/h]

    Returns:
        V_supply_d_t_i: キャップ済 日付dの時刻tにおける 暖冷房区画iの吹き出し風量 [m3/h]

    """
    V_vent_g_i = _expand_ventilation_airflow(V_vent_g_i)

    H, C, M = _get_season_arrays(region)

    if V_supply_cap_dto.v_supply_cap_logic == Vサプライの上限キャップ.従来:
        if print_exec:
            print(Vサプライの上限キャップ.従来)
        new_V_supply_d_t_i = _cap_legacy_supply_airflow(
            V_supply_d_t_i, V_dash_supply_d_t_i, V_vent_g_i,
        )

    elif V_supply_cap_dto.v_supply_cap_logic == Vサプライの上限キャップ.設計風量_全室で均一:
        if print_exec:
            print(Vサプライの上限キャップ.設計風量_全室で均一)
        # 委員より提案 案1('24/01)
        V_hs_dsgn_H, V_hs_dsgn_C = _normalize_design_airflows(
            V_hs_dsgn_H, V_hs_dsgn_C,
        )
        state = _prepare_supply_cap_state(
            V_supply_d_t_i, V_vent_g_i, H, C,
            V_hs_dsgn_H, V_hs_dsgn_C,
        )
        new_V_supply_d_t_i = _apply_uniform_design_cap(
            state, V_hs_dsgn_H, V_hs_dsgn_C,
        )
        _assert_design_airflow_caps(
            new_V_supply_d_t_i, H, C, V_hs_dsgn_H, V_hs_dsgn_C,
        )
    elif V_supply_cap_dto.v_supply_cap_logic == Vサプライの上限キャップ.設計風量_風量増室のみ:
        if print_exec:
            print(Vサプライの上限キャップ.設計風量_風量増室のみ)
        # 委員より提案 案2('24/01)

        V_hs_dsgn_H, V_hs_dsgn_C = _normalize_design_airflows(
            V_hs_dsgn_H, V_hs_dsgn_C,
        )
        state = _prepare_supply_cap_state(
            V_supply_d_t_i, V_vent_g_i, H, C,
            V_hs_dsgn_H, V_hs_dsgn_C,
        )
        increment_state = _prepare_increment_only_cap_state(
            state, V_dash_supply_d_t_i, V_hs_dsgn_H, V_hs_dsgn_C,
        )
        V_supply_d_t_i = state.V_supply_d_t_i
        added_mask_d_t_i = increment_state.added_mask_d_t_i
        target_mask_H_d_t_i = increment_state.target_mask_H_d_t_i
        target_mask_C_d_t_i = increment_state.target_mask_C_d_t_i
        overflow_values_H_d_t = increment_state.overflow_values_H_d_t
        overflow_values_C_d_t = increment_state.overflow_values_C_d_t
        masked_vs_H_d_t_i = increment_state.masked_vs_H_d_t_i
        masked_vs_C_d_t_i = increment_state.masked_vs_C_d_t_i
        added_sums_H_d_t_i = increment_state.added_sums_H_d_t_i
        added_sums_C_d_t_i = increment_state.added_sums_C_d_t_i
        default_subtract_d_t_i = np.zeros_like(V_supply_d_t_i)

        ratio_H_d_t_i = np.divide(masked_vs_H_d_t_i,
                            np.floor(added_sums_H_d_t_i * 1000) / 1000,  # 超えない工夫(引くのを大き目に)
                            where=target_mask_H_d_t_i, out=default_subtract_d_t_i)
        # ratio_H_d_t_i = np.nan_to_num(ratio_H_d_t_i, nan=0.0)
        # 削減量に値の割合を適用
        subtract_H_d_t_i = ratio_H_d_t_i * np.tile(overflow_values_H_d_t, (5,1))

        ratio_C_d_t_i = np.divide(masked_vs_C_d_t_i,
                            np.floor(added_sums_C_d_t_i * 1000) / 1000,
                            where=target_mask_C_d_t_i, out=default_subtract_d_t_i)
        # ratio_C_d_t_i = np.nan_to_num(ratio_C_d_t_i, nan=0.0)
        # 削減量に値の割合を適用
        subtract_C_d_t_i = ratio_C_d_t_i * np.tile(overflow_values_C_d_t, (5,1))

        """ 元から制限を超えてしまってないか念のためチェックします """
        added_mask_d_t = np.sum(added_mask_d_t_i, axis=0)
        # NOTE: 増加していないのに、制限を超えてしまっている時刻がないか
        should_be_target = np.logical_or(overflow_values_H_d_t > 0, overflow_values_C_d_t > 0)
        errors = np.logical_and(added_mask_d_t == 0, should_be_target)
        assert not np.any(errors), "元から制限を超えている時刻があるようです."

        """ 減算の実行 """
        new_V_supply_d_t_i = np.where(
            target_mask_H_d_t_i,  # 引き算対象セル
            V_supply_d_t_i - subtract_H_d_t_i,
            V_supply_d_t_i)  # 引き算しない箇所の値

        new_V_supply_d_t_i = np.where(
            target_mask_C_d_t_i,  # 引き算対象セル
            new_V_supply_d_t_i - subtract_C_d_t_i,
            new_V_supply_d_t_i)  # 引き算しない箇所の値

        """ 事後条件の確認"""
        check = np.sum(new_V_supply_d_t_i, axis=0)
        # TODO: バグ修正して有効にする
        assert all(check[H] <= V_hs_dsgn_H)
        assert all(check[C] <= V_hs_dsgn_C)

    else:
        raise ValueError("change_V_supply_d_t_i is out of range")

    return new_V_supply_d_t_i
