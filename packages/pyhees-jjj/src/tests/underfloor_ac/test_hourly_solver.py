import numpy as np
import pytest

import pyhees.section3_1_e as appendix_e
from jjjexperiment.underfloor_ac.hourly_solver import (
    UnderfloorHeatBalance,
    get_runup_floor_temperature,
    run_up_ground_response,
)
from jjjexperiment.underfloor_ac.section3_1_e_jjj import (
    get_Theta_uf_d_t_runup,
)


def test_runup_temperature_matches_appendix_e_equation_13():
    theta_ex = np.linspace(-10.0, 40.0, 24 * 365)

    actual = get_runup_floor_temperature(True, theta_ex)

    np.testing.assert_array_equal(actual, np.clip(theta_ex, 20.0, 27.0))
    np.testing.assert_array_equal(
        actual,
        appendix_e.get_Theta_uf_d_t_runup(True, theta_ex),
    )
    np.testing.assert_array_equal(
        actual,
        get_Theta_uf_d_t_runup(True, theta_ex),
    )
    np.testing.assert_array_equal(
        actual,
        appendix_e._get_new_underfloor_runup_temperature(True, theta_ex),
    )


def test_first_main_hour_ground_response_matches_workbook():
    from pyhees.section11_1 import load_climate

    theta_ex = load_climate(6)["外気温[℃]"].to_numpy()
    theta_g_avg = appendix_e.get_Theta_g_avg(theta_ex)
    theta_uf_runup = get_runup_floor_temperature(True, theta_ex)

    state = run_up_ground_response(theta_uf_runup, theta_g_avg)

    assert float(np.sum(state.response_terms())) == pytest.approx(
        4.133764732220631,
        abs=1e-12,
    )


@pytest.fixture
def first_hour_workbook_heat_balance():
    return UnderfloorHeatBalance(
        air_heat_capacity=901.4672514593672,
        room_conductance=145.40643,
        exterior_conductance=27.91456363309953,
        ground_conductance=372.6959473301369,
        room_weighted_temperature=2908.1286,
        exterior_weighted_temperature=72.5778654461,
        ground_weighted_temperature=7386.7944942628,
    )


def test_pass_1_direct_inverse_matches_first_workbook_hour(
    first_hour_workbook_heat_balance,
):
    actual = first_hour_workbook_heat_balance.required_supply_temperature(
        26.227993170302334,
        heating=True,
    )

    assert actual == pytest.approx(42.01596492017895, abs=1e-12)


def test_pass_2_forward_balance_matches_first_workbook_hour(
    first_hour_workbook_heat_balance,
):
    actual = first_hour_workbook_heat_balance.actual_floor_temperature(
        36.3508199793356
    )

    assert actual == pytest.approx(24.446788350230452, abs=1e-12)
