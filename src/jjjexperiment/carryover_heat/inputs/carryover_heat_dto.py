from dataclasses import dataclass
# NOTE: データクラスからどうしてもロジックを参照するときは遅延インポートする
from jjjexperiment.inputs.options import 過剰熱量繰越計算

@dataclass
class CarryoverHeatDto:
    """F23-02 Vサプライの上限キャップ変更に関する設定値"""

    carry_over_heat: 過剰熱量繰越計算 = 過剰熱量繰越計算.行わない
    """過剰熱量を次の時刻に持ち越す"""

    @classmethod
    def from_dict(cls, data: dict) -> 'CarryoverHeatDto':
        kwargs = {}

        if 'carry_over_heat' in data:
            carry_over_heat = 過剰熱量繰越計算(int(data['carry_over_heat']))
            kwargs['carry_over_heat'] = carry_over_heat

        return cls(**kwargs)
