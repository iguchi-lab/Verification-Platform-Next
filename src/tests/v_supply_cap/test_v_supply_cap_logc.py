import numpy as np

from jjjexperiment.inputs.options import Vサプライの上限キャップ
from jjjexperiment.v_supply_cap.cap_V_supply_d_t_i import cap_V_supply_d_t_i
from jjjexperiment.v_supply_cap.inputs.v_supply_cap_dto import VSupplyCapDto


class TestVサプライ上限キャップロジック:

    def test_方式1_設計風量_全室で均一(self):
        result = cap_V_supply_d_t_i(
            V_supply_cap_dto=VSupplyCapDto(Vサプライの上限キャップ.設計風量_全室で均一),
            V_supply_d_t_i=np.repeat(
                np.array([200, 90, 120, 80, 100], dtype=np.float64).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_dash_supply_d_t_i=np.repeat(
                np.array([100, 100, 100, 100, 100]).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_vent_g_i=np.array([20, 20, 20, 20, 20]),
            region=6,
            V_hs_dsgn_H=550,
            V_hs_dsgn_C=580,
        )

        ratio_H = 550 / sum([200, 90, 120, 80, 100])
        ratio_C = 580 / sum([200, 90, 120, 80, 100])

        # 暖房
        assert result[0, 0] == 200 * ratio_H
        assert result[1, 0] == 90 * ratio_H
        assert result[2, 0] == 120 * ratio_H
        assert result[3, 0] == 80 * ratio_H
        assert result[4, 0] == 100 * ratio_H
        # 冷房
        assert result[0, 4000] == 200 * ratio_C
        assert result[1, 4000] == 90 * ratio_C
        assert result[2, 4000] == 120 * ratio_C
        assert result[3, 4000] == 80 * ratio_C
        assert result[4, 4000] == 100 * ratio_C


    def test_方式1_設計風量_風量増室のみ(self):
        result = cap_V_supply_d_t_i(
            V_supply_cap_dto=VSupplyCapDto(Vサプライの上限キャップ.設計風量_風量増室のみ),
            V_supply_d_t_i=np.repeat(
                np.array([200, 90, 120, 80, 100], dtype=np.float64).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_dash_supply_d_t_i=np.repeat(
                np.array([100, 100, 100, 100, 100]).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_vent_g_i=np.array([20, 20, 20, 20, 20]),
            region=6,
            V_hs_dsgn_H=550,
            V_hs_dsgn_C=510,
        )

        # 暖房
        assert result[0, 0] == (200 - 25)
        assert result[1, 0] == 90
        assert result[2, 0] == (120 - 15)
        assert result[3, 0] == 80
        assert result[4, 0] == 100
        # 冷房
        assert result[0, 4000] == (200 - 50)
        assert result[1, 4000] == 90
        assert result[2, 4000] == (120 - 30)
        assert result[3, 4000] == 80
        assert result[4, 4000] == 100


    def test_方式1_設計風量_風量増室のみ_風量が負になる(self):
        result = cap_V_supply_d_t_i(
            V_supply_cap_dto=VSupplyCapDto(Vサプライの上限キャップ.設計風量_風量増室のみ),
            V_supply_d_t_i=np.repeat(
                np.array([210, 190, 170, 180, 120], dtype=np.float64).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_dash_supply_d_t_i=np.repeat(
                np.array([200, 200, 200, 200, 200]).reshape((5, 1)),
                8760,
                axis=1
            ),
            V_vent_g_i=np.array([20, 20, 20, 20, 20]),
            region=6,
            V_hs_dsgn_H=550,
            V_hs_dsgn_C=510,
        )

        # 暖房
        assert result[0, 0] == (210 - (870 - 550))
        assert result[1, 0] == 190
        assert result[2, 0] == 170
        assert result[3, 0] == 180
        assert result[4, 0] == 120
        # 冷房
        assert result[0, 4000] == (210 - (870 - 510))
        assert result[1, 4000] == 190
        assert result[2, 4000] == 170
        assert result[3, 4000] == 180
        assert result[4, 4000] == 120
