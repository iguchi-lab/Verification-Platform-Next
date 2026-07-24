from types import SimpleNamespace

import numpy as np

import jjjexperiment.section4_2_jjj as sut


def _fixed(events, name, result):
    def replacement(*args):
        events.append((name, args))
        return result

    return replacement


def test_prepare_calculation_pre_branch_state_preserves_phase_order(monkeypatch):
    events = []
    preparation = SimpleNamespace(
        df_output="initial-frame",
        df_output2="frame-2",
        climate="climate",
        A_HCZ_i="areas",
        V_hs_dsgn_H="design-h",
        V_hs_dsgn_C="design-c",
        V_hs_min="minimum",
        Q_hs_rtd_H="rated-h",
        Q_hs_rtd_C="rated-c",
        Q_hat_hs_d_t="output",
        Q_hat_hs_CS_d_t="sensible-output",
        V_vent_g_i="general-airflow",
        Theta_ex_d_t="outdoor-temperature",
        X_star_HBR_d_t="balanced-room-humidity",
        L_wtr="water-load",
        V_vent_l_NR_d_t="local-airflow",
        A_NR="non-room-area",
        A_prt_i="partition-area",
        U_prt="partition-u",
        Theta_star_HBR_d_t="balanced-room-temperature",
        Theta_sur_d_t_i="duct-temperature",
    )
    pre_vav = sut._PreVavAirflowStateResult(
        "underfloor-area",
        "underfloor-temperature",
        "supply-ratio",
        "hourly-supply-ratio",
        "supply-airflow",
        "pre-vav-frame",
    )
    monkeypatch.setattr(
        sut,
        "_prepare_calculation_state",
        _fixed(events, "calculation", preparation),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_underfloor_adjustment_state",
        _fixed(
            events,
            "underfloor",
            ("indoor-temperature", "phi", "ground-average", "ground-sum", True),
        ),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_pre_vav_airflow_state",
        _fixed(events, "pre-vav", pre_vav),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_balanced_non_room_humidity",
        _fixed(events, "balanced-humidity", "balanced-non-room-humidity"),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_balanced_non_room_temperature",
        _fixed(events, "balanced-temperature", ("balanced-non-room-temperature", 0.4)),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_actual_humidity_state",
        _fixed(events, "actual-humidity", ("non-room-humidity", "room-humidity", "humidity-frame")),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_balanced_load_state",
        _fixed(events, "balanced-load", ("partition-load", "latent-load", "load-frame")),
    )

    inputs = sut._CalculationPreBranchInputs(
        SimpleNamespace(region=6),
        *range(1, 12),
    )
    actual = sut._prepare_calculation_pre_branch_state(inputs)

    assert [name for name, _ in events] == [
        "calculation",
        "underfloor",
        "pre-vav",
        "balanced-humidity",
        "balanced-temperature",
        "actual-humidity",
        "balanced-load",
    ]
    assert actual == sut._CalculationPreBranchResult(
        preparation,
        pre_vav._replace(df_output="load-frame"),
        "indoor-temperature",
        "balanced-non-room-humidity",
        "balanced-non-room-temperature",
        0.4,
        "non-room-humidity",
        "room-humidity",
        "latent-load",
        "partition-load",
    )


