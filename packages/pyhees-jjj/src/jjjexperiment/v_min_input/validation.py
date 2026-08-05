"""最低風量・最低電力直接入力の数値整合性検証。"""

from __future__ import annotations

import math


def require_positive_finite(value: float, field_name: str) -> float:
    """正の有限値を返し、不正値は入力項目名付きで拒否する。"""
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{field_name} は正の有限値で入力してください。")
    return parsed


def require_nonnegative_finite(value: float, field_name: str) -> float:
    """0以上の有限値を返し、不正値は入力項目名付きで拒否する。"""
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{field_name} は0以上の有限値で入力してください。")
    return parsed


def validate_minimum_airflow_relation(
    V_hs_min: float,
    V_hs_dsgn: float,
    mode_name: str,
) -> None:
    """設備最低風量が設計風量以下であることを検証する。"""
    minimum = require_positive_finite(V_hs_min, f"{mode_name} V_hs_min")
    design = require_positive_finite(V_hs_dsgn, f"{mode_name} V_hs_dsgn")
    if minimum > design:
        raise ValueError(
            f"{mode_name} V_hs_min ({minimum:g} m3/h) は "
            f"V_hs_dsgn ({design:g} m3/h) 以下にしてください。"
        )


def validate_minimum_fan_power_relation(
    E_E_fan_min: float,
    P_fan_rtd: float,
    mode_name: str,
) -> None:
    """最低電力が定格ファン電力以下であることを検証する。"""
    minimum = require_nonnegative_finite(
        E_E_fan_min,
        f"{mode_name} E_E_fan_min",
    )
    rated = require_positive_finite(P_fan_rtd, f"{mode_name} P_fan_rtd")
    if minimum > rated:
        raise ValueError(
            f"{mode_name} E_E_fan_min ({minimum:g} W) は "
            f"P_fan_rtd ({rated:g} W) 以下にしてください。"
        )
