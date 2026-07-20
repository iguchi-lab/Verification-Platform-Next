import numpy as np
import pytest
from jjjexperiment.v_min_input.section4_2_a import get_E_E_fan_d_t
from jjjexperiment.inputs.options import ファン消費電力算定方法
from pyhees.section4_2 import get_season_array_d_t


class TestVMinInput送風機消費電力:
    """最低風量・最低電力直接入力モデルの送風機消費電力テスト (jjjexperiment.v_min_input.section4_2_a)"""

    def setup_method(self):
        self.P_fan_rtd = 100.0  # 定格電力 [W] (y2)
        self.V_hs_vent = np.full(8760, 50.0)  # 最低風量 [m3/h] (x1)
        self.V_hs_supply = np.full(8760, 200.0)  # 現在の風量 [m3/h]
        self.V_hs_dsgn = 300.0  # 設計風量 [m3/h] (x2)
        self.E_E_fan_min = 20.0  # 最低電力 [W] (y1)
        self.region = 6
        H, C, M = get_season_array_d_t(self.region)
        self.H = H
        self.C = C
        self.M = M

    def test_直線近似法(self):
        # y = ax + b
        # a = (y2 - y1) / (x2 - x1) = (100 - 20) / (300 - 50) = 80 / 250 = 0.32
        # b = y1 - a * x1 = 20 - 0.32 * 50 = 20 - 16 = 4
        # y(200) = 0.32 * 200 + 4 = 64 + 4 = 68 [W]
        # result = 68 * 1e-3 = 0.068 [kW]

        result = get_E_E_fan_d_t(
            ファン消費電力算定方法.直線近似法,
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn,
            self.E_E_fan_min, self.region, for_cooling=False
        )
        # 暖房期の時間帯で計算値を確認
        assert result[self.H][0] == pytest.approx(0.068)
        # 冷房期と中間期はゼロ
        assert (result[self.C] == 0.0).all()
        assert (result[self.M] == 0.0).all()

    def test_風量三乗近似法(self):
        # y = ax^3 + b
        # a = (y2 - y1) / (x2^3 - x1^3) = (100 - 20) / (300^3 - 50^3)
        # a = 80 / (27,000,000 - 125,000) = 80 / 26,875,000 = 1 / 335,937.5
        # b = y1 - a * x1^3 = 20 - (1 / 335,937.5) * 125,000 = 20 - 0.372093... = 19.6279...
        # y(200) = a * 200^3 + b = (1 / 335,937.5) * 8,000,000 + 19.6279...
        # y(200) = 23.81395... + 19.6279... = 43.44186... [W]
        # result = 0.04344186... [kW]

        x1, x2 = 50.0, 300.0
        y1, y2 = 20.0, 100.0
        a = (y2 - y1) / (x2 ** 3 - x1 ** 3)
        b = y1 - a * (x1 ** 3)
        expected_y = a * (200.0 ** 3) + b
        expected_result = expected_y * 1e-3

        result = get_E_E_fan_d_t(
            ファン消費電力算定方法.風量三乗近似法,
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn,
            self.E_E_fan_min, self.region, for_cooling=False
        )
        # 暖房期の時間帯で計算値を確認
        assert result[self.H][0] == pytest.approx(expected_result)


class TestVMinInput送風機消費電力_冷房:
    """冷房時を想定したテスト（入力パラメータが冷房用になるだけでロジックは共通）"""

    def setup_method(self):
        self.P_fan_rtd = 120.0  # 定格電力 [W]
        self.V_hs_vent = np.full(8760, 60.0)  # 最低風量 [m3/h]
        self.V_hs_supply = np.full(8760, 250.0)  # 現在の風量 [m3/h]
        self.V_hs_dsgn = 400.0  # 設計風量 [m3/h]
        self.E_E_fan_min = 30.0  # 最低電力 [W]
        self.region = 6
        H, C, M = get_season_array_d_t(self.region)
        self.H = H
        self.C = C
        self.M = M

    def test_直線近似法_冷房(self):
        # a = (120 - 30) / (400 - 60) = 90 / 340 = 9 / 34
        # b = 30 - (9/34) * 60 = 30 - 540/34 = 30 - 15.882... = 14.117...
        # y(250) = (9/34) * 250 + 14.117... = 2250/34 + 14.117... = 66.176... + 14.117... = 80.294... [W]

        x1, x2 = 60.0, 400.0
        y1, y2 = 30.0, 120.0
        a = (y2 - y1) / (x2 - x1)
        b = y1 - a * x1
        expected_y = a * 250.0 + b
        expected_result = expected_y * 1e-3

        result = get_E_E_fan_d_t(
            ファン消費電力算定方法.直線近似法,
            self.P_fan_rtd, self.V_hs_vent, self.V_hs_supply, self.V_hs_dsgn,
            self.E_E_fan_min, self.region, for_cooling=True
        )
        # 冷房期・中間期の時間帯で計算値を確認
        assert result[self.C][0] == pytest.approx(expected_result)
        assert result[self.M][0] == pytest.approx(expected_result)
        # 暖房期はゼロ
        assert (result[self.H] == 0.0).all()
