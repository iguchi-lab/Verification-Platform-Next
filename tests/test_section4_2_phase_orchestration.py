from types import SimpleNamespace

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
