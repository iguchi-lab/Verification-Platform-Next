import jjjexperiment.common as jjj_common
import jjjexperiment.constants as jjj_constants
import jjjexperiment.logger as jjj_logger
from jjjexperiment.underfloor_ac.inputs.common import UnderfloorAc, UfVarsDataFrame
from jjjexperiment.inputs import options
from pyhees import jjj_runtime

EXPECTED_RUNTIME_CONSTANT_DEFAULTS = {
    "A_e_hex_large_H": 10.6,
    "A_e_hex_small_H": 6.2,
    "A_f_hex_large_H": 0.3,
    "A_f_hex_small_H": 0.2,
    "C_df_H_d_t_defrost_ductcentral": 0.77,
    "C_df_H_d_t_defrost_rac": 0.77,
    "C_hm_C": 1.15,
    "Theta_hs_out_max_H_d_t_limit": 45,
    "Theta_hs_out_min_C_d_t_limit": 15,
    "a_c_hex_c_a0_C": 0.0015,
    "a_c_hex_c_a1_C": 0.0631,
    "a_c_hex_c_a2_C": 0,
    "a_c_hex_c_a3_C": 0,
    "a_c_hex_c_a4_C": 0,
    "airvolume_coeff_a0_C": 10.209,
    "airvolume_coeff_a0_H": 12.084,
    "airvolume_coeff_a1_C": 2.4855,
    "airvolume_coeff_a1_H": 1.2946,
    "airvolume_coeff_a2_C": 0,
    "airvolume_coeff_a2_H": 0,
    "airvolume_coeff_a3_C": 0,
    "airvolume_coeff_a3_H": 0,
    "airvolume_coeff_a4_C": 0,
    "airvolume_coeff_a4_H": 0,
    "airvolume_maximum_C": 24.3824,
    "airvolume_maximum_H": 24.3824,
    "airvolume_minimum_C": 14.38995,
    "airvolume_minimum_H": 14.38995,
    "change_heat_source_outlet_required_temperature": 1,
    "defrost_humid_ductcentral": 80,
    "defrost_humid_rac": 80,
    "defrost_temp_ductcentral": 5,
    "defrost_temp_rac": 5,
    "phi_i": 0.49,
    "q_rtd_C_limit": 5600,
}

def test_cross_boundary_enums_are_reexported_without_copying():
    assert options.計算モデル is jjj_runtime.計算モデル
    assert options.床下空調ロジック is jjj_runtime.床下空調ロジック
    assert (
        options.ファン消費電力から換気分を引く
        is jjj_runtime.ファン消費電力から換気分を引く
    )


def test_cross_boundary_enum_values_remain_stable():
    assert {member.value for member in options.計算モデル} == {1, 2, 3, 4}
    assert {member.value for member in options.床下空調ロジック} == {1, 2}
    assert {
        member.value for member in options.ファン消費電力から換気分を引く
    } == {1, 2}

def test_runtime_constant_defaults_match_jjj_defaults():
    assert jjj_runtime._DEFAULT_CONSTANTS == EXPECTED_RUNTIME_CONSTANT_DEFAULTS
    assert {
        name: getattr(jjj_constants, name)
        for name in EXPECTED_RUNTIME_CONSTANT_DEFAULTS
    } == EXPECTED_RUNTIME_CONSTANT_DEFAULTS


def test_runtime_constant_provider_tracks_direct_assignments(monkeypatch):
    overrides = {
        "Theta_hs_out_max_H_d_t_limit": 48.5,
        "a_c_hex_c_a1_C": 0.081,
        "q_rtd_C_limit": 6100,
    }

    for name, value in overrides.items():
        monkeypatch.setattr(jjj_constants, name, value)
        assert jjj_runtime.get_constant(name) == value

def test_runtime_logging_preserves_result_metadata_and_dynamic_handler():
    events = []
    jjj_runtime.set_result_logger(
        lambda function, result, labels: events.append(
            (function.__name__, result, labels)
        )
    )

    try:
        @jjj_runtime.log_res(["value"])
        def sample(value):
            return value + 1

        assert sample.__name__ == "sample"
        assert sample(4) == 5
        assert events == [("sample", 5, ["value"])]
    finally:
        jjj_runtime.set_result_logger(jjj_logger._record_result)


def test_underfloor_context_resolver_preserves_explicit_values():
    new_ufac = object()
    new_ufac_df = object()

    assert jjj_runtime.resolve_underfloor_context(new_ufac, new_ufac_df) == (
        new_ufac,
        new_ufac_df,
    )


def test_underfloor_context_resolver_fills_only_missing_values():
    configured_ufac = object()
    configured_frame = object()
    values = {UnderfloorAc: configured_ufac, UfVarsDataFrame: configured_frame}

    class FakeInjector:
        def get(self, key):
            return values[key]

    explicit_ufac = object()
    with jjj_common.injector_context(FakeInjector()):
        assert jjj_runtime.resolve_underfloor_context(None, None) == (
            configured_ufac,
            configured_frame,
        )
        assert jjj_runtime.resolve_underfloor_context(explicit_ufac, None) == (
            explicit_ufac,
            configured_frame,
        )
