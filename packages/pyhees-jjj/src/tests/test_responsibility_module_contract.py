import inspect

import numpy as np
import pytest

import jjjexperiment.constants as jjj_consts
from jjjexperiment.inputs.options import ファン消費電力算定方法
import jjjexperiment.latent_load.compressor_efficiency as latent_compressor
import jjjexperiment.latent_load.fan_power as latent_fan
import jjjexperiment.v_min_input.fan_power as v_min_fan


def _parameter_names(function):
    return tuple(inspect.signature(function).parameters)


def test_latent_load_public_signatures_are_stable():
    assert _parameter_names(latent_compressor.get_e_r_H_d_t) == ("q_hs_H_d_t",)
    assert _parameter_names(latent_compressor.get_e_r_C_d_t) == ("q_hs_C_d_t",)
    assert _parameter_names(latent_fan.get_E_E_fan_H_d_t) == (
        "V_hs_vent_d_t",
        "q_hs_H_d_t",
        "f_SFP",
    )
    assert _parameter_names(latent_fan.get_E_E_fan_C_d_t) == (
        "V_hs_vent_d_t",
        "q_hs_C_d_t",
        "f_SFP",
    )


@pytest.mark.parametrize(
    ("function", "coefficient_names"),
    [
        (
            latent_compressor.get_e_r_H_d_t,
            ("a_r_H_t_t_a4", "a_r_H_t_t_a3", "a_r_H_t_t_a2", "a_r_H_t_t_a1", "a_r_H_t_t_a0"),
        ),
        (
            latent_compressor.get_e_r_C_d_t,
            ("a_r_C_t_t_a4", "a_r_C_t_t_a3", "a_r_C_t_t_a2", "a_r_C_t_t_a1", "a_r_C_t_t_a0"),
        ),
    ],
)
def test_latent_load_compressor_efficiency_preserves_polynomial(function, coefficient_names):
    q_hs_d_t = np.array([0.0, 1000.0, 2500.0])
    x = q_hs_d_t / 1000
    a4, a3, a2, a1, a0 = (
        getattr(jjj_consts, coefficient_name) for coefficient_name in coefficient_names
    )

    actual = function(q_hs_d_t)

    np.testing.assert_array_equal(
        actual,
        a4 * x**4 + a3 * x**3 + a2 * x**2 + a1 * x + a0,
    )


def test_v_min_public_and_solver_signatures_are_stable():
    assert _parameter_names(v_min_fan.get_E_E_fan_d_t) == (
        "E_E_fan_logic",
        "P_fan_rtd",
        "V_hs_vent_d_t",
        "V_hs_supply_d_t",
        "V_hs_dsgn",
        "E_E_fan_min",
        "region",
        "for_cooling",
    )
    assert _parameter_names(v_min_fan._solve_linear_system) == ("x1", "x2", "y1", "y2")
    assert _parameter_names(v_min_fan._solve_cubic_system) == ("x1", "x2", "y1", "y2")


def test_v_min_linear_and_cubic_solvers_preserve_endpoints():
    x1 = np.array([100.0, 200.0])
    x2 = 500.0
    y1 = 50.0
    y2 = 250.0

    linear_a, linear_b = v_min_fan._solve_linear_system(x1, x2, y1, y2)
    cubic_a, cubic_b = v_min_fan._solve_cubic_system(x1, x2, y1, y2)

    np.testing.assert_allclose(linear_a * x1 + linear_b, y1)
    np.testing.assert_allclose(linear_a * x2 + linear_b, y2)
    np.testing.assert_allclose(cubic_a * x1**3 + cubic_b, y1)
    np.testing.assert_allclose(cubic_a * x2**3 + cubic_b, y2)


def test_v_min_invalid_fan_logic_preserves_exception():
    values = np.zeros(24 * 365)

    with pytest.raises(ValueError, match="^Invalid E_E_fan_logic$"):
        v_min_fan.get_E_E_fan_d_t(
            E_E_fan_logic=object(),
            P_fan_rtd=200.0,
            V_hs_vent_d_t=values,
            V_hs_supply_d_t=values,
            V_hs_dsgn=500.0,
            E_E_fan_min=50.0,
            region=6,
            for_cooling=False,
        )


@pytest.mark.parametrize(
    "logic",
    [ファン消費電力算定方法.直線近似法, ファン消費電力算定方法.風量三乗近似法],
)
def test_v_min_fan_power_preserves_shape_and_nonnegative_result(logic):
    ventilation = np.full(24 * 365, 100.0)
    supply = np.full(24 * 365, 300.0)

    actual = v_min_fan.get_E_E_fan_d_t(
        E_E_fan_logic=logic,
        P_fan_rtd=250.0,
        V_hs_vent_d_t=ventilation,
        V_hs_supply_d_t=supply,
        V_hs_dsgn=500.0,
        E_E_fan_min=50.0,
        region=6,
        for_cooling=False,
    )

    assert actual.shape == (24 * 365,)
    assert np.all(actual >= 0)