def test_run_no_carryover_calculation_preserves_phase_order_and_result(monkeypatch):
    events = []
    capacity = sut._CapacityStateResult(*[f"capacity-{index}" for index in range(18)])
    supply = sut._SupplyStateResult(*[f"supply-{index}" for index in range(7)])
    preparation = SimpleNamespace(
        Theta_star_HBR_d_t="balanced-room-temperature",
        Theta_ex_d_t="outdoor-temperature",
        climate="climate",
        h_ex_d_t="outdoor-humidity",
        Theta_sur_d_t_i="duct-temperature",
        l_duct_i="duct-length",
        V_vent_g_i="general-airflow",
        V_hs_dsgn_H="design-h",
        V_hs_dsgn_C="design-c",
        U_prt="partition-u",
        A_prt_i="partition-area",
        A_HCZ_i="areas",
        A_NR="non-room-area",
        V_vent_l_NR_d_t="local-airflow",
        X_star_HBR_d_t="balanced-room-humidity",
    )
    pre_vav = SimpleNamespace(
        A_s_ufac_i="underfloor-area",
        V_dash_supply_d_t_i="pre-vav-airflow",
        Theta_uf_d_t="underfloor-temperature",
    )
    pre_branch = sut._CalculationPreBranchResult(
        preparation,
        pre_vav,
        "indoor-temperature",
        "balanced-non-room-humidity",
        "balanced-non-room-temperature",
        "underfloor-ratio",
        "non-room-humidity",
        "room-humidity",
        "latent-load",
        "partition-load",
    )
    monkeypatch.setattr(
        sut,
        "_prepare_no_carryover_balanced_loads",
        _fixed(events, "balanced-loads", ("heating-load", "sensible-load")),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_no_carryover_capacity_state",
        _fixed(events, "capacity", capacity),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_balanced_heat_source_inlet_state",
        _fixed(events, "inlet", ("inlet-humidity", "inlet-temperature")),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_no_carryover_outlet_requirements",
        _fixed(events, "requirements", ("minimum-humidity", "required-humidity", "required-temperature")),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_no_carryover_supply_state",
        _fixed(events, "supply", supply),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_no_carryover_actual_temperature_state",
        _fixed(events, "actual-temperature", ("room-temperature", "non-room-temperature")),
    )

    actual = sut._run_no_carryover_calculation(
        sut._NoCarryoverCalculationInputs(
            "setting",
            SimpleNamespace(region=6),
            "skin",
            "heat-spec",
            "cool-spec",
            "underfloor",
            "underfloor-frame",
            "supply-cap",
            "load",
            pre_branch,
        )
    )

    assert [name for name, _ in events] == [
        "balanced-loads",
        "capacity",
        "inlet",
        "requirements",
        "supply",
        "actual-temperature",
    ]
    assert actual == sut._CalculationBranchResult(
        capacity,
        supply,
        "heating-load",
        "sensible-load",
        "inlet-humidity",
        "inlet-temperature",
        "minimum-humidity",
        "required-humidity",
        "required-temperature",
        "room-temperature",
        "non-room-temperature",
        None,
    )


