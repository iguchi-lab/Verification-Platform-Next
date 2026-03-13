import numpy as np
import pytest

from pyhees.section4_2 import get_season_array_d_t
from pyhees.section4_2_a import get_E_E_fan_H_d_t, get_E_E_fan_C_d_t
from jjjexperiment.inputs.options import ファン消費電力から換気分を引く


class Test従来モデル送風機消費電力:
    """従来モデルの送風機消費電力テスト (pyhees.section4_2_a)"""

    def setup_method(self):
        self.P_fan_rtd = 100.0
        self.V_hs_vent = np.full(8760, 50.0)
        self.V_hs_supply = np.full(8760, 200.0)
        self.V_hs_dsgn = 300.0
        self.q_hs = np.zeros(8760)
        self.q_hs[0] = 1000.0  # 1件だけ負荷あり
        self.region = 6  # 6地域。暖房期、中間期、冷房期の月を決定するためだけに使われる
        H, C, M = get_season_array_d_t(self.region)
        self.H = H
        self.C = C
        self.M = M

    def test_暖房_換気分を引く_デフォルト(self):
        # f_SFP デフォルト = 0.4 * 0.36 = 0.144
        # P_fan_vent = 0.144 * 50.0 = 7.2
        # a = (100.0 - 7.2) * ((200.0 - 50.0) / (300.0 - 50.0)) * 1e-3
        # a = 92.8 * (150 / 250) * 1e-3 = 92.8 * 0.6 * 1e-3 = 0.05568

        result = get_E_E_fan_H_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region
        )
        assert result[0] == pytest.approx(0.05568)
        assert result[1] == 0.0

    def test_暖房_換気分を引かない(self):
        # P_fan_vent = 0
        # a = (100.0 - 7.2) * ((200.0 - 50.0) / (300.0 - 50.0)) * 1e-3
        # E = 92.8 * 0.6 * 1e-3 + 0.0072 = 0.06288

        result = get_E_E_fan_H_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region,
            subtract_ventilation_power=ファン消費電力から換気分を引く.換気分を引かない
        )
        assert result[self.H][0] == pytest.approx(0.06288)  # 暖房期
        assert (result[self.M] == 0.0).all()                # 中間期はゼロ
        assert (result[self.C] == 0.0).all()                # 冷房期はゼロ

    def test_暖房_SFP指定(self):
        # f_SFP = 0.5
        # P_fan_vent = 0.5 * 50.0 = 25.0
        # a = (100.0 - 25.0) * 0.6 * 1e-3 = 75.0 * 0.6 * 1e-3 = 0.045

        result = get_E_E_fan_H_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region,
            f_SFP=0.5
        )
        assert result[self.H][0] == pytest.approx(0.045)

    def test_冷房_換気分を引く_デフォルト(self):
        # f_SFP デフォルト = 0.144
        # P_fan_vent = 7.2
        # a = (100.0 - 7.2) * 0.6 * 1e-3 = 0.05568

        result = get_E_E_fan_C_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region
        )
        assert result[0] == pytest.approx(0.05568)

    def test_冷房_換気分を引かない(self):
        # P_fan_vent = 0
        # a = (100.0 - 7.2) * 0.6 * 1e-3 = 0.06
        # E = 92.8 * 0.6 * 1e-3 + 0.0072 = 0.06288
        # 冷房期・中間期のみ値が入り、暖房期はゼロ

        result = get_E_E_fan_C_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region,
            subtract_ventilation_power=ファン消費電力から換気分を引く.換気分を引かない
        )
        assert (result[self.H] == 0.0).all()                # 暖房期はゼロ
        assert result[self.M][0] == pytest.approx(0.06288)  # 中間期
        assert result[self.C][0] == pytest.approx(0.06288)  # 冷房期

    def test_冷房_SFP指定(self):
        # f_SFP = 0.5
        # P_fan_vent = 25.0
        # a = 75.0 * 0.6 * 1e-3 = 0.045

        result = get_E_E_fan_C_d_t(
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn, self.q_hs, self.region,
            f_SFP=0.5
        )
        assert result[0] == pytest.approx(0.045)
