import pandas as pd
from dataclasses import dataclass, replace
# JJJ
from jjjexperiment.inputs.options import 床下空調ロジック
from jjjexperiment.csv_artifacts import write_dataframe_csv
from jjjexperiment.underfloor_ac.selection import underfloor_enabled
# NOTE: データクラスからどうしてもロジックを参照するときは遅延インポートする

__all__ = ['UnderfloorAc', 'UfVarsDataFrame']

@dataclass
class UnderfloorAc:
    """F24-05 床下空調に関する設定値"""

    new_ufac_flg: 床下空調ロジック = 床下空調ロジック.変更しない

    # NOTE: Theta_g_avg と U_s_vert は旧入力JSONとの互換保持用。
    # 現行計算ではそれぞれ気象系列からの自動算定値と用途別U値を使用する。
    """床下空調ロジック"""
    Theta_g_avg: float = 15.7
    """地盤内の不易層の温度 [℃]"""
    U_s_vert: float = 2.223
    """床板(床チャンバー上面)の U_s [W/(m2・K)]（外部入力名は歴史的名称）"""
    phi: float = 0.846
    """基礎(床チャンバー側面)の線熱貫流率 [W/(m・K)]"""

    # 現在はただの定数としてユーザー入力させていない
    U_s_floor_ins: float = 0.41
    """床断熱の熱貫流率 [W/(m2・K)]"""
    explicit_constants: bool = False
    """True when optional user-entered underfloor constants are used."""
    heating_enabled: bool | None = None
    cooling_enabled: bool | None = None

    def enabled_for(self, season: str) -> bool:
        enabled = self.heating_enabled if season == "H" else self.cooling_enabled
        return self.new_ufac_flg == 床下空調ロジック.変更する if enabled is None else enabled

    def for_season(self, season: str) -> 'UnderfloorAc':
        return replace(self, new_ufac_flg=床下空調ロジック(
            2 if self.enabled_for(season) else 1))

    @classmethod
    def from_dict(cls, data: dict) -> 'UnderfloorAc':
        enabled = underfloor_enabled(data)
        kwargs = dict(
            new_ufac_flg=床下空調ロジック(2 if enabled else 1),
            heating_enabled=underfloor_enabled(data, 'H'),
            cooling_enabled=underfloor_enabled(data, 'C'),
        )
        if enabled and int(data.get('input_ufac_consts', 1)) == 2:
            kwargs['explicit_constants'] = True
            kwargs['phi'] = float(data['phi'])
        return cls(**kwargs)

class UfVarsDataFrame:
    '''床下空調 新ロジックの調査用 出力変数'''
    def __init__(self):
        # d_t 長のデータフレーム
        self._df_d_t = pd.DataFrame()

    def update_df(self, data: dict):
        # 横連結時は ignore_index しないこと
        self._df_d_t = pd.concat([self._df_d_t, pd.DataFrame(data)], axis=1)

    def export_to_csv(self, filename: str, encoding: str = 'cp932'):
        '''csv書き出し'''
        write_dataframe_csv(
            self._df_d_t,
            filename,
            index=False,
            encoding=encoding,
        )
