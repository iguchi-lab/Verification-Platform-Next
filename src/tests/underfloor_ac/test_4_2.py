import os
import pytest
import numpy as np
# JJJ
from jjjexperiment.inputs.di_container import create_injector_from_json
from jjjexperiment.inputs.common import HouseInfo
from jjjexperiment.inputs.house_service import get_r_A_NR_uf_1F_excl_bath
from jjjexperiment.underfloor_ac.section4_2 import get_A_s_ufac_i
from test_utils.utils import load_input_yaml

class Test_床下空調時_共通:

    def test_床下空調利用時の有効面積と比率(self):
        """
        床下空調利用時の有効面積と比率
        """
        # Arrange
        yaml_fullpath = os.path.join(os.path.dirname(__file__), 'test_input.yaml')
        injector = create_injector_from_json(load_input_yaml(yaml_fullpath))

        house = injector.get(HouseInfo)

        # Act
        A_s_ufac_i, r_A_s_ufac = get_A_s_ufac_i(house.A_A, house.A_MR, house.A_OR)

        # Assert
        assert np.shape(A_s_ufac_i) == (12, 1)
        assert r_A_s_ufac == pytest.approx(65.4/house.A_A, rel=1e-2)

    def test_非居室1F浴室除く面積比(self):
        """
        get_r_A_NR_uf_1F_excl_bath が標準住戸における
        1F非居室(浴室除く)面積 / 非居室合計面積 ≈ 0.404 を返すこと
        """
        # Act
        r = get_r_A_NR_uf_1F_excl_bath()

        # Assert
        # ゾーン6,7,9の有効面積 (3.31+1.66+10.76) / 標準住戸非居室合計 (38.93)
        expected = (3.31 + 1.66 + 10.76) / 38.93  # 0.404
        assert r == pytest.approx(expected, rel=1e-4)
