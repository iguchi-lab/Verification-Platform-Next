import ast
import importlib
import inspect
from pathlib import Path

import pytest

from jjjexperiment import main


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
JJJEXPERIMENT_MAIN = (
    REPOSITORY_ROOT / "packages" / "pyhees-jjj" / "src" / "jjjexperiment" / "main.py"
)

EXPECTED_SECTION4_2_MAIN_API = {
    "ActiveAcSetting",
    "Load_DTI",
    "VHS_DSGN_C",
    "VHS_DSGN_H",
    "calc_Q_UT_A",
}

EXPECTED_CALC_Q_UT_A_PARAMETERS = (
    "case_name",
    "climateFile",
    "house",
    "ac_setting",
    "skin",
    "heat_CRAC",
    "cool_CRAC",
    "new_ufac",
    "new_ufac_df",
    "v_min_heat_input",
    "v_min_cool_input",
    "V_hs_dsgn_H",
    "V_hs_dsgn_C",
    "v_supply_cap_dto",
    "carryover_heat_dto",
    "load",
)

EXPECTED_SECTION4_2_A_MAIN_API = {
    "calc_E_E_C_d_t_type1_and_type3",
    "calc_E_E_C_d_t_type2",
    "calc_E_E_C_d_t_type4",
    "calc_E_E_H_d_t_type1_and_type3",
    "calc_E_E_H_d_t_type2",
    "calc_E_E_H_d_t_type4",
}

EXPECTED_UNDERFLOOR_SECTION_API = {
    "section3_1_e": {
        "THETA_UF_COOL",
        "THETA_UF_WARM",
        "calc_Theta_uf_d_t_2023",
        "calc_sum_Theta_dash_g_surf_A_m_runup",
        "get_Theta_uf_d_t_runup",
    },
    "section4_2": {
        "calc_Theta_uf",
        "calc_delta_L_room2uf_i",
        "calc_delta_L_uf2gnd",
        "calc_delta_L_uf2outdoor",
        "get_A_s_ufac_i",
        "get_r_A_NR_uf_1F_excl_bath",
        "get_r_A_uf_i",
    },
    "section4_2_f40": {"calc_Q_hat_hs"},
    "section4_2_f46_f48": {"get_Theta_HBR_i", "get_Theta_NR"},
    "section4_2_f52": {"get_Theta_star_NR"},
}


def _accessed_attributes(alias: str) -> set[str]:
    tree = ast.parse(
        JJJEXPERIMENT_MAIN.read_text(encoding="utf-8"),
        filename=str(JJJEXPERIMENT_MAIN),
    )
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == alias
    }


def test_main_section4_2_api_contract():
    assert _accessed_attributes("jjj_dc") == EXPECTED_SECTION4_2_MAIN_API
    assert all(hasattr(main.jjj_dc, name) for name in EXPECTED_SECTION4_2_MAIN_API)


def test_calc_q_ut_a_signature_contract():
    assert tuple(inspect.signature(main.jjj_dc.calc_Q_UT_A).parameters) == (
        EXPECTED_CALC_Q_UT_A_PARAMETERS
    )


def test_legacy_section4_2_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.section4_2")
    implementation = importlib.import_module("jjjexperiment.section4_2_jjj")

    assert legacy is implementation
    assert main.jjj_dc is implementation


def test_main_section4_2_a_api_contract():
    assert _accessed_attributes("jjj_dc_a") == EXPECTED_SECTION4_2_A_MAIN_API
    assert all(hasattr(main.jjj_dc_a, name) for name in EXPECTED_SECTION4_2_A_MAIN_API)


def _starred_context_name_for_call(function_name: str) -> str:
    tree = ast.parse(
        JJJEXPERIMENT_MAIN.read_text(encoding="utf-8"),
        filename=str(JJJEXPERIMENT_MAIN),
    )
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == function_name
    ]
    assert len(calls) == 1
    call = calls[0]
    assert call.keywords == []
    assert len(call.args) == 1
    assert isinstance(call.args[0], ast.Starred)
    context = call.args[0].value
    assert isinstance(context, ast.Call)
    assert isinstance(context.func, ast.Name)
    return context.func.id


def test_heating_type1_and3_call_uses_signature_order_context():
    assert _starred_context_name_for_call(
        "calc_E_E_H_d_t_type1_and_type3"
    ) == "_HeatingType1And3ElectricityInputs"


def test_legacy_section4_2_a_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.section4_2_a")
    implementation = importlib.import_module("jjjexperiment.section4_2_a_jjj")

    assert legacy is implementation
    assert main.jjj_dc_a is implementation


@pytest.mark.parametrize(
    ("module_name", "expected_api"),
    EXPECTED_UNDERFLOOR_SECTION_API.items(),
)
def test_underfloor_section_module_api_contract(module_name, expected_api):
    module = importlib.import_module(f"jjjexperiment.underfloor_ac.{module_name}")

    assert all(hasattr(module, name) for name in expected_api)


def test_legacy_underfloor_section3_1_e_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.underfloor_ac.section3_1_e")
    implementation = importlib.import_module(
        "jjjexperiment.underfloor_ac.section3_1_e_jjj"
    )

    assert legacy is implementation


def test_legacy_underfloor_section4_2_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.underfloor_ac.section4_2")
    implementation = importlib.import_module(
        "jjjexperiment.underfloor_ac.section4_2_jjj"
    )

    assert legacy is implementation


def test_legacy_underfloor_section4_2_f40_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.underfloor_ac.section4_2_f40")
    implementation = importlib.import_module(
        "jjjexperiment.underfloor_ac.section4_2_f40_jjj"
    )

    assert legacy is implementation


def test_legacy_underfloor_section4_2_f46_f48_import_aliases_jjj_module():
    legacy = importlib.import_module(
        "jjjexperiment.underfloor_ac.section4_2_f46_f48"
    )
    implementation = importlib.import_module(
        "jjjexperiment.underfloor_ac.section4_2_f46_f48_jjj"
    )

    assert legacy is implementation


def test_legacy_underfloor_section4_2_f52_import_aliases_jjj_module():
    legacy = importlib.import_module("jjjexperiment.underfloor_ac.section4_2_f52")
    implementation = importlib.import_module(
        "jjjexperiment.underfloor_ac.section4_2_f52_jjj"
    )

    assert legacy is implementation
