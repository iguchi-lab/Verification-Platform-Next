import ast
from pathlib import Path

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

EXPECTED_SECTION4_2_A_MAIN_API = {
    "calc_E_E_C_d_t_type1_and_type3",
    "calc_E_E_C_d_t_type2",
    "calc_E_E_C_d_t_type4",
    "calc_E_E_H_d_t_type1_and_type3",
    "calc_E_E_H_d_t_type2",
    "calc_E_E_H_d_t_type4",
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


def test_main_section4_2_a_api_contract():
    assert _accessed_attributes("jjj_dc_a") == EXPECTED_SECTION4_2_A_MAIN_API
    assert all(hasattr(main.jjj_dc_a, name) for name in EXPECTED_SECTION4_2_A_MAIN_API)
