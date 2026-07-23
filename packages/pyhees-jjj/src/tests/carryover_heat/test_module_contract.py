import importlib
import inspect

import jjjexperiment.carryover_heat as carryover_heat
from jjjexperiment.carryover_heat import section4_2_jjj


EXPECTED_FUNCTIONS = (
    "_prepare_carryover_zone_areas",
    "_get_carryover_C_BR_i",
    "_get_carryover_temperature_diff",
    "_calculate_carryover_result",
    "calc_carryover",
    "get_L_star_H_i_2024",
    "get_L_star_CS_i_2024",
    "_assert_Theta_HBR_i_2023_shapes",
    "_get_c_prt_46",
    "_get_heat_loss_46",
    "_get_C_BR_i_46",
    "_get_ac_capacity_46",
    "_get_Theta_HBR_i_46",
    "_return_Theta_HBR_i_46",
    "get_Theta_HBR_i_2023",
    "_assert_Theta_NR_2023_shapes",
    "_get_c_prt_48",
    "_get_air_properties_48",
    "_get_k_prt_dash_i_48",
    "_get_k_prt_i_48",
    "_get_k_evp_48",
    "_get_balance_terms_48",
    "_get_carryover_state_48",
    "_get_Theta_NR_48",
    "get_Theta_NR_2023",
)

PUBLIC_FUNCTIONS = (
    "calc_carryover",
    "get_L_star_H_i_2024",
    "get_L_star_CS_i_2024",
    "get_Theta_HBR_i_2023",
    "get_Theta_NR_2023",
)


def test_section4_2_preserves_25_function_boundaries():
    actual = tuple(
        name
        for name, value in vars(section4_2_jjj).items()
        if inspect.isfunction(value) and value.__module__ == section4_2_jjj.__name__
    )

    assert actual == EXPECTED_FUNCTIONS


def test_carryover_package_preserves_public_function_objects():
    for name in PUBLIC_FUNCTIONS:
        assert getattr(carryover_heat, name) is getattr(section4_2_jjj, name)

def test_legacy_section4_2_import_is_the_jjj_implementation_module():
    legacy = importlib.import_module("jjjexperiment.carryover_heat.section4_2")

    assert legacy is section4_2_jjj
    for name in EXPECTED_FUNCTIONS:
        assert getattr(legacy, name) is getattr(section4_2_jjj, name)