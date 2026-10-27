"""Room temperature convention when unmet load is counted as primary energy."""
import numpy as np


TEMPERATURE_POLICIES = {
    "signed": "過剰分と不足分を持ち越す（現行）",
    "setpoint": "未処理負荷を計上し、設定温度で補完する",
}


def validate_temperature_policy(value):
    if not isinstance(value, str) or value not in TEMPERATURE_POLICIES:
        raise ValueError("carryover_temperature_policy は signed または setpoint を指定してください。")
    return value


def compensate_room_temperature(temperature, setpoint, heating, cooling):
    """Only remove the deficit side; preserve surplus and intermediate seasons.

    Use this evaluation temperature for delivered heat / unmet load accounting,
    the non-room balance and the next hour's stored heat. Do not add the virtual
    compensation to the heat source output or compressor electricity a second time.
    """
    if heating:
        return np.maximum(temperature, setpoint)
    if cooling:
        return np.minimum(temperature, setpoint)
    return temperature
