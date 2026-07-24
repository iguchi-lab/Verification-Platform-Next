import numpy as np
import pytest

import pyhees.section2_2 as section2_2
import pyhees.section2_3 as section2_3
import pyhees.section2_4 as section2_4
import pyhees.section2_5 as section2_5
import pyhees.section4_8 as section4_8
import pyhees.section7_4 as section7_4
import pyhees.section9_3 as section9_3
from pyhees.util import util


def test_convert_to_gj_ignores_floating_point_noise_at_tenth_boundary():
    assert util.convert_to_gj(1200.0000001) == 1.2
    assert util.convert_to_gj(1200.001) == 1.3


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (section2_2.get_E_T_gn_du, (1200.0000001, 0, 0, 0, 0, 0, 0)),
        (section2_3.get_E_ST_gn_du_p, (1200.0000001, 0, 0, 0, 0, 0)),
        (section2_5.get_E_dash_T_gn_rdu, (1200.0000001,)),
    ],
)
def test_primary_energy_results_use_ver_3_10_gj_conversion(function, args):
    result = function(*args)
    if isinstance(result, tuple):
        result = result[0]
    assert result == 1.2


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [
        (1.2, 1.0, 1.2),
        (1.2000000001, 1.0, 1.2),
        (1.201, 1.0, 1.21),
    ],
)
def test_bei_uses_ver_3_10_decimal_ceiling(numerator, denominator, expected):
    assert section2_4.get_BEI_gn_du(numerator, denominator) == expected


def test_rac_floor_heating_auxiliary_power_uses_ver_3_10_formulas():
    q_out = np.full(24 * 365, 2.0)
    rac_demand = np.zeros(24 * 365)
    rac_demand[1] = 1.0

    result = section4_8.get_E_aux_hs_d_t(q_out, rac_demand)

    assert result[0] == pytest.approx(0.0037 * 2.0 + 0.0801)
    assert result[1] == pytest.approx(0.0139 * 2.0 + 0.0805)


@pytest.mark.parametrize(
    ("rated_efficiency", "expected"),
    [
        (2.0, 2.7),
        (3.0, 3.0),
        (4.0, 3.6),
    ],
)
def test_heat_pump_water_heater_efficiency_is_limited(rated_efficiency, expected):
    assert section7_4.get_e_rtd(rated_efficiency) == expected


def test_air_collector_undefined_heat_loss_returns_outdoor_temperature():
    assert np.isnan(section9_3.get_U_c_j(m_fan_test_j=0.001, d1_j=2.0))

    outdoor = np.array([-5.0, 10.0])
    result = section9_3.get_Theta_col_opg_j_d_t(
        V_col_j_d_t=np.array([100.0, 100.0]),
        A_col_j=1.0,
        U_c_j=np.nan,
        Theta_col_nonopg_j_d_t=np.array([20.0, 25.0]),
        Theta_ex_d_t=outdoor,
    )

    assert result is outdoor
