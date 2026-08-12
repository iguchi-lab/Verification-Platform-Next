import numpy as np
import pytest
from typing import List

from jjjexperiment.common import JJJ_HCM
from jjjexperiment.inputs.climate_service import ClimateService
from jjjexperiment.underfloor_ac.inputs.common import UnderfloorAc

@pytest.mark.usefixtures('climate_entity')
class Test_Input_Climate:

    yaml_filename = "inputs/test_input.yaml"

    def test_get_J_d_t(self, climate_entity):
        """
        get_J_d_t をテスト
        """
        # Act
        J_d_t = climate_entity.get_J_d_t()
        # Assert
        assert J_d_t is not None
        assert np.shape(J_d_t) == (8760,)

    def test_get_X_ex_d_t(self, climate_entity):
        """
        get_X_ex_d_t をテスト
        """
        # Act
        X_ex_d_t = climate_entity.get_X_ex_d_t()
        # Assert
        assert X_ex_d_t is not None
        assert len(X_ex_d_t) == 8760

    def test_get_Theta_ex_d_t(self, climate_entity):
        """
        get_Theta_ex_d_t をテスト
        """
        # Act
        Theta_ex_d_t = climate_entity.get_Theta_ex_d_t()
        # Assert
        assert Theta_ex_d_t is not None
        assert len(Theta_ex_d_t) == 8760

    def test_get_HCM_d_t(self, climate_entity):
        """
        get_HCM_d_t をテスト
        """
        # Act
        HCM_d_t: List[JJJ_HCM] = climate_entity.get_HCM_d_t()
        # Assert
        assert HCM_d_t is not None
        assert len(HCM_d_t) == 8760
        assert all([x is not None for x in HCM_d_t])

    def test_get_g_avg(self, climate_entity):
        """
        get_g_avg をテスト
        """
        # Act
        Theta_g_avg = climate_entity.get_Theta_g_avg()
        # Assert
        assert Theta_g_avg is not None
        assert Theta_g_avg == pytest.approx(15.68, rel=1e-2)

def test_underfloor_constants_are_derived_when_not_explicit():
    climate = ClimateService(6, UnderfloorAc(explicit_constants=False))
    q = 2.647962191872085

    assert climate.get_Theta_g_avg() == pytest.approx(
        15.686130136986295,
        abs=1e-12,
    )
    assert climate.get_U_s_vert(q) == pytest.approx(
        0.5422264459110593,
        abs=1e-12,
    )
    assert climate.get_phi(q) == pytest.approx(
        0.845957617838108,
        abs=1e-12,
    )


def test_explicit_underfloor_constants_only_override_foundation_phi():
    q = 2.647962191872085
    climate = ClimateService(
        6,
        UnderfloorAc(
            Theta_g_avg=14.1,
            U_s_vert=2.223,
            phi=0.91,
            explicit_constants=True,
        ),
    )

    assert climate.get_Theta_g_avg() == pytest.approx(
        15.686130136986295,
        abs=1e-12,
    )
    assert climate.get_U_s_vert(q) == pytest.approx(
        0.5422264459110593,
        abs=1e-12,
    )
    assert climate.get_phi(2.6) == 0.91


def test_underfloor_input_only_accepts_editable_ground_constants():
    underfloor = UnderfloorAc.from_dict({
        "change_underfloor_temperature": 2,
        "input_ufac_consts": 2,
        "Theta_g_avg": 14.1,
        "U_s_vert": 9.9,
        "phi": 0.91,
    })

    assert underfloor.explicit_constants
    assert underfloor.Theta_g_avg == 15.7
    assert underfloor.U_s_vert == 2.223
    assert underfloor.phi == 0.91
