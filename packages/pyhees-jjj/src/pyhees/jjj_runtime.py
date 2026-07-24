"""Verification Platform固有処理を建研由来コードへ接続する内部アダプター。

このモジュールは建研上流由来ではない。pyhees側からjjjexperiment実装を
importせず、既定動作と実行時providerだけを保持する。
"""

from enum import Enum
from functools import wraps


class 計算モデル(Enum):
    ダクト式セントラル空調機 = 1
    RAC活用型全館空調_現行省エネ法RACモデル = 2
    RAC活用型全館空調_潜熱評価モデル = 3
    電中研モデル = 4


class 床下空調ロジック(Enum):
    変更しない = 1
    変更する = 2


class ファン消費電力から換気分を引く(Enum):
    換気分を引く = 1
    換気分を引かない = 2


_DEFAULT_CONSTANTS = {
    "A_e_hex_large_H": 10.6,
    "A_e_hex_small_H": 6.2,
    "A_f_hex_large_H": 0.3,
    "A_f_hex_small_H": 0.2,
    "C_df_H_d_t_defrost_ductcentral": 0.77,
    "C_df_H_d_t_defrost_rac": 0.77,
    "C_hm_C": 1.15,
    "Theta_hs_out_max_H_d_t_limit": 45,
    "Theta_hs_out_min_C_d_t_limit": 15,
    "a_c_hex_c_a0_C": 0.0015,
    "a_c_hex_c_a1_C": 0.0631,
    "a_c_hex_c_a2_C": 0,
    "a_c_hex_c_a3_C": 0,
    "a_c_hex_c_a4_C": 0,
    "airvolume_coeff_a0_C": 10.209,
    "airvolume_coeff_a0_H": 12.084,
    "airvolume_coeff_a1_C": 2.4855,
    "airvolume_coeff_a1_H": 1.2946,
    "airvolume_coeff_a2_C": 0,
    "airvolume_coeff_a2_H": 0,
    "airvolume_coeff_a3_C": 0,
    "airvolume_coeff_a3_H": 0,
    "airvolume_coeff_a4_C": 0,
    "airvolume_coeff_a4_H": 0,
    "airvolume_maximum_C": 24.3824,
    "airvolume_maximum_H": 24.3824,
    "airvolume_minimum_C": 14.38995,
    "airvolume_minimum_H": 14.38995,
    "change_heat_source_outlet_required_temperature": 1,
    "defrost_humid_ductcentral": 80,
    "defrost_humid_rac": 80,
    "defrost_temp_ductcentral": 5,
    "defrost_temp_rac": 5,
    "phi_i": 0.49,
    "q_rtd_C_limit": 5600,
}

_constant_provider = _DEFAULT_CONSTANTS.__getitem__
_result_logger = None


def _resolve_explicit_underfloor_context(new_ufac, new_ufac_df):
    return new_ufac, new_ufac_df


_underfloor_context_resolver = _resolve_explicit_underfloor_context


def set_constant_provider(provider):
    global _constant_provider
    _constant_provider = provider


def get_constant(name):
    return _constant_provider(name)

def get_default_constant(name):
    return _DEFAULT_CONSTANTS[name]


def set_result_logger(logger):
    global _result_logger
    _result_logger = logger


def log_res(res_labels=None):
    labels = [] if res_labels is None else res_labels

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if _result_logger is not None:
                _result_logger(func, result, labels)
            return result

        return wrapper

    return decorator


def set_underfloor_context_resolver(resolver):
    global _underfloor_context_resolver
    _underfloor_context_resolver = resolver


def resolve_underfloor_context(new_ufac, new_ufac_df):
    return _underfloor_context_resolver(new_ufac, new_ufac_df)
