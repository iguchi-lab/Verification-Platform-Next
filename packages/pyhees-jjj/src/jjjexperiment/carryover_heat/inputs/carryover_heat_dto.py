from dataclasses import dataclass
# NOTE: データクラスからどうしてもロジックを参照するときは遅延インポートする
from jjjexperiment.inputs.options import 過剰熱量繰越計算
from jjjexperiment.carryover_heat.temperature_policy import validate_temperature_policy

@dataclass
class CarryoverHeatDto:
    """過剰熱量持越しと、未処理負荷計上時の居室温度の扱い。"""

    carry_over_heat: 過剰熱量繰越計算 = 過剰熱量繰越計算.行わない
    """過剰熱量を次の時刻に持ち越す"""

    carryover_temperature_policy: str = "signed"

    def __post_init__(self):
        validate_temperature_policy(self.carryover_temperature_policy)

    @classmethod
    def from_dict(cls, data: dict) -> 'CarryoverHeatDto':
        kwargs = {}

        if 'carry_over_heat' in data:
            carry_over_heat = 過剰熱量繰越計算(int(data['carry_over_heat']))
            kwargs['carry_over_heat'] = carry_over_heat

        kwargs['carryover_temperature_policy'] = data.get('carryover_temperature_policy', 'signed')
        return cls(**kwargs)