def test_run_carryover_calculation_preserves_8760_hour_order(monkeypatch):
    hours = []
    first_flags = []
    call_counts = {
        "balanced": 0,
        "capacity": 0,
        "inlet": 0,
        "requirements": 0,
        "supply": 0,
        "temperature": 0,
    }
    L_star_CS_d_t_i = np.zeros((5, 8760))
    L_star_H_d_t_i = np.zeros((5, 8760))
    Theta_HBR_d_t_i = np.zeros((5, 8760))
    Theta_NR_d_t = np.zeros(8760)
    carryovers = np.zeros((5, 8760))
    hourly_state = sut._CarryoverHourlyStateResult(
        L_star_CS_d_t_i,
        L_star_H_d_t_i,
        "initial-inlet-temperature",
        Theta_HBR_d_t_i,
        Theta_NR_d_t,
        carryovers,
        "heating-season",
        "cooling-season",
        "middle-season",
    )
    capacity = sut._CapacityStateResult(*[f"capacity-{index}" for index in range(18)])
    supply = sut._SupplyStateResult(*[f"supply-{index}" for index in range(7)])
    preparation = SimpleNamespace(
        A_HCZ_i="areas",
        Theta_star_HBR_d_t="balanced-room-temperature",
        Theta_ex_d_t="outdoor-temperature",
        h_ex_d_t="outdoor-humidity",
        Theta_sur_d_t_i="duct-temperature",
        l_duct_i="duct-length",
        V_vent_g_i="general-airflow",
        V_hs_dsgn_H="design-h",
        V_hs_dsgn_C="design-c",
        U_prt="partition-u",
        A_prt_i="partition-area",
        A_NR="non-room-area",
        V_vent_l_NR_d_t="local-airflow",
        X_star_HBR_d_t="balanced-room-humidity",
    )
    pre_branch = sut._CalculationPreBranchResult(
        preparation,
        SimpleNamespace(V_dash_supply_d_t_i="pre-vav-airflow"),
        "indoor-temperature",
        "balanced-non-room-humidity",
        "balanced-non-room-temperature",
        "underfloor-ratio",
        "non-room-humidity",
        "room-humidity",
        "latent-load",
        "partition-load",
    )

    monkeypatch.setattr(
        sut,
        "_initialize_carryover_hourly_state",
        lambda region: hourly_state,
    )

    def carryover_at_hour(inputs):
        hours.append(inputs.t)
        return np.full((5, 1), inputs.t, dtype=float)

    def balanced_loads(inputs):
        call_counts["balanced"] += 1
        return (
            np.full((5, 1), inputs.t + 1, dtype=float),
            np.full((5, 1), inputs.t + 2, dtype=float),
        )

    def inlet_state(inputs):
        call_counts["inlet"] += 1
        first_flags.append(inputs.isFirst)
        return "inlet-humidity", "inlet-temperature"

    def fixed_count(name, result):
        def replacement(inputs):
            call_counts[name] += 1
            return result

        return replacement

    monkeypatch.setattr(sut, "_get_carryover_at_hour", carryover_at_hour)
    monkeypatch.setattr(sut, "_get_balanced_loads_at_hour", balanced_loads)
    monkeypatch.setattr(
        sut,
        "_prepare_carryover_capacity_state",
        fixed_count("capacity", capacity),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_carryover_heat_source_inlet_state",
        inlet_state,
    )
    monkeypatch.setattr(
        sut,
        "_prepare_carryover_outlet_requirements",
        fixed_count(
            "requirements",
            ("minimum-humidity", "required-humidity", "required-temperature"),
        ),
    )
    monkeypatch.setattr(
        sut,
        "_prepare_carryover_supply_state",
        fixed_count("supply", supply),
    )
    monkeypatch.setattr(
        sut,
        "_update_carryover_actual_temperature_state",
        fixed_count("temperature", (Theta_HBR_d_t_i, Theta_NR_d_t)),
    )

    actual = sut._run_carryover_calculation(
        sut._CarryoverCalculationPhaseInputs(
            "setting",
            SimpleNamespace(region=6),
            SimpleNamespace(Q="heat-loss"),
            "heat-spec",
            "cool-spec",
            "supply-cap",
            "load",
            pre_branch,
        )
    )

    assert hours == list(range(8760))
    assert first_flags[0] is True
    assert all(flag is False for flag in first_flags[1:])
    assert call_counts == {
        "balanced": 8760,
        "capacity": 8760,
        "inlet": 8760,
        "requirements": 8760,
        "supply": 8760,
        "temperature": 8760,
    }
    np.testing.assert_array_equal(carryovers[:, 0], np.zeros(5))
    np.testing.assert_array_equal(carryovers[:, -1], np.full(5, 8759))
    np.testing.assert_array_equal(L_star_H_d_t_i[:, 0], np.ones(5))
    np.testing.assert_array_equal(L_star_CS_d_t_i[:, -1], np.full(5, 8761))
    assert actual.capacity_state is capacity
    assert actual.supply_state is supply
    assert actual.carryovers is carryovers

