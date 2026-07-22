from types import ModuleType

import jjjexperiment.denchu.denchu_1 as denchu_1
import jjjexperiment.denchu.denchu_2 as denchu_2


EXPECTED_DENCHU_1_REEXPORTS = {
    "ATM_AIR_PRESSURE",
    "BF",
    "C_CatalogSpec",
    "C_RealInnerCondition",
    "Condition",
    "H_CatalogSpec",
    "H_RealInnerCondition",
    "Pa_to_gkgDA",
    "Spec",
    "absolute_humid",
    "avoid_over_saturated",
    "calc_Pa_wexler",
    "calc_R_and_Pc_C",
    "calc_R_and_Pc_H",
    "calc_reibai_phase_T_C",
    "calc_reibai_phase_T_H",
    "dry_air_density",
    "exp",
    "get_Ca",
    "get_DataFrame_denchu_modeling_consts",
    "is_over_saturated",
    "log",
    "log_res",
    "m3ph_to_kgDAps",
    "np",
    "pd",
    "typing",
}

EXPECTED_DENCHU_2_PUBLIC_NAMES = EXPECTED_DENCHU_1_REEXPORTS | {
    "calc_COP_C_d_t",
    "calc_COP_H_d_t",
    "get_Theta_ex",
    "get_X_ex",
    "load_climate",
    "math",
    "simu_COP_C",
    "simu_COP_H",
    "simu_P",
    "simu_R",
}


def _public_names(module: ModuleType) -> set[str]:
    return {name for name in vars(module) if not name.startswith("_")}


def test_denchu_2_public_names_match_legacy_contract():
    assert _public_names(denchu_2) == EXPECTED_DENCHU_2_PUBLIC_NAMES


def test_denchu_2_reexports_denchu_1_objects():
    assert _public_names(denchu_1) == EXPECTED_DENCHU_1_REEXPORTS
    for name in EXPECTED_DENCHU_1_REEXPORTS:
        assert getattr(denchu_2, name) is getattr(denchu_1, name)