def test_finalize_calculation_outputs_preserves_common_output_order(monkeypatch):
    events = []
    preparation = SimpleNamespace(
        df_output2="frame-2",
        df_output3="frame-3",
        df_carryover_output="carryover-frame",
        X_star_HBR_d_t="balanced-room-humidity",
        V_vent_g_i="general-airflow",
    )
    pre_branch = sut._CalculationPreBranchResult(
        preparation,
        SimpleNamespace(df_output="initial-frame", V_dash_supply_d_t_i="pre-vav-airflow"),
        "indoor-temperature",
        "balanced-non-room-humidity",
        "balanced-non-room-temperature",
        "underfloor-ratio",
        "non-room-humidity",
        "room-humidity",
        "latent-load",
        "partition-load",
    )
    capacity = sut._CapacityStateResult(*[f"capacity-{index}" for index in range(18)])
    supply = sut._SupplyStateResult(*[f"supply-{index}" for index in range(7)])
    branch = sut._CalculationBranchResult(
        capacity,
        supply,
        "heating-load",
        "sensible-load",
        "inlet-humidity-balanced",
        "inlet-temperature-balanced",
        "minimum-humidity",
        "required-humidity",
        "required-temperature",
        "room-temperature",
        "non-room-temperature",
        "carryovers",
    )
    replacements = (
        ("_log_actual_temperature_state", "log", None),
        ("_export_carryover_diagnostics", "carryover-export", None),
        ("_record_balanced_load_outputs", "balanced-output", "balanced-frame"),
        ("_record_capacity_state_outputs", "capacity-output", ("capacity-frame", "capacity-frame-3")),
        ("_record_common_outlet_and_supply_outputs", "outlet-output", "outlet-frame"),
        ("_prepare_heat_source_outlet_temperature_output", "outlet-temperature", ("outlet-temperature", "outlet-temperature-frame")),
        ("_prepare_supply_humidity_output", "supply-humidity", ("supply-humidity", "supply-humidity-frame")),
        ("_prepare_heat_source_ventilation_airflow_output", "ventilation-airflow", ("ventilation-airflow", "ventilation-frame")),
        ("_prepare_heat_source_supply_airflow_output", "supply-airflow", ("supply-airflow", "supply-airflow-frame")),
        ("_prepare_heat_source_inlet_humidity_output", "inlet-humidity", ("inlet-humidity", "inlet-humidity-frame")),
        ("_prepare_heat_source_inlet_temperature_output", "inlet-temperature", ("inlet-temperature", "inlet-temperature-frame")),
        ("_prepare_actual_load_state", "actual-load", ("actual-latent", "actual-sensible", "actual-heating", "actual-frame")),
        ("_prepare_unprocessed_load_state", "unprocessed-load", ("unprocessed-latent", "unprocessed-sensible", "unprocessed-heating", "unprocessed-frame")),
        ("_prepare_unprocessed_energy_state", "energy", ("energy", "energy-frame")),
        ("_export_and_build_calculation_result", "export", "calculation-result"),
    )
    for attribute, name, result in replacements:
        monkeypatch.setattr(sut, attribute, _fixed(events, name, result))

    actual = sut._finalize_calculation_outputs(
        sut._CalculationOutputPhaseInputs(
            "case",
            SimpleNamespace(general_ventilation=True),
            SimpleNamespace(region=6),
            "underfloor",
            "underfloor-frame",
            "carryover-setting",
            pre_branch,
            branch,
        )
    )

    assert [name for name, _ in events] == [
        "log",
        "carryover-export",
        "balanced-output",
        "capacity-output",
        "outlet-output",
        "outlet-temperature",
        "supply-humidity",
        "ventilation-airflow",
        "supply-airflow",
        "inlet-humidity",
        "inlet-temperature",
        "actual-load",
        "unprocessed-load",
        "energy",
        "export",
    ]
    export_inputs = events[-1][1][0]
    assert export_inputs.df_output == "energy-frame"
    assert export_inputs.df_output2 == "frame-2"
    assert export_inputs.df_output3 == "capacity-frame-3"
    assert actual == "calculation-result"


def test_calc_q_ut_a_selects_branch_then_finalizes(monkeypatch):
    pre_branch = object()
    carryover_branch = object()
    no_carryover_branch = object()
    events = []
    monkeypatch.setattr(
        sut,
        "_prepare_calculation_pre_branch_state",
        _fixed(events, "prepare", pre_branch),
    )
    monkeypatch.setattr(
        sut,
        "_run_carryover_calculation",
        _fixed(events, "carryover", carryover_branch),
    )
    monkeypatch.setattr(
        sut,
        "_run_no_carryover_calculation",
        _fixed(events, "no-carryover", no_carryover_branch),
    )
    monkeypatch.setattr(
        sut,
        "_finalize_calculation_outputs",
        _fixed(events, "finalize", "result"),
    )

    common = [
        "case",
        "climate",
        "house",
        "setting",
        "skin",
        "heat-spec",
        "cool-spec",
        "underfloor",
        "underfloor-frame",
        "minimum-h",
        "minimum-c",
        "design-h",
        "design-c",
        "supply-cap",
    ]
    carryover = SimpleNamespace(carry_over_heat=sut.過剰熱量繰越計算.行う)
    assert sut.calc_Q_UT_A(*common, carryover, "load") == "result"
    assert [name for name, _ in events] == ["prepare", "carryover", "finalize"]
    assert events[-1][1][0].branch is carryover_branch

    events.clear()
    no_carryover = SimpleNamespace(carry_over_heat=object())
    assert sut.calc_Q_UT_A(*common, no_carryover, "load") == "result"
    assert [name for name, _ in events] == ["prepare", "no-carryover", "finalize"]
    assert events[-1][1][0].branch is no_carryover_branch