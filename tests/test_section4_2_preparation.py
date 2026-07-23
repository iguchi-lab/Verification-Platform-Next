from types import SimpleNamespace

import numpy as np
import pytest

import jjjexperiment.section4_2_jjj as sut


def _setting(setting_type):
    return object.__new__(setting_type)

class _FrameRecorder:
    def __init__(self, events=None, generation=0):
        self.events = [] if events is None else events
        self.generation = generation

    def __setitem__(self, key, value):
        self.events.append(("setitem", self.generation, key, value))

    def assign(self, **columns):
        self.events.append(("assign", self.generation, tuple(columns.items())))
        return _FrameRecorder(self.events, self.generation + 1)


def test_output_suffix_matches_heating_and_cooling():
    assert sut._get_output_suffix(_setting(sut.HeatingAcSetting)) == "_H"
    assert sut._get_output_suffix(_setting(sut.CoolingAcSetting)) == "_C"


def test_heating_rated_capacity_service_is_called_each_time(monkeypatch):
    calls = []
    heating = _setting(sut.HeatingAcSetting)
    house = SimpleNamespace(region=6, A_A=120.0)

    class StubHeatQuantityService:
        def __init__(self, ac_setting, region, area):
            calls.append((ac_setting, region, area))
            self.q_hs_rtd = 1234.0

    monkeypatch.setattr(sut, "HeatQuantityService", StubHeatQuantityService)

    assert sut._get_q_hs_rtd_H(heating, house) == 1234.0
    assert sut._get_q_hs_rtd_H(heating, house) == 1234.0
    assert calls == [(heating, 6, 120.0), (heating, 6, 120.0)]
    assert sut._get_q_hs_rtd_C(heating, house) is None


def test_cooling_rated_capacity_service_is_called_each_time(monkeypatch):
    calls = []
    cooling = _setting(sut.CoolingAcSetting)
    house = SimpleNamespace(region=7, A_A=90.0)

    class StubCoolQuantityService:
        def __init__(self, ac_setting, region, area):
            calls.append((ac_setting, region, area))
            self.q_hs_rtd = 5678.0

    monkeypatch.setattr(sut, "CoolQuantityService", StubCoolQuantityService)

    assert sut._get_q_hs_rtd_C(cooling, house) == 5678.0
    assert sut._get_q_hs_rtd_C(cooling, house) == 5678.0
    assert calls == [(cooling, 7, 90.0), (cooling, 7, 90.0)]
    assert sut._get_q_hs_rtd_H(cooling, house) is None


@pytest.mark.parametrize(
    "helper",
    (sut._get_output_suffix, sut._get_q_hs_rtd_H, sut._get_q_hs_rtd_C),
)
def test_season_helpers_reject_unknown_setting(helper):
    if helper is sut._get_output_suffix:
        with pytest.raises(ValueError):
            helper(object())
    else:
        with pytest.raises(ValueError):
            helper(object(), SimpleNamespace(region=6, A_A=120.0))


def test_normalize_design_airflows_preserves_heating_selection():
    assert sut._normalize_design_airflows(0, 1500.0) == (None, 1500.0)


def test_normalize_design_airflows_preserves_cooling_selection():
    assert sut._normalize_design_airflows(1200.0, 0) == (1200.0, None)


def test_normalize_design_airflows_preserves_both_zero_match_priority():
    assert sut._normalize_design_airflows(0, 0) == (None, 0)


def test_normalize_design_airflows_rejects_two_nonzero_values():
    with pytest.raises(ValueError, match="暖房・冷房の判別がつかない"):
        sut._normalize_design_airflows(1200.0, 1500.0)


def test_select_minimum_airflow_input_matches_season():
    heat_input = object()
    cool_input = object()

    assert sut._select_minimum_airflow_input(
        _setting(sut.HeatingAcSetting), heat_input, cool_input
    ) is heat_input
    assert sut._select_minimum_airflow_input(
        _setting(sut.CoolingAcSetting), heat_input, cool_input
    ) is cool_input


def test_select_minimum_airflow_input_rejects_unknown_setting():
    with pytest.raises(ValueError):
        sut._select_minimum_airflow_input(object(), object(), object())


@pytest.mark.parametrize(
    "model",
    (
        sut.計算モデル.ダクト式セントラル空調機,
        sut.計算モデル.RAC活用型全館空調_潜熱評価モデル,
    ),
)
def test_rated_heat_source_capacities_use_quantity_services(monkeypatch, model):
    calls = []
    setting = SimpleNamespace(type=model)
    house = object()

    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda ac, value: 200.0)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda ac, value: 100.0)
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_C",
        lambda value: calls.append(("C", value)) or value + 2.0,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_H",
        lambda value: calls.append(("H", value)) or value + 1.0,
    )

    result = sut._get_rated_heat_source_capacities(
        setting,
        house,
        SimpleNamespace(q_rtd=300.0),
        SimpleNamespace(q_rtd=400.0),
    )

    assert result == (101.0, 202.0)
    assert calls == [("C", 200.0), ("H", 100.0)]


@pytest.mark.parametrize(
    "model",
    (
        sut.計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        sut.計算モデル.電中研モデル,
    ),
)
def test_rated_heat_source_capacities_use_equipment_ratings(monkeypatch, model):
    calls = []
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_C",
        lambda value: calls.append(("C", value)) or value + 2.0,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_hs_rtd_H",
        lambda value: calls.append(("H", value)) or value + 1.0,
    )

    result = sut._get_rated_heat_source_capacities(
        SimpleNamespace(type=model),
        object(),
        SimpleNamespace(q_rtd=300.0),
        SimpleNamespace(q_rtd=400.0),
    )

    assert result == (301.0, 402.0)
    assert calls == [("C", 400.0), ("H", 300.0)]


def test_rated_heat_source_capacities_reject_unknown_model():
    with pytest.raises(Exception, match="設備機器の種類の入力が不正です。"):
        sut._get_rated_heat_source_capacities(
            SimpleNamespace(type=object()),
            object(),
            SimpleNamespace(q_rtd=300.0),
            SimpleNamespace(q_rtd=400.0),
        )


@pytest.mark.parametrize(
    ("setting_type", "season", "representative_temperature", "runup_result"),
    (
        (sut.HeatingAcSetting, "H", sut.THETA_UF_WARM, 11.2224),
        (sut.CoolingAcSetting, "CS", sut.THETA_UF_COOL, 9.15940),
    ),
)
def test_prepare_underfloor_ground_response_preserves_order_and_season(
    monkeypatch,
    setting_type,
    season,
    representative_temperature,
    runup_result,
):
    calls = []
    theta_ex = object()
    theta_in = object()

    monkeypatch.setattr(
        sut.uf,
        "get_Theta_in_d_t",
        lambda value: calls.append(("indoor", value)) or theta_in,
    )
    monkeypatch.setattr(
        sut.algo,
        "get_Theta_g_avg",
        lambda value: calls.append(("ground", value)) or 15.5,
    )
    monkeypatch.setattr(
        sut,
        "calc_sum_Theta_dash_g_surf_A_m_runup",
        lambda temperature, average: calls.append(
            ("runup", temperature, average)
        ) or runup_result,
    )

    result = sut._prepare_underfloor_ground_response(
        _setting(setting_type),
        theta_ex,
    )

    assert result == (theta_in, 0.025504994, 15.5, runup_result)
    assert calls == [
        ("indoor", season),
        ("ground", theta_ex),
        ("runup", representative_temperature, 15.5),
    ]


def test_prepare_underfloor_ground_response_rejects_unknown_setting():
    with pytest.raises(ValueError):
        sut._prepare_underfloor_ground_response(object(), object())

@pytest.mark.parametrize(
    ("carryover", "expected"),
    (
        (sut.過剰熱量繰越計算.行う, [0.0, 2.0]),
        (sut.過剰熱量繰越計算.行わない, [-1.0, 2.0]),
    ),
)
def test_get_actual_loads_preserves_formula_order_and_clipping(
    monkeypatch,
    carryover,
    expected,
):
    calls = []
    inputs = [object() for _ in range(5)]

    def result(name, *args):
        calls.append((name, args))
        return np.array([-1.0, 2.0])

    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_CL_d_t_i",
        lambda *args: result("CL", *args),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_CS_d_t_i",
        lambda *args: result("CS", *args),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_L_dash_H_d_t_i",
        lambda *args: result("H", *args),
    )

    actual = sut._get_actual_loads(
        SimpleNamespace(carry_over_heat=carryover),
        *inputs,
        6,
    )

    for value in actual:
        np.testing.assert_array_equal(value, expected)
    assert calls == [
        ("CL", (inputs[0], inputs[1], inputs[2], 6)),
        ("CS", (inputs[0], inputs[3], inputs[4], 6)),
        ("H", (inputs[0], inputs[3], inputs[4], 6)),
    ]

def test_get_unprocessed_loads_preserves_formula_order_and_arguments(monkeypatch):
    calls = []
    inputs = [object() for _ in range(6)]
    outputs = [object() for _ in range(3)]

    monkeypatch.setattr(
        sut.dc,
        "get_Q_UT_CL_d_t_i",
        lambda *args: calls.append(("CL", args)) or outputs[0],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_UT_CS_d_t_i",
        lambda *args: calls.append(("CS", args)) or outputs[1],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Q_UT_H_d_t_i",
        lambda *args: calls.append(("H", args)) or outputs[2],
    )

    assert sut._get_unprocessed_loads(*inputs) == tuple(outputs)
    assert calls == [
        ("CL", (inputs[0], inputs[1])),
        ("CS", (inputs[2], inputs[3])),
        ("H", (inputs[4], inputs[5])),
    ]

def test_get_unprocessed_energy_for_heating(monkeypatch):
    monkeypatch.setattr(sut, "get_alpha_UT_H_A", lambda region: region / 2)
    monkeypatch.setattr(
        sut.dc,
        "get_E_C_UT_d_t",
        lambda *args: pytest.fail("cooling calculation must not run"),
    )
    heating_load = np.array([[1.0, 2.0], [3.0, 4.0]])

    value, output_name = sut._get_unprocessed_energy(
        _setting(sut.HeatingAcSetting),
        object(),
        object(),
        heating_load,
        6,
    )

    np.testing.assert_array_equal(value, [12.0, 18.0])
    assert output_name == "E_UT_H_d_t"


def test_get_unprocessed_energy_for_cooling(monkeypatch):
    calls = []
    latent = object()
    sensible = object()
    expected = object()
    monkeypatch.setattr(
        sut.dc,
        "get_E_C_UT_d_t",
        lambda *args: calls.append(args) or expected,
    )

    assert sut._get_unprocessed_energy(
        _setting(sut.CoolingAcSetting),
        latent,
        sensible,
        object(),
        7,
    ) == (expected, "E_UT_C_d_t")
    assert calls == [(latent, sensible, 7)]


def test_get_unprocessed_energy_rejects_unknown_setting():
    with pytest.raises(
        ValueError,
        match="ac_setting must be HeatingAcSetting or CoolingAcSetting",
    ):
        sut._get_unprocessed_energy(object(), object(), object(), object(), 6)

def test_export_underfloor_output_preserves_filename_and_call_order(monkeypatch):
    calls = []
    setting = _setting(sut.HeatingAcSetting)
    frame = SimpleNamespace(
        export_to_csv=lambda filename: calls.append(("export", filename))
    )
    monkeypatch.setattr(
        sut.jjj_consts,
        "version_info",
        lambda: calls.append(("version",)) or "v-test",
    )
    monkeypatch.setattr(
        sut,
        "_get_output_suffix",
        lambda value: calls.append(("suffix", value)) or "_H",
    )

    sut._export_underfloor_output(
        "case",
        setting,
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更する),
        frame,
    )

    assert calls == [
        ("version",),
        ("suffix", setting),
        ("export", "casev-test_H_output_uf.csv"),
    ]


def test_export_underfloor_output_does_nothing_when_disabled(monkeypatch):
    monkeypatch.setattr(
        sut.jjj_consts,
        "version_info",
        lambda: pytest.fail("version must not be requested"),
    )
    frame = SimpleNamespace(
        export_to_csv=lambda filename: pytest.fail("CSV must not be exported")
    )

    sut._export_underfloor_output(
        "case",
        object(),
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更しない),
        frame,
    )

@pytest.mark.parametrize(
    ("capacities", "season"),
    (
        ((1.0, None), "H"),
        ((None, 2.0), "C"),
    ),
)
def test_export_standard_outputs_preserves_capacity_and_file_order(
    monkeypatch,
    capacities,
    season,
):
    calls = []
    setting = object()
    house = object()

    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_H",
        lambda ac, value: calls.append(("capacity", "H", ac, value))
        or capacities[0],
    )
    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_C",
        lambda ac, value: calls.append(("capacity", "C", ac, value))
        or capacities[1],
    )
    monkeypatch.setattr(
        sut.jjj_consts,
        "version_info",
        lambda: calls.append(("version",)) or "v-test",
    )

    def frame(number):
        return SimpleNamespace(
            to_csv=lambda filename, encoding: calls.append(
                ("export", number, filename, encoding)
            )
        )

    sut._export_standard_outputs(
        "case",
        setting,
        house,
        frame(3),
        frame(4),
        frame(5),
    )

    assert calls == [
        ("capacity", "H", setting, house),
        ("capacity", "C", setting, house),
        ("version",),
        ("export", 3, f"casev-test_{season}_output3.csv", "cp932"),
        ("version",),
        ("export", 4, f"casev-test_{season}_output4.csv", "cp932"),
        ("version",),
        ("export", 5, f"casev-test_{season}_output5.csv", "cp932"),
    ]


@pytest.mark.parametrize("capacities", ((None, None), (1.0, 2.0)))
def test_export_standard_outputs_rejects_ambiguous_capacities(
    monkeypatch,
    capacities,
):
    calls = []
    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_H",
        lambda *args: calls.append("H") or capacities[0],
    )
    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_C",
        lambda *args: calls.append("C") or capacities[1],
    )

    with pytest.raises(Exception):
        sut._export_standard_outputs(
            "case",
            object(),
            object(),
            object(),
            object(),
            object(),
        )

    assert calls == ["H", "C"]

def test_record_balanced_load_outputs_preserves_assign_order_and_result():
    frame = _FrameRecorder()
    sensible = [object() for _ in range(5)]
    heating = [object() for _ in range(5)]

    result = sut._record_balanced_load_outputs(frame, sensible, heating)

    assert result.generation == 2
    assert frame.events == [
        (
            "assign",
            0,
            tuple(
                (f"L_star_CS_d_t_i_{i + 1}", sensible[i])
                for i in range(5)
            ),
        ),
        (
            "assign",
            1,
            tuple(
                (f"L_star_H_d_t_i_{i + 1}", heating[i])
                for i in range(5)
            ),
        ),
    ]

def test_record_heat_source_outlet_outputs_preserves_write_order():
    frame = _FrameRecorder()
    x_star = object()
    theta_star = object()
    x_min = object()
    x_req = [object() for _ in range(5)]
    theta_req = [object() for _ in range(5)]
    x_out = object()
    theta_min = object()
    theta_max = object()
    theta_out = object()

    result = sut._record_heat_source_outlet_outputs(
        frame,
        x_star,
        theta_star,
        x_min,
        x_req,
        theta_req,
        x_out,
        theta_min,
        theta_max,
        theta_out,
    )

    assert result.generation == 3
    assert frame.events == [
        ("setitem", 0, "X_star_hs_in_d_t", x_star),
        ("setitem", 0, "Theta_star_hs_in_d_t", theta_star),
        ("setitem", 0, "X_star_hs_in_d_t", x_star),
        ("setitem", 0, "Theta_star_hs_in_d_t", theta_star),
        ("setitem", 0, "X_hs_out_min_C_d_t", x_min),
        (
            "assign",
            0,
            tuple((f"X_req_d_t_{i + 1}", x_req[i]) for i in range(5)),
        ),
        (
            "assign",
            1,
            tuple(
                (f"Theta_req_d_t_{i + 1}", theta_req[i])
                for i in range(5)
            ),
        ),
        ("setitem", 2, "X_hs_out_d_t", x_out),
        (
            "assign",
            2,
            (
                ("Theta_hs_out_min_C_d_t", theta_min),
                ("Theta_hs_out_max_H_d_t", theta_max),
                ("Theta_hs_out_d_t", theta_out),
            ),
        ),
    ]

@pytest.mark.parametrize("before_is_none", (False, True))
def test_record_supply_state_outputs_preserves_assign_order(before_is_none):
    frame = _FrameRecorder()
    before_values = [object() for _ in range(5)]
    before = None if before_is_none else before_values
    supply = [object() for _ in range(5)]
    theta_supply = [object() for _ in range(5)]
    theta_hbr = [object() for _ in range(5)]
    theta_nr = object()

    result = sut._record_supply_state_outputs(
        frame,
        before,
        supply,
        theta_supply,
        theta_hbr,
        theta_nr,
    )

    expected_before = [None] * 5 if before_is_none else before_values
    assert result.generation == 4
    assert frame.events == [
        (
            "assign",
            0,
            tuple(
                (f"V_supply_d_t_{i + 1}_before", expected_before[i])
                for i in range(5)
            ),
        ),
        (
            "assign",
            1,
            tuple((f"V_supply_d_t_{i + 1}", supply[i]) for i in range(5)),
        ),
        (
            "assign",
            2,
            tuple(
                (f"Theta_supply_d_t_{i + 1}", theta_supply[i])
                for i in range(5)
            ),
        ),
        (
            "assign",
            3,
            tuple(
                (f"Theta_HBR_d_t_{i + 1}", theta_hbr[i])
                for i in range(5)
            ) + (("Theta_NR_d_t", theta_nr),),
        ),
    ]

def test_record_actual_load_outputs_preserves_assign_order():
    frame = _FrameRecorder()
    latent = [object() for _ in range(5)]
    sensible = [object() for _ in range(5)]
    heating = [object() for _ in range(5)]

    result = sut._record_actual_load_outputs(
        frame,
        latent,
        sensible,
        heating,
    )

    assert result.generation == 3
    assert frame.events == [
        (
            "assign",
            0,
            tuple((f"L_dash_CL_d_t_{i + 1}", latent[i]) for i in range(5)),
        ),
        (
            "assign",
            1,
            tuple(
                (f"L_dash_CS_d_t_{i + 1}", sensible[i])
                for i in range(5)
            ),
        ),
        (
            "assign",
            2,
            tuple((f"L_dash_H_d_t_{i + 1}", heating[i]) for i in range(5)),
        ),
    ]

def test_record_unprocessed_load_outputs_preserves_assign_order():
    frame = _FrameRecorder()
    latent = [object() for _ in range(5)]
    sensible = [object() for _ in range(5)]
    heating = [object() for _ in range(5)]

    result = sut._record_unprocessed_load_outputs(
        frame,
        latent,
        sensible,
        heating,
    )

    assert result.generation == 3
    assert frame.events == [
        (
            "assign",
            0,
            tuple((f"Q_UT_CL_d_t_{i + 1}", latent[i]) for i in range(5)),
        ),
        (
            "assign",
            1,
            tuple(
                (f"Q_UT_CS_d_t_{i + 1}", sensible[i])
                for i in range(5)
            ),
        ),
        (
            "assign",
            2,
            tuple((f"Q_UT_H_d_t_{i + 1}", heating[i]) for i in range(5)),
        ),
    ]


def test_record_unprocessed_energy_output_preserves_direct_assignment():
    frame = _FrameRecorder()
    energy = object()

    result = sut._record_unprocessed_energy_output(
        frame,
        "E_UT_H_d_t",
        energy,
    )

    assert result is frame
    assert frame.events == [
        ("setitem", 0, "E_UT_H_d_t", energy),
    ]


def test_heat_source_supply_airflow_before_vav_uses_cav_seasons(monkeypatch):
    heating = np.zeros(24 * 365, dtype=bool)
    cooling = np.zeros(24 * 365, dtype=bool)
    mid = np.zeros(24 * 365, dtype=bool)
    heating[0] = True
    cooling[1] = True
    mid[2] = True
    monkeypatch.setattr(
        sut.dc_a,
        "get_season_array_d_t",
        lambda region: (heating, cooling, mid),
    )

    result = sut._get_heat_source_supply_airflow_before_vav(
        SimpleNamespace(type=object()),
        SimpleNamespace(region=6),
        SimpleNamespace(hs_CAV=True),
        1200.0,
        1500.0,
        300.0,
        100.0,
        200.0,
        object(),
        object(),
    )

    np.testing.assert_array_equal(result[:3], [1200.0, 1500.0, 0.0])
    np.testing.assert_array_equal(result[3:], np.zeros(24 * 365 - 3))


@pytest.mark.parametrize(
    ("capacities", "load_index", "cooling"),
    (
        ((100.0, None), 0, False),
        ((None, 200.0), 1, True),
    ),
)
def test_heat_source_supply_airflow_before_vav_preserves_2023_branch(
    monkeypatch,
    capacities,
    load_index,
    cooling,
):
    calls = []
    loads = (object(), object())
    expected = object()
    monkeypatch.setattr(
        sut.dc,
        "get_V_dash_hs_supply_d_t_2023",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_heat_source_supply_airflow_before_vav(
        SimpleNamespace(type=sut.計算モデル.RAC活用型全館空調_潜熱評価モデル),
        SimpleNamespace(region=7),
        SimpleNamespace(hs_CAV=False),
        1200.0,
        1500.0,
        300.0,
        *capacities,
        *loads,
    )

    assert result is expected
    assert calls == [(loads[load_index], 7, cooling)]


def test_heat_source_supply_airflow_before_vav_preserves_standard_arguments(
    monkeypatch,
):
    calls = []
    load = object()
    expected = object()
    monkeypatch.setattr(
        sut.dc,
        "get_V_dash_hs_supply_d_t",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_heat_source_supply_airflow_before_vav(
        SimpleNamespace(type=object()),
        SimpleNamespace(region=5),
        SimpleNamespace(hs_CAV=False),
        0,
        1800.0,
        250.0,
        100.0,
        None,
        load,
        object(),
    )

    assert result is expected
    assert calls == [(250.0, 0, None, 100.0, None, load, 5)]

def test_supply_airflow_before_vav_preserves_vav_formula_order(monkeypatch):
    calls = []
    sensible = object()
    heating = object()
    heat_source_airflow = object()
    ventilation = object()
    ratios = np.arange(5 * 24 * 365).reshape(5, 24 * 365)
    supply = object()
    monkeypatch.setattr(
        sut.jjj_consts,
        "change_supply_volume_before_vav_adjust",
        sut.VAVありなしの吹出風量.数式を統一する.value,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_r_supply_des_d_t_i_2023",
        lambda *args: calls.append(("ratios", args)) or ratios,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_V_dash_supply_d_t_i_2023",
        lambda *args: calls.append(("supply", args)) or supply,
    )

    result = sut._get_supply_airflow_before_vav(
        SimpleNamespace(VAV=True),
        SimpleNamespace(region=6),
        SimpleNamespace(L_CS_d_t_i=sensible, L_H_d_t_i=heating),
        object(),
        heat_source_airflow,
        ventilation,
    )

    np.testing.assert_array_equal(result[0], ratios[:, 0:1])
    assert result[1] is ratios
    assert result[2] is supply
    assert calls == [
        ("ratios", (6, sensible, heating)),
        ("supply", (ratios, heat_source_airflow, ventilation)),
    ]


def test_supply_airflow_before_vav_preserves_standard_formula_order(monkeypatch):
    calls = []
    areas = object()
    heat_source_airflow = object()
    ventilation = object()
    ratios = np.arange(1.0, 6.0)
    supply = object()
    monkeypatch.setattr(
        sut.dc,
        "get_r_supply_des_i",
        lambda value: calls.append(("ratios", value)) or ratios,
    )
    monkeypatch.setattr(
        sut.dc,
        "get_V_dash_supply_d_t_i",
        lambda *args: calls.append(("supply", args)) or supply,
    )

    result = sut._get_supply_airflow_before_vav(
        SimpleNamespace(VAV=False),
        object(),
        object(),
        areas,
        heat_source_airflow,
        ventilation,
    )

    assert result[0] is ratios
    np.testing.assert_array_equal(
        result[1],
        np.tile(ratios, 24 * 365).reshape(5, 24 * 365),
    )
    assert result[2] is supply
    assert calls == [
        ("ratios", areas),
        ("supply", (ratios, heat_source_airflow, ventilation)),
    ]

def test_room_to_underfloor_transfer_preserves_in_place_adjustment(monkeypatch):
    calls = []
    area = np.arange(1.0, 13.0).reshape(12, 1)
    theta_out = np.arange(24 * 365, dtype=float)
    theta_in = theta_out - 2.0
    output = np.full(24 * 365, 100.0)
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "get_A_s_ufac_i",
        lambda *args: calls.append(("area", args)) or (area, 0.4),
    )
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "calc_delta_L_room2uf_i",
        lambda insulation, values, delta: calls.append(
            ("transfer", insulation, values, delta)
        ) or np.full((12, 1), delta),
    )

    result = sut._adjust_heat_source_output_for_room_to_underfloor_transfer(
        SimpleNamespace(U_s_vert=0.7, U_s_floor_ins=0.3),
        SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0),
        theta_out,
        theta_in,
        output,
    )

    assert result[0] is output
    np.testing.assert_array_equal(output, np.full(24 * 365, 76.0))
    assert result[1] == 0.7
    assert result[2] is area
    assert result[3] == 0.4
    assert calls[0] == ("area", (120.0, 30.0, 50.0))
    assert len(calls) == 1 + 24 * 365
    assert calls[1][1:] == (0.3, area, 2.0)
    assert calls[-1][1:] == (0.3, area, 2.0)

def test_underfloor_to_outdoor_transfer_preserves_heating_order(monkeypatch):
    setting = _setting(sut.HeatingAcSetting)
    area = np.ones((12, 1))
    theta_in = np.full(24 * 365, 20.0)
    theta_out = np.full(24 * 365, 10.0)
    supply = np.ones((5, 24 * 365))
    output = np.full(24 * 365, 100.0)
    capacity_calls = []
    theta_calls = []
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda *args: capacity_calls.append("H") or 1.0)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda *args: capacity_calls.append("C") or None)
    monkeypatch.setattr(sut.jjj_ufac_dc, "get_r_A_uf_i", lambda: np.ones((12, 1)))
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "calc_Theta_uf",
        lambda *args: theta_calls.append(args) or 20.0,
    )
    monkeypatch.setattr(sut.algo, "get_L_uf", lambda value: value + 1.0)
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "calc_delta_L_uf2outdoor",
        lambda phi, length, delta: delta,
    )

    result = sut._adjust_heat_source_output_for_underfloor_to_outdoor_transfer(
        setting,
        SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0),
        SimpleNamespace(Q=2.7),
        SimpleNamespace(L_H_d_t_i=np.ones((12, 24 * 365))),
        SimpleNamespace(U_s_floor_ins=0.3),
        SimpleNamespace(get_phi=lambda q: q + 0.5),
        area,
        0.4,
        0.7,
        theta_in,
        theta_out,
        supply,
        output,
    )

    assert result[0] is output
    np.testing.assert_array_equal(output, np.full(24 * 365, 110.0))
    np.testing.assert_array_equal(result[1], np.full(24 * 365, 20.0))
    assert capacity_calls == ["H", "C"] * (24 * 365)
    assert len(theta_calls) == 24 * 365
    assert theta_calls[0][:2] == (1.0, None)
    np.testing.assert_allclose(
        theta_calls[0][2:],
        (4.8, 12.0, 0.7, 0.3, 20.0, 10.0, 5.0),
    )
    assert theta_calls[-1] == theta_calls[0]

def test_underfloor_to_ground_transfer_preserves_argument_order(monkeypatch):
    setting = object()
    house = object()
    area = np.arange(1.0, 13.0).reshape(12, 1)
    theta = np.arange(24 * 365, dtype=float)
    output = np.full(24 * 365, 100.0)
    calls = []
    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_H",
        lambda *args: calls.append(("capacity", "H", args)) or 1.0,
    )
    monkeypatch.setattr(
        sut,
        "_get_q_hs_rtd_C",
        lambda *args: calls.append(("capacity", "C", args)) or 2.0,
    )
    monkeypatch.setattr(sut.jjj_consts, "R_g", 3.0, raising=False)
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "calc_delta_L_uf2gnd",
        lambda q_h, q_c, area_total, resistance, phi, theta_uf, response, average: (
            calls.append(
                (
                    "transfer",
                    q_h,
                    q_c,
                    area_total,
                    resistance,
                    phi,
                    theta_uf,
                    response,
                    average,
                )
            )
            or theta_uf + 1.0
        ),
    )

    result = sut._adjust_heat_source_output_for_underfloor_to_ground_transfer(
        setting,
        house,
        area,
        0.025,
        theta,
        11.2,
        15.5,
        output,
    )

    assert result is output
    np.testing.assert_array_equal(output, 101.0 + theta)
    assert calls[:2] == [
        ("capacity", "H", (setting, house)),
        ("capacity", "C", (setting, house)),
    ]
    # np.vectorize evaluates the first element once for type inference.
    assert len(calls) == 3 + 24 * 365
    assert calls[2] == (
        "transfer", 1.0, 2.0, 78.0, 3.0, 0.025, 0.0, 11.2, 15.5
    )
    assert calls[-1] == (
        "transfer", 1.0, 2.0, 78.0, 3.0, 0.025, 8759.0, 11.2, 15.5
    )

def test_heat_source_outlet_requirements_preserve_formula_order(monkeypatch):
    calls = []
    inputs = [object() for _ in range(10)]
    outputs = [object() for _ in range(3)]
    monkeypatch.setattr(
        sut.dc,
        "get_X_hs_out_min_C_d_t",
        lambda *args: calls.append(("minimum", args)) or outputs[0],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_X_req_d_t_i",
        lambda *args: calls.append(("humidity", args)) or outputs[1],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_req_d_t_i",
        lambda *args: calls.append(("temperature", args)) or outputs[2],
    )

    result = sut._get_heat_source_outlet_requirements(*inputs, 6)

    assert result == tuple(outputs)
    assert calls == [
        ("minimum", (inputs[0], inputs[1], inputs[2])),
        ("humidity", (inputs[3], inputs[4], inputs[2], 6)),
        (
            "temperature",
            (inputs[5], inputs[6], inputs[2], inputs[7], inputs[8], inputs[9], 6),
        ),
    ]

def test_heat_source_outlet_humidity_preserves_formula_arguments(monkeypatch):
    inputs = [object() for _ in range(5)]
    calls = []
    expected = object()
    monkeypatch.setattr(
        sut.dc,
        "get_X_hs_out_d_t",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_heat_source_outlet_humidity(*inputs, 7)

    assert result is expected
    assert calls == [((*inputs, 7))]

def test_heat_source_outlet_temperatures_preserve_formula_order(monkeypatch):
    calls = []
    setting = SimpleNamespace(VAV=True)
    house = SimpleNamespace(region=6)
    inputs = [object() for _ in range(8)]
    outputs = [object() for _ in range(3)]
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_hs_out_min_C_d_t",
        lambda *args: calls.append(("minimum", args)) or outputs[0],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_hs_out_max_H_d_t",
        lambda *args: calls.append(("maximum", args)) or outputs[1],
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_hs_out_d_t",
        lambda *args: calls.append(("outlet", args)) or outputs[2],
    )

    result = sut._get_heat_source_outlet_temperatures(
        setting,
        house,
        *inputs,
    )

    assert result == tuple(outputs)
    assert calls == [
        ("minimum", (inputs[0], inputs[1], inputs[2])),
        ("maximum", (inputs[0], inputs[3], inputs[2])),
        (
            "outlet",
            (
                True,
                inputs[4],
                inputs[2],
                inputs[5],
                inputs[6],
                6,
                inputs[7],
                outputs[1],
                outputs[0],
            ),
        ),
    ]

@pytest.mark.parametrize("print_exec", (False, True))
def test_capped_supply_airflows_preserve_call_order_and_diagnostics(
    monkeypatch,
    print_exec,
):
    calls = []
    cap = object()
    setting = SimpleNamespace(VAV=True)
    house = SimpleNamespace(region=6)
    inputs = [object() for _ in range(10)]
    before = object()
    after = object()
    monkeypatch.setattr(
        sut.dc,
        "get_V_supply_d_t_i",
        lambda *args: calls.append(("calculate", args)) or before,
    )
    monkeypatch.setattr(
        sut.jjj_vsupcap,
        "cap_V_supply_d_t_i",
        lambda *args, **kwargs: calls.append(("cap", args, kwargs)) or after,
    )

    result = sut._get_capped_supply_airflows(sut._CappedSupplyAirflowInputs(
        cap,
        setting,
        house,
        *inputs,
        print_exec=print_exec,
    ))

    assert result == (before, after)
    assert calls == [
        (
            "calculate",
            (
                inputs[0],
                inputs[1],
                inputs[2],
                inputs[3],
                inputs[4],
                inputs[5],
                inputs[6],
                True,
                6,
                inputs[7],
            ),
        ),
        (
            "cap",
            (
                cap,
                before,
                inputs[6],
                inputs[5],
                6,
                inputs[8],
                inputs[9],
            ),
            {"print_exec": print_exec},
        ),
    ]

def test_supply_air_temperatures_preserve_formula_arguments(monkeypatch):
    calls = []
    house = SimpleNamespace(region=7)
    inputs = [object() for _ in range(7)]
    expected = object()
    monkeypatch.setattr(
        sut.dc,
        "get_Thata_supply_d_t_i",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_supply_air_temperatures(house, *inputs)

    assert result is expected
    assert calls == [((*inputs, 7))]

def test_balanced_cooling_loads_preserve_formula_order(monkeypatch):
    calls = []
    latent_by_room = object()
    sensible_by_room = object()
    outputs = [object() for _ in range(6)]
    names = (
        "get_L_star_CL_d_t",
        "get_L_star_CS_d_t",
        "get_L_star_CL_max_d_t",
        "get_L_star_dash_CL_d_t",
        "get_L_star_dash_C_d_t",
        "get_SHF_dash_d_t",
    )
    for index, name in enumerate(names):
        monkeypatch.setattr(
            sut.dc,
            name,
            lambda *args, index=index, name=name: calls.append((name, args))
            or outputs[index],
        )

    result = sut._get_balanced_cooling_loads(latent_by_room, sensible_by_room)

    assert result == tuple(outputs)
    assert calls == [
        (names[0], (latent_by_room,)),
        (names[1], (sensible_by_room,)),
        (names[2], (outputs[1],)),
        (names[3], (outputs[2], outputs[0])),
        (names[4], (outputs[1], outputs[3])),
        (names[5], (outputs[1], outputs[4])),
    ]

def test_standard_heat_source_capacity_limits_preserve_formula_order(monkeypatch):
    calls = []
    setting = SimpleNamespace(type=object())
    house = object()
    heating = SimpleNamespace(input_C_af=1.1)
    cooling = SimpleNamespace(input_C_af=1.2)
    shf = object()
    latent = object()
    outputs = [object() for _ in range(5)]
    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda *args: calls.append(("rated_C", args)) or 200.0)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda *args: calls.append(("rated_H", args)) or 100.0)
    monkeypatch.setattr(sut.dc, "get_Q_hs_max_C_d_t_2024", lambda *args: calls.append(("max_C", args)) or outputs[0])
    monkeypatch.setattr(sut.dc, "get_Q_hs_max_CL_d_t", lambda *args: calls.append(("max_CL", args)) or outputs[1])
    monkeypatch.setattr(sut.dc, "get_Q_hs_max_CS_d_t", lambda *args: calls.append(("max_CS", args)) or outputs[2])
    monkeypatch.setattr(sut.dc, "get_Q_hs_max_H_d_t_2024", lambda *args: calls.append(("max_H", args)) or outputs[4])

    def get_defrost():
        calls.append(("defrost", ()))
        return outputs[3]

    result = sut._get_standard_heat_source_capacity_limits(
        setting, house, heating, cooling, shf, latent, get_defrost
    )

    assert result == tuple(outputs)
    assert calls == [
        ("rated_C", (setting, house)),
        ("max_C", (setting.type, 200.0, 1.2)),
        ("max_CL", (outputs[0], shf, latent)),
        ("max_CS", (outputs[0], shf)),
        ("defrost", ()),
        ("rated_H", (setting, house)),
        ("max_H", (setting.type, 100.0, outputs[3], 1.1)),
    ]

@pytest.mark.parametrize("log_intermediates", (False, True))
def test_rac_heating_capacity_preserves_formula_and_log_order(
    monkeypatch,
    log_intermediates,
):
    calls = []
    heating = SimpleNamespace(q_max=10.0, q_rtd=8.0, input_C_af=1.1)
    cooling = SimpleNamespace(q_rtd=7.0)
    theta = object()
    humidity = object()
    outputs = (1.25, object(), object())
    monkeypatch.setattr(
        sut.rac,
        "get_q_r_max_H",
        lambda *args: calls.append(("ratio", args)) or outputs[0],
    )
    monkeypatch.setattr(
        sut.rac,
        "calc_Q_r_max_H_d_t",
        lambda *args: calls.append(("output_ratio", args)) or outputs[1],
    )
    monkeypatch.setattr(
        sut.rac,
        "calc_Q_max_H_d_t",
        lambda *args: calls.append(("output", args)) or outputs[2],
    )
    monkeypatch.setattr(
        sut._logger,
        "debug",
        lambda message: calls.append(("debug", message)),
    )
    monkeypatch.setattr(
        sut._logger,
        "NDdebug",
        lambda name, value: calls.append(("NDdebug", name, value)),
    )

    result = sut._get_rac_heating_capacity(
        heating, cooling, theta, humidity, log_intermediates
    )

    assert result == outputs
    expected = [("ratio", (10.0, 8.0))]
    if log_intermediates:
        expected.append(("debug", "q_r_max_H: 1.25"))
    expected.append(("output_ratio", (7.0, outputs[0], theta)))
    if log_intermediates:
        expected.append(("NDdebug", "Q_r_max_H_d_t", outputs[1]))
    expected.append(("output", (outputs[1], 8.0, theta, humidity, 1.1)))
    if log_intermediates:
        expected.append(("NDdebug", "Q_max_H_d_t", outputs[2]))
    assert calls == expected

@pytest.mark.parametrize("log_intermediates", (False, True))
def test_rac_cooling_capacity_preserves_formula_and_log_order(
    monkeypatch,
    log_intermediates,
):
    calls = []
    cooling = SimpleNamespace(q_max=10.0, q_rtd=8.0, input_C_af=1.2)
    sensible_by_room = object()
    latent_by_room = object()
    load = SimpleNamespace(
        L_CS_d_t_i=sensible_by_room,
        L_CL_d_t_i=latent_by_room,
    )
    theta = object()
    sensible_total = object()
    latent_total = object()
    outputs = (1.25,) + tuple(object() for _ in range(9))

    def sum_values(value, axis):
        calls.append(("sum", value, axis))
        return sensible_total if value is sensible_by_room else latent_total

    monkeypatch.setattr(sut.np, "sum", sum_values)
    functions = (
        ("get_q_r_max_C", "ratio", outputs[0]),
        ("calc_Q_r_max_C_d_t", "output_ratio", outputs[1]),
        ("calc_Q_max_C_d_t", "output", outputs[2]),
        ("get_SHF_L_min_c", "minimum_shf", outputs[3]),
        ("get_L_max_CL_d_t", "max_latent", outputs[4]),
        ("get_L_dash_CL_d_t", "latent", outputs[5]),
        ("get_L_dash_C_d_t", "total", outputs[6]),
        ("get_SHF_dash_d_t", "shf", outputs[7]),
        ("get_Q_max_CS_d_t", "max_sensible", outputs[8]),
        ("get_Q_max_CL_d_t", "max_latent_output", outputs[9]),
    )
    for function_name, event_name, output in functions:
        monkeypatch.setattr(
            sut.rac,
            function_name,
            lambda *args, event_name=event_name, output=output: calls.append(
                (event_name, args)
            )
            or output,
        )
    monkeypatch.setattr(sut._logger, "debug", lambda message: calls.append(("debug", message)))
    monkeypatch.setattr(sut._logger, "NDdebug", lambda name, value: calls.append(("NDdebug", name, value)))

    result = sut._get_rac_cooling_capacity(
        cooling, load, theta, log_intermediates
    )

    assert result == outputs
    expected = [("ratio", (10.0, 8.0))]
    if log_intermediates:
        expected.append(("debug", "q_r_max_C: 1.25"))
    expected.append(("output_ratio", (outputs[0], 8.0, theta)))
    if log_intermediates:
        expected.extend((
            ("NDdebug", "Theta_ex_d_t", theta),
            ("NDdebug", "Q_r_max_C_d_t", outputs[1]),
        ))
    expected.append(("output", (outputs[1], 8.0, 1.2)))
    if log_intermediates:
        expected.append(("NDdebug", "Q_max_C_d_t", outputs[2]))
    expected.extend((
        ("minimum_shf", ()),
        ("sum", sensible_by_room, 0),
        ("max_latent", (sensible_total, outputs[3])),
        ("sum", latent_by_room, 0),
        ("latent", (outputs[4], latent_total)),
        ("sum", sensible_by_room, 0),
        ("total", (sensible_total, outputs[5])),
        ("sum", sensible_by_room, 0),
        ("shf", (sensible_total, outputs[6])),
        ("max_sensible", (outputs[2], outputs[7])),
        ("max_latent_output", (outputs[2], outputs[7], outputs[5])),
    ))
    assert calls == expected

def test_carryover_at_hour_rejects_overlapping_seasons_before_first_hour():
    with pytest.raises(ValueError, match="想定外の季節"):
        sut._get_carryover_at_hour(
            0,
            np.array([True]),
            np.array([True]),
            object(),
            np.zeros((5, 1)),
            np.zeros(1),
        )


def test_carryover_at_hour_returns_first_hour_zero_without_calculation(monkeypatch):
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "calc_carryover",
        lambda *args: pytest.fail("first hour must not calculate carryover"),
    )

    result = sut._get_carryover_at_hour(
        0,
        np.array([True]),
        np.array([False]),
        object(),
        np.zeros((5, 1)),
        np.zeros(1),
    )

    np.testing.assert_array_equal(result, np.zeros((5, 1)))


@pytest.mark.parametrize(
    ("heating", "cooling", "room_temperature", "target_temperature"),
    (
        (True, False, 22.0, 20.0),
        (False, True, 24.0, 26.0),
    ),
)
def test_carryover_at_hour_preserves_previous_comparison_and_current_target(
    monkeypatch,
    heating,
    cooling,
    room_temperature,
    target_temperature,
):
    calls = []
    area = object()
    expected = object()
    rooms = np.full((5, 2), room_temperature)
    targets = np.array([target_temperature, target_temperature + 1.0])
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "calc_carryover",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_carryover_at_hour(
        1,
        np.array([False, heating]),
        np.array([False, cooling]),
        area,
        rooms,
        targets,
    )

    assert result is expected
    assert len(calls) == 1
    assert calls[0][:3] == (heating, cooling, area)
    np.testing.assert_array_equal(calls[0][3], rooms[:, 0:1])
    assert calls[0][4] == targets[1]

def test_balanced_loads_at_hour_preserve_formula_order_and_slices(monkeypatch):
    calls = []
    heating = np.arange(7 * 3).reshape(7, 3)
    cooling = heating + 100
    transfer = heating + 200
    carryover = object()
    outputs = (object(), object())
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "get_L_star_H_i_2024",
        lambda *args: calls.append(("heating", args)) or outputs[0],
    )
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "get_L_star_CS_i_2024",
        lambda *args: calls.append(("cooling", args)) or outputs[1],
    )

    result = sut._get_balanced_loads_at_hour(
        1,
        np.array([False, True, False]),
        np.array([False, False, True]),
        SimpleNamespace(L_H_d_t_i=heating, L_CS_d_t_i=cooling),
        transfer,
        carryover,
    )

    assert result == outputs
    assert calls[0][0] == "heating"
    assert calls[0][1][0] is True or calls[0][1][0] == np.bool_(True)
    np.testing.assert_array_equal(calls[0][1][1], heating[:5, 1:2])
    np.testing.assert_array_equal(calls[0][1][2], transfer[:5, 1:2])
    assert calls[0][1][3] is carryover
    assert calls[1][0] == "cooling"
    assert calls[1][1][0] is False or calls[1][1][0] == np.bool_(False)
    np.testing.assert_array_equal(calls[1][1][1], cooling[:5, 1:2])
    np.testing.assert_array_equal(calls[1][1][2], transfer[:5, 1:2])
    assert calls[1][1][3] is carryover

@pytest.mark.parametrize("t", (0, 1))
def test_actual_room_temperatures_at_hour_preserve_slices(monkeypatch, t):
    calls = []
    expected = object()
    H = np.array([True, False])
    C = np.array([False, True])
    M = np.array([False, False])
    theta_star = np.array([20.0, 21.0])
    supply = np.arange(5 * 2).reshape(5, 2)
    supply_theta = supply + 10
    area_partition = np.arange(1.0, 6.0)
    area_room = np.arange(6.0, 11.0)
    heating = np.arange(7 * 2).reshape(7, 2) + 20
    cooling = heating + 20
    actual = heating + 40
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "get_Theta_HBR_i_2023",
        lambda *args: calls.append(args) or expected,
    )

    result = sut._get_actual_room_temperatures_at_hour(sut._ActualRoomTemperatureHourInputs(
        t,
        H,
        C,
        M,
        theta_star,
        supply,
        supply_theta,
        0.5,
        area_partition,
        2.7,
        area_room,
        heating,
        cooling,
        actual,
    ))

    assert result is expected
    args = calls[0]
    assert args[:4] == (H[t], C[t], M[t], theta_star[t])
    np.testing.assert_array_equal(args[4], supply[:, t : t + 1])
    np.testing.assert_array_equal(args[5], supply_theta[:, t : t + 1])
    assert args[6] == 0.5
    np.testing.assert_array_equal(args[7], area_partition.reshape(-1, 1))
    assert args[8] == 2.7
    np.testing.assert_array_equal(args[9], area_room.reshape(-1, 1))
    np.testing.assert_array_equal(args[10], heating[:5, t : t + 1])
    np.testing.assert_array_equal(args[11], cooling[:5, t : t + 1])
    expected_previous = np.zeros((5, 1)) if t == 0 else actual[:5, t - 1 : t]
    np.testing.assert_array_equal(args[12], expected_previous)

@pytest.mark.parametrize("t", (0, 1))
def test_actual_non_room_temperature_at_hour_preserves_slices(monkeypatch, t):
    calls = []
    H = np.array([True, False])
    C = np.array([False, True])
    M = np.array([False, False])
    theta_star_nr = np.array([18.0, 19.0])
    theta_star_hbr = np.array([20.0, 21.0])
    theta_hbr = np.arange(5 * 2).reshape(5, 2)
    ventilation_nr = np.array([30.0, 31.0])
    dash_supply = theta_hbr + 20
    supply = theta_hbr + 40
    area_partition = np.arange(1.0, 6.0)
    theta_nr = np.array([17.0, 0.0])
    monkeypatch.setattr(
        sut.jjj_carryover_heat,
        "get_Theta_NR_2023",
        lambda *args: calls.append(args) or 22.0,
    )

    result = sut._get_actual_non_room_temperature_at_hour(
        t,
        t == 0,
        H,
        C,
        M,
        theta_star_nr,
        theta_star_hbr,
        theta_hbr,
        40.0,
        ventilation_nr,
        dash_supply,
        supply,
        0.5,
        area_partition,
        2.7,
        theta_nr,
    )

    assert result == 22.0
    args = calls[0]
    assert args[:6] == (t == 0, H[t], C[t], M[t], theta_star_nr[t], theta_star_hbr[t])
    np.testing.assert_array_equal(args[6], theta_hbr[:, t : t + 1])
    assert args[7:9] == (40.0, ventilation_nr[t])
    np.testing.assert_array_equal(args[9], dash_supply[:, t : t + 1])
    np.testing.assert_array_equal(args[10], supply[:, t : t + 1])
    assert args[11] == 0.5
    np.testing.assert_array_equal(args[12], area_partition.reshape(-1, 1))
    assert args[13] == 2.7
    assert args[14] == (0 if t == 0 else theta_nr[t - 1])


@pytest.mark.parametrize(
    ("setting_type", "theta_uf", "expected_first", "expected_second"),
    (
        (sut.HeatingAcSetting, np.array([5.0, 25.0, 30.0]), np.array([15.0, 20.0, 30.0]), np.array([15.0, 20.0, 40.0])),
        (sut.CoolingAcSetting, np.array([15.0, 15.0, 30.0]), np.array([5.0, 20.0, 30.0]), np.array([5.0, 20.0, 35.0])),
    ),
)
def test_legacy_underfloor_requested_temperatures_preserve_first_pass_formula(
    monkeypatch, setting_type, theta_uf, expected_first, expected_second
):
    calls = []
    theta_req = np.array([
        [10.0, 20.0, 30.0],
        [10.0, 20.0, 35.0],
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ])
    theta_ex = np.array([0.0, 1.0, 2.0])
    airflows = np.arange(15.0).reshape(5, 3)
    r_a_ufvnt = object()
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(Q=2.7, underfloor_insulation=True)
    load = SimpleNamespace(L_H_d_t_i=object(), L_CS_d_t_i=object())

    def calc_theta(*args):
        calls.append(args)
        return theta_uf, object(), object()

    monkeypatch.setattr(sut.algo, "calc_Theta", calc_theta)

    result = sut._adjust_legacy_underfloor_requested_temperatures(
        _setting(setting_type), house, skin, load, r_a_ufvnt,
        theta_req, theta_ex, airflows
    )

    assert result is theta_req
    np.testing.assert_array_equal(result[0], expected_first)
    np.testing.assert_array_equal(result[1], expected_second)
    np.testing.assert_array_equal(result[2:], np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ]))
    assert len(calls) == 2
    assert [call[5] for call in calls] == [r_a_ufvnt, r_a_ufvnt]
    for index, call in enumerate(calls):
        np.testing.assert_array_equal(call[9], airflows[index])

@pytest.mark.parametrize(
    ("setting_type", "expected_first", "expected_second"),
    (
        (sut.HeatingAcSetting, np.array([10.0, 15.0, 30.0]), np.array([5.0, 15.0, 30.0])),
        (sut.CoolingAcSetting, np.array([15.0, 20.0, 30.0]), np.array([15.0, 25.0, 35.0])),
    ),
)
def test_carryover_underfloor_supply_temperatures_preserve_clipping(
    monkeypatch, setting_type, expected_first, expected_second
):
    calls = []
    theta_supply = np.array([
        [10.0, 20.0, 30.0],
        [5.0, 25.0, 35.0],
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ])
    theta_uf = np.array([15.0, 15.0, 30.0])
    theta_ex = np.array([0.0, 1.0, 2.0])
    airflows = np.arange(15.0).reshape(5, 3)
    r_a_ufvnt = object()
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(
        Q=2.7,
        YUCACO_r_A_ufvnt=r_a_ufvnt,
        underfloor_insulation=True,
    )
    load = SimpleNamespace(L_H_d_t_i=object(), L_CS_d_t_i=object())

    def calc_theta(*args):
        calls.append(args)
        return theta_uf, object(), object()

    monkeypatch.setattr(sut.algo, "calc_Theta", calc_theta)

    result = sut._adjust_carryover_underfloor_supply_temperatures(
        _setting(setting_type), house, skin, load,
        theta_supply, theta_ex, airflows
    )

    assert result is theta_supply
    np.testing.assert_array_equal(result[0], expected_first)
    np.testing.assert_array_equal(result[1], expected_second)
    np.testing.assert_array_equal(result[2:], np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ]))
    assert len(calls) == 2
    assert [call[5] for call in calls] == [r_a_ufvnt, r_a_ufvnt]


@pytest.mark.parametrize(
    ("setting_type", "heating_capacity", "cooling_capacity", "limit", "expected_first", "expected_third"),
    (
        (sut.HeatingAcSetting, 1000.0, None, 12.0, 12.0, 20.0),
        (sut.CoolingAcSetting, None, 1000.0, 8.0, 8.0, 8.0),
    ),
)
def test_new_underfloor_requested_temperatures_preserve_reverse_solve_and_limits(
    monkeypatch,
    setting_type,
    heating_capacity,
    cooling_capacity,
    limit,
    expected_first,
    expected_third,
):
    events = []
    theta_uf_2023 = np.full(8760, 14.0)
    theta_uf_supply = np.full(8760, 10.0)
    theta_req = np.full((5, 8760), 20.0)
    theta_ex = np.full(8760, 5.0)
    airflows = np.vstack([np.full(8760, float(i + 1)) for i in range(5)])
    l_star_h = object()
    l_star_cs = object()
    new_ufac = object()

    class FrameRecorder:
        def update_df(self, values):
            events.append(("update", values))

    frame = FrameRecorder()
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(Q=2.7, r_A_ufac=0.5, underfloor_insulation=True)
    load = SimpleNamespace(
        L_dash_H_R_d_t_i=object(),
        L_dash_CS_R_d_t_i=object(),
    )

    def calc_theta_uf(*args):
        events.append(("expected_underfloor", args))
        return theta_uf_2023

    def calc_theta(**kwargs):
        events.append(("reverse_solve", kwargs))
        return object(), object(), theta_uf_supply

    monkeypatch.setattr(sut, "calc_Theta_uf_d_t_2023", calc_theta_uf)
    monkeypatch.setattr(sut.algo, "calc_Theta", calc_theta)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda *_: heating_capacity)
    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda *_: cooling_capacity)

    result = sut._get_new_underfloor_requested_temperatures(
        _setting(setting_type), house, skin, load, new_ufac, frame,
        theta_req, theta_ex, airflows, np.array([limit]),
        l_star_h, l_star_cs
    )

    np.testing.assert_array_equal(result[0], np.full(8760, expected_first))
    np.testing.assert_array_equal(result[1], np.full(8760, expected_first))
    np.testing.assert_array_equal(result[2], np.full(8760, expected_third))
    assert [event[0] for event in events] == [
        "expected_underfloor", "reverse_solve", "update"
    ]
    expected_args = events[0][1]
    assert expected_args[0] is l_star_h
    assert expected_args[1] is l_star_cs
    reverse_kwargs = events[1][1]
    assert reverse_kwargs["calc_backwards"] is True
    assert reverse_kwargs["Theta_sa_d_t"] is theta_uf_2023
    np.testing.assert_array_equal(reverse_kwargs["V_sa_d_t_A"], airflows[0] + airflows[1])
    update_values = events[2][1]
    assert update_values["Theta_uf_d_t_2023"] is theta_uf_2023
    np.testing.assert_array_equal(update_values["Theta_req_d_t_1"], result[0])


def test_new_underfloor_supply_temperatures_preserve_forward_solve_and_outputs(
    monkeypatch,
):
    events = []
    theta_uf = np.full(8760, 11.0)
    theta_supply = np.vstack([np.full(8760, float(i + 1)) for i in range(5)])
    theta_hs_out = np.full(8760, 30.0)
    theta_ex = np.full(8760, 5.0)
    airflows = np.vstack([np.full(8760, float(i + 2)) for i in range(5)])
    new_ufac = object()

    class FrameRecorder:
        def update_df(self, values):
            events.append(("update", values))

    frame = FrameRecorder()
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(Q=2.7, r_A_ufac=0.5, underfloor_insulation=True)
    load = SimpleNamespace(
        L_dash_H_R_d_t_i=object(),
        L_dash_CS_R_d_t_i=object(),
    )

    def calc_theta(**kwargs):
        events.append(("forward_solve", kwargs))
        return theta_uf, object(), object()

    monkeypatch.setattr(sut.algo, "calc_Theta", calc_theta)

    result = sut._get_new_underfloor_supply_temperatures(
        house, skin, load, new_ufac, frame,
        theta_supply, theta_hs_out, theta_ex, airflows
    )

    np.testing.assert_array_equal(result[0], theta_uf)
    np.testing.assert_array_equal(result[1], theta_uf)
    np.testing.assert_array_equal(result[2:], theta_supply[2:])
    assert [event[0] for event in events] == ["forward_solve", "update"]
    forward_kwargs = events[0][1]
    assert forward_kwargs["calc_backwards"] is False
    assert forward_kwargs["Theta_sa_d_t"] is theta_hs_out
    np.testing.assert_array_equal(forward_kwargs["V_sa_d_t_A"], airflows[0] + airflows[1])
    update_values = events[1][1]
    assert update_values["Theta_hs_out_d_t"] is theta_hs_out
    assert update_values["Theta_uf_d_t"] is theta_uf
    np.testing.assert_array_equal(update_values["Theta_supply_d_t_1"], result[0])

@pytest.mark.parametrize(
    ("setting_type", "expected_first", "expected_second"),
    (
        (sut.HeatingAcSetting, np.array([10.0, 15.0, 30.0]), np.array([5.0, 15.0, 30.0])),
        (sut.CoolingAcSetting, np.array([15.0, 20.0, 30.0]), np.array([15.0, 25.0, 35.0])),
    ),
)
def test_legacy_underfloor_supply_temperatures_preserve_where_operation(
    monkeypatch, setting_type, expected_first, expected_second
):
    calls = []
    where_calls = []
    theta_supply = np.array([
        [10.0, 20.0, 30.0],
        [5.0, 25.0, 35.0],
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ])
    theta_uf = np.array([15.0, 15.0, 30.0])
    theta_ex = np.array([0.0, 1.0, 2.0])
    airflows = np.arange(15.0).reshape(5, 3)
    r_a_ufac = object()
    house = SimpleNamespace(region=6, A_A=120.0, A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(
        Q=2.7,
        r_A_ufac=r_a_ufac,
        underfloor_insulation=True,
    )
    load = SimpleNamespace(L_H_d_t_i=object(), L_CS_d_t_i=object())
    original_where = np.where

    def calc_theta(*args):
        calls.append(args)
        return theta_uf, object(), object()

    def recording_where(*args):
        where_calls.append(args)
        return original_where(*args)

    monkeypatch.setattr(sut.algo, "calc_Theta", calc_theta)
    monkeypatch.setattr(sut.np, "where", recording_where)
    monkeypatch.setattr(
        sut.np,
        "clip",
        lambda *_args, **_kwargs: pytest.fail("legacy phase must retain np.where"),
    )

    result = sut._adjust_legacy_underfloor_supply_temperatures(
        _setting(setting_type), house, skin, load,
        theta_supply, theta_ex, airflows
    )

    assert result is theta_supply
    np.testing.assert_array_equal(result[0], expected_first)
    np.testing.assert_array_equal(result[1], expected_second)
    np.testing.assert_array_equal(result[2:], np.array([
        [1.0, 2.0, 3.0],
        [4.0, 5.0, 6.0],
        [7.0, 8.0, 9.0],
    ]))
    assert len(calls) == 2
    assert len(where_calls) == 2
    assert [call[5] for call in calls] == [r_a_ufac, r_a_ufac]


def test_new_underfloor_balanced_loads_preserve_seasonal_masks_and_outputs(
    monkeypatch,
):
    calc_calls = []
    updates = []
    hours = 24 * 365
    heating = np.zeros(hours, dtype=bool)
    cooling = np.zeros(hours, dtype=bool)
    middle = np.zeros(hours, dtype=bool)
    heating[2] = True
    cooling[1] = True
    load_h = np.zeros((5, hours))
    load_cs = np.zeros((5, hours))
    load_h[1, 2] = 1.0
    load_cs[0, 1] = 1.0
    load = SimpleNamespace(
        L_H_d_t_i=load_h,
        L_CS_d_t_i=load_cs,
        L_CL_d_t_i=np.full((5, hours), 3.0),
    )
    l_star_h = np.full((5, hours), 10.0)
    l_star_cs = np.full((5, hours), 20.0)
    theta_room = np.arange(float(hours))
    theta_ex = np.zeros(hours)
    area = object()
    new_ufac = SimpleNamespace(U_s_floor_ins=0.8)

    class FrameRecorder:
        def update_df(self, values):
            updates.append(values)

    def calc_delta(u_value, area_value, temperature_difference):
        calc_calls.append((u_value, area_value, temperature_difference))
        return np.full((5, 1), 2.0)

    monkeypatch.setattr(sut.jjj_ufac_dc, "calc_delta_L_room2uf_i", calc_delta)
    monkeypatch.setattr(
        sut.dc,
        "get_season_array_d_t",
        lambda region: (heating, cooling, middle),
    )

    result_h, result_cs = sut._adjust_new_underfloor_balanced_loads(
        SimpleNamespace(region=6), new_ufac, FrameRecorder(), load, area,
        theta_room, theta_ex, l_star_h, l_star_cs
    )

    assert result_h is l_star_h
    assert result_cs is l_star_cs
    assert len(calc_calls) == hours
    assert calc_calls[0] == (0.8, area, 0.0)
    assert calc_calls[-1] == (0.8, area, float(hours - 1))
    assert result_cs[0, 1] == 18.0
    assert result_h[1, 2] == 8.0
    assert np.count_nonzero(result_cs != 20.0) == 1
    assert np.count_nonzero(result_h != 10.0) == 1
    assert len(updates) == 1
    assert tuple(updates[0]) == (
        "L_H_d_t_1", "L_H_d_t_2", "L_H_d_t_3", "L_H_d_t_4", "L_H_d_t_5",
        "L_CS_d_t_1", "L_CS_d_t_2", "L_CS_d_t_3", "L_CS_d_t_4", "L_CS_d_t_5",
        "L_CL_d_t_1", "L_CL_d_t_2", "L_CL_d_t_3", "L_CL_d_t_4", "L_CL_d_t_5",
        "L_star_CS_d_t_1", "L_star_CS_d_t_2", "L_star_CS_d_t_3", "L_star_CS_d_t_4", "L_star_CS_d_t_5",
        "L_star_H_d_t_1", "L_star_H_d_t_2", "L_star_H_d_t_3", "L_star_H_d_t_4", "L_star_H_d_t_5",
    )

def test_actual_room_temperatures_without_carryover_preserve_new_hour_order(
    monkeypatch,
):
    hours = 24 * 365
    call_count = 0
    boundary_calls = []
    theta_star = np.arange(float(hours))
    supply_airflow = np.vstack([np.arange(float(hours)) + i for i in range(5)])
    supply_temperature = supply_airflow + 10.0
    l_star_h = supply_airflow + 20.0
    l_star_cs = supply_airflow + 30.0
    theta_uf = np.arange(float(hours)) + 40.0
    hcm = np.arange(hours) % 3
    area_underfloor = np.arange(5.0).reshape(5, 1)
    area_partition = np.arange(5.0)
    area_hcz = np.arange(5.0) + 10.0

    class Climate:
        def get_HCM_d_t(self):
            return hcm

    def get_area(*args):
        boundary_calls.append(("area", args))
        return area_underfloor, object()

    def get_theta_hbr(**kwargs):
        nonlocal call_count
        if call_count in (0, hours - 1):
            boundary_calls.append(("hour", call_count, kwargs))
        call_count += 1
        return np.full((5, 1), kwargs["Theta_uf"])

    monkeypatch.setattr(sut.jjj_ufac_dc, "get_A_s_ufac_i", get_area)
    monkeypatch.setattr(sut, "get_Theta_HBR_i", get_theta_hbr)
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_HBR_d_t_i",
        lambda *_: pytest.fail("new branch must not call the legacy formula"),
    )

    result = sut._get_actual_room_temperatures_without_carryover(
        SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0, region=6),
        SimpleNamespace(Q=2.7),
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更する),
        Climate(), theta_star, supply_airflow, supply_temperature,
        0.5, area_partition, area_hcz, l_star_h, l_star_cs, theta_uf
    )

    assert result.shape == (5, hours)
    np.testing.assert_array_equal(result[0], theta_uf)
    assert call_count == hours
    assert boundary_calls[0] == ("area", (120.0, 30.0, 50.0))
    first = boundary_calls[1][2]
    last = boundary_calls[2][2]
    assert first["Theta_star_HBR"] == theta_star[0]
    assert last["Theta_star_HBR"] == theta_star[-1]
    assert first["HCM"] == hcm[0]
    assert last["HCM"] == hcm[-1]
    np.testing.assert_array_equal(first["V_supply_i"], supply_airflow[:, 0:1])
    np.testing.assert_array_equal(last["V_supply_i"], supply_airflow[:, -1:])
    np.testing.assert_array_equal(first["A_prt_i"], area_partition.reshape(-1, 1)[:5, :])
    np.testing.assert_array_equal(first["A_s_ufac_i"], area_underfloor[:5, :])


def test_actual_room_temperatures_without_carryover_preserve_legacy_formula(
    monkeypatch,
):
    calls = []
    result = object()
    house = SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0, region=6)
    skin = SimpleNamespace(Q=2.7)
    values = [object() for _ in range(9)]

    monkeypatch.setattr(
        sut,
        "get_Theta_HBR_i",
        lambda **_: pytest.fail("legacy branch must not call the new formula"),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_HBR_d_t_i",
        lambda *args: calls.append(args) or result,
    )

    actual = sut._get_actual_room_temperatures_without_carryover(
        house, skin,
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更しない),
        object(), *values
    )

    assert actual is result
    assert calls == [(
        values[0], values[1], values[2], values[3], values[4], 2.7,
        values[5], values[6], values[7], 6,
    )]

def test_actual_non_room_temperatures_without_carryover_preserve_new_hour_order(
    monkeypatch,
):
    hours = 24 * 365
    call_count = 0
    boundary_calls = []
    theta_star_nr = np.arange(float(hours))
    theta_star_hbr = theta_star_nr + 10.0
    theta_hbr = np.vstack([theta_star_nr + i for i in range(5)])
    vent_nr = theta_star_nr + 20.0
    dash_supply = theta_hbr + 30.0
    supply = theta_hbr + 40.0
    theta_uf = theta_star_nr + 50.0
    area_partition = np.arange(5.0)
    r_area = object()

    def get_theta_nr(**kwargs):
        nonlocal call_count
        if call_count in (0, hours - 1):
            boundary_calls.append((call_count, kwargs))
        call_count += 1
        return kwargs["Theta_uf"]

    monkeypatch.setattr(sut, "get_Theta_NR", get_theta_nr)
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_NR_d_t",
        lambda *_: pytest.fail("new branch must not call the legacy formula"),
    )

    result = sut._get_actual_non_room_temperatures_without_carryover(
        SimpleNamespace(Q=2.7),
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更する),
        theta_star_nr, theta_star_hbr, theta_hbr, 45.0, vent_nr,
        dash_supply, supply, 0.5, area_partition, theta_uf, r_area
    )

    np.testing.assert_array_equal(result, theta_uf)
    assert call_count == hours
    first = boundary_calls[0][1]
    last = boundary_calls[1][1]
    assert first["Theta_star_NR"] == theta_star_nr[0]
    assert last["Theta_star_NR"] == theta_star_nr[-1]
    assert first["V_vent_l_NR"] == vent_nr[0]
    assert last["V_vent_l_NR"] == vent_nr[-1]
    np.testing.assert_array_equal(first["Theta_HBR_i"], theta_hbr[:, 0:1])
    np.testing.assert_array_equal(last["Theta_HBR_i"], theta_hbr[:, -1:])
    np.testing.assert_array_equal(first["A_prt_i"], area_partition.reshape(-1, 1))
    assert first["r_A_NR_1F_excl_bath"] is r_area


def test_actual_non_room_temperatures_without_carryover_preserve_legacy_formula(
    monkeypatch,
):
    calls = []
    result = object()
    values = [object() for _ in range(11)]

    monkeypatch.setattr(
        sut,
        "get_Theta_NR",
        lambda **_: pytest.fail("legacy branch must not call the new formula"),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_NR_d_t",
        lambda *args: calls.append(args) or result,
    )

    actual = sut._get_actual_non_room_temperatures_without_carryover(
        SimpleNamespace(Q=2.7),
        SimpleNamespace(new_ufac_flg=sut.床下空調ロジック.変更しない),
        *values
    )

    assert actual is result
    assert calls == [(
        values[0], values[1], values[2], values[3], values[4],
        values[5], values[6], values[7], values[8], 2.7,
    )]

def test_new_balanced_non_room_temperature_preserves_formula_52_inputs(
    monkeypatch,
):
    calls = []
    result = object()
    r_area = object()
    theta_star_hbr = np.array([20.0, 21.0, 22.0])
    theta_in = np.array([15.0, 16.0, 17.0])
    theta_uf = np.array([18.0, 19.0, 20.0])
    vent_nr = np.array([1.0, 2.0, 3.0])
    dash_supply = np.arange(15.0).reshape(5, 3)
    load_h = np.arange(21.0).reshape(7, 3)
    load_cs = load_h + 30.0
    area_partition = np.arange(5.0)
    hcm = np.array([1, 2, 3])

    class Climate:
        def get_HCM_d_t(self):
            calls.append(("hcm",))
            return hcm

    def vectorize(function):
        calls.append(("vectorize", function))

        def invoke(**kwargs):
            calls.append(("invoke", kwargs))
            return result

        return invoke

    monkeypatch.setattr(sut.np, "vectorize", vectorize)
    monkeypatch.setattr(
        sut.jjj_ufac_dc,
        "get_r_A_NR_uf_1F_excl_bath",
        lambda: calls.append(("area_ratio",)) or r_area,
    )

    actual, actual_r_area = sut._get_new_balanced_non_room_temperature(
        SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0),
        SimpleNamespace(Q=2.7), Climate(),
        SimpleNamespace(L_H_d_t_i=load_h, L_CS_d_t_i=load_cs),
        45.0, area_partition, 0.5, vent_nr, dash_supply,
        theta_star_hbr, theta_in, theta_uf
    )

    assert actual is result
    assert actual_r_area is r_area
    assert [call[0] for call in calls] == [
        "hcm", "area_ratio", "vectorize", "invoke"
    ]
    assert calls[2][1] is sut.get_Theta_star_NR
    kwargs = calls[3][1]
    np.testing.assert_array_equal(
        kwargs["V_dash_supply_A"], np.sum(dash_supply[0:5, :], axis=0)
    )
    np.testing.assert_array_equal(
        kwargs["L_H_NR_A"], np.sum(load_h[5:, :], axis=0)
    )
    np.testing.assert_array_equal(
        kwargs["L_CS_NR_A"], np.sum(load_cs[5:, :], axis=0)
    )
    assert kwargs["A_prt_A"] == np.sum(area_partition)
    assert kwargs["Q"] == 2.7
    assert kwargs["A_NR"] == 45.0
    assert kwargs["U_prt"] == 0.5
    assert kwargs["Theta_NR"] is theta_in
    assert kwargs["Theta_uf"] is theta_uf
    np.testing.assert_array_equal(kwargs["HCM"], hcm)
    assert kwargs["r_A_NR_1F_excl_bath"] is r_area

def test_actual_non_room_humidity_preserves_formula_49_and_output_order(
    monkeypatch,
):
    events = []
    theta_star = object()
    humidity = object()

    class FrameRecorder:
        def __setitem__(self, key, value):
            events.append(("setitem", key, value))

    monkeypatch.setattr(
        sut.dc,
        "get_X_NR_d_t",
        lambda value: events.append(("formula", value)) or humidity,
    )

    result = sut._get_actual_non_room_humidity(FrameRecorder(), theta_star)

    assert result is humidity
    assert events == [
        ("formula", theta_star),
        ("setitem", "X_NR_d_t", humidity),
    ]

def test_actual_room_humidities_preserve_formula_47_assign_generation(
    monkeypatch,
):
    events = []
    theta_star = object()
    humidity = np.arange(15.0).reshape(5, 3)
    frame = _FrameRecorder(events)

    monkeypatch.setattr(
        sut.dc,
        "get_X_HBR_d_t_i",
        lambda value: events.append(("formula", value)) or humidity,
    )

    result, next_frame = sut._get_actual_room_humidities(frame, theta_star)

    assert result is humidity
    assert next_frame.generation == 1
    assert events[0] == ("formula", theta_star)
    assert events[1][0:2] == ("assign", 0)
    columns = events[1][2]
    assert tuple(name for name, _ in columns) == (
        "X_HBR_d_t_1", "X_HBR_d_t_2", "X_HBR_d_t_3",
        "X_HBR_d_t_4", "X_HBR_d_t_5",
    )
    for index, (_, value) in enumerate(columns):
        np.testing.assert_array_equal(value, humidity[index])

def test_partition_heat_transfers_preserve_formula_11_assign_generation(
    monkeypatch,
):
    events = []
    inputs = [object() for _ in range(4)]
    transfers = np.arange(15.0).reshape(5, 3)
    frame = _FrameRecorder(events)

    monkeypatch.setattr(
        sut.dc,
        "get_Q_star_trs_prt_d_t_i",
        lambda *args: events.append(("formula", args)) or transfers,
    )

    result, next_frame = sut._get_partition_heat_transfers(frame, *inputs)

    assert result is transfers
    assert next_frame.generation == 1
    assert events[0] == ("formula", tuple(inputs))
    assert events[1][0:2] == ("assign", 0)
    columns = events[1][2]
    assert tuple(name for name, _ in columns) == (
        "Q_star_trs_prt_d_t_i_1", "Q_star_trs_prt_d_t_i_2",
        "Q_star_trs_prt_d_t_i_3", "Q_star_trs_prt_d_t_i_4",
        "Q_star_trs_prt_d_t_i_5",
    )
    for index, (_, value) in enumerate(columns):
        np.testing.assert_array_equal(value, transfers[index])

def test_balanced_latent_cooling_loads_preserve_formula_10_assign_generation(
    monkeypatch,
):
    events = []
    sensible = object()
    latent = object()
    loads = np.arange(15.0).reshape(5, 3)
    load = SimpleNamespace(L_CS_d_t_i=sensible, L_CL_d_t_i=latent)
    frame = _FrameRecorder(events)

    monkeypatch.setattr(
        sut.dc,
        "get_L_star_CL_d_t_i",
        lambda *args: events.append(("formula", args)) or loads,
    )

    result, next_frame = sut._get_balanced_latent_cooling_loads(
        frame, load, 6
    )

    assert result is loads
    assert next_frame.generation == 1
    assert events[0] == ("formula", (sensible, latent, 6))
    assert events[1][0:2] == ("assign", 0)
    columns = events[1][2]
    assert tuple(name for name, _ in columns) == (
        "L_star_CL_d_t_i_1", "L_star_CL_d_t_i_2",
        "L_star_CL_d_t_i_3", "L_star_CL_d_t_i_4",
        "L_star_CL_d_t_i_5",
    )
    for index, (_, value) in enumerate(columns):
        np.testing.assert_array_equal(value, loads[index])

def test_prepare_climate_conditions_preserves_fetch_and_write_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]

    class Climate:
        def __init__(self, region, new_ufac, climate_file):
            events.append(("init", region, new_ufac, climate_file))

        def get_Theta_ex_d_t(self):
            events.append(("fetch", "Theta"))
            return values[0]

        def get_X_ex_d_t(self):
            events.append(("fetch", "X"))
            return values[1]

        def get_J_d_t(self):
            events.append(("fetch", "J"))
            return values[2]

        def get_h_ex_d_t(self):
            events.append(("fetch", "h"))
            return values[3]

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    new_ufac = object()
    climate_file = object()
    monkeypatch.setattr(sut, "ClimateService", Climate)

    result = sut._prepare_climate_conditions(
        Frame(), SimpleNamespace(region=6), new_ufac, climate_file
    )

    assert isinstance(result[0], Climate)
    assert result[1:] == tuple(values)
    assert events == [
        ("init", 6, new_ufac, climate_file),
        ("fetch", "Theta"), ("fetch", "X"),
        ("fetch", "J"), ("fetch", "h"),
        ("write", "Theta_ex_d_t", values[0]),
        ("write", "X_ex_d_t", values[1]),
        ("write", "J_d_t", values[2]),
        ("write", "h_ex_d_t", values[3]),
    ]

def test_prepare_dwelling_areas_and_water_heat_preserves_order(monkeypatch):
    events = []

    class Frame:
        def __init__(self, name):
            self.name = name

        def __setitem__(self, key, value):
            events.append(("write", self.name, key, value))

    monkeypatch.setattr(
        sut.ld, "get_A_HCZ_i",
        lambda i, *areas: events.append(("HCZ", i, areas)) or float(i),
    )
    monkeypatch.setattr(
        sut.ld, "get_A_HCZ_R_i",
        lambda i: events.append(("HCZR", i)) or float(i + 10),
    )
    monkeypatch.setattr(
        sut.ld, "get_A_NR",
        lambda *areas: events.append(("NR", areas)) or 40.0,
    )
    monkeypatch.setattr(
        sut.dc, "get_L_wtr",
        lambda: events.append(("water",)) or 2500.0,
    )

    result = sut._prepare_dwelling_areas_and_water_heat(
        Frame("df2"), Frame("df3"),
        SimpleNamespace(A_A=120.0, A_MR=30.0, A_OR=50.0),
    )

    np.testing.assert_array_equal(result[0], np.arange(1.0, 6.0))
    np.testing.assert_array_equal(result[1], np.arange(11.0, 16.0))
    assert result[2:] == (40.0, 2500.0)
    assert [event[0] for event in events[:11]] == [
        "HCZ", "HCZ", "HCZ", "HCZ", "HCZ",
        "HCZR", "HCZR", "HCZR", "HCZR", "HCZR", "NR",
    ]
    assert [(event[1], event[2]) for event in events[11:14]] == [
        ("df2", "A_HCZ_i"), ("df2", "A_HCZ_R_i"), ("df3", "A_NR"),
    ]
    assert events[14] == ("water",)
    assert events[15][0:3] == ("write", "df3", "L_wtr")

def test_prepare_occupancy_state_preserves_formula_66_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    monkeypatch.setattr(sut.dc, "calc_n_p_NR_d_t", lambda x: events.append(("NR", x)) or values[0])
    monkeypatch.setattr(sut.dc, "calc_n_p_OR_d_t", lambda x: events.append(("OR", x)) or values[1])
    monkeypatch.setattr(sut.dc, "calc_n_p_MR_d_t", lambda x: events.append(("MR", x)) or values[2])
    monkeypatch.setattr(sut.dc, "get_n_p_d_t", lambda *x: events.append(("total", x)) or values[3])

    result = sut._prepare_occupancy_state(
        Frame(), SimpleNamespace(A_OR=50.0, A_MR=30.0), 40.0
    )

    assert result is values[3]
    assert [event[0] for event in events] == [
        "NR", "write", "OR", "write", "MR", "write", "total", "write"
    ]
    assert events[6][1] == (values[2], values[1], values[0])
    assert [events[i][1] for i in (1, 3, 5, 7)] == [
        "n_p_NR_d_t", "n_p_OR_d_t", "n_p_MR_d_t", "n_p_d_t"
    ]

def test_prepare_internal_moisture_state_preserves_formula_65_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    monkeypatch.setattr(sut.dc, "calc_w_gen_NR_d_t", lambda x: events.append(("NR", x)) or values[0])
    monkeypatch.setattr(sut.dc, "calc_w_gen_OR_d_t", lambda x: events.append(("OR", x)) or values[1])
    monkeypatch.setattr(sut.dc, "calc_w_gen_MR_d_t", lambda x: events.append(("MR", x)) or values[2])
    monkeypatch.setattr(sut.dc, "get_w_gen_d_t", lambda *x: events.append(("total", x)) or values[3])

    result = sut._prepare_internal_moisture_state(
        Frame(), SimpleNamespace(A_OR=50.0, A_MR=30.0), 40.0
    )

    assert result is values[3]
    assert [event[0] for event in events] == [
        "NR", "write", "OR", "write", "MR", "write", "total", "write"
    ]
    assert events[6][1] == (values[2], values[1], values[0])
    assert [events[i][1] for i in (1, 3, 5, 7)] == [
        "w_gen_NR_d_t", "w_gen_OR_d_t", "w_gen_MR_d_t", "w_gen_d_t"
    ]

def test_prepare_internal_heat_state_preserves_formula_64_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    monkeypatch.setattr(sut.dc, "calc_q_gen_NR_d_t", lambda x: events.append(("NR", x)) or values[0])
    monkeypatch.setattr(sut.dc, "calc_q_gen_OR_d_t", lambda x: events.append(("OR", x)) or values[1])
    monkeypatch.setattr(sut.dc, "calc_q_gen_MR_d_t", lambda x: events.append(("MR", x)) or values[2])
    monkeypatch.setattr(sut.dc, "get_q_gen_d_t", lambda *x: events.append(("total", x)) or values[3])

    result = sut._prepare_internal_heat_state(
        Frame(), SimpleNamespace(A_OR=50.0, A_MR=30.0), 40.0
    )

    assert result is values[3]
    assert [event[0] for event in events] == [
        "NR", "write", "OR", "write", "MR", "write", "total", "write"
    ]
    assert events[6][1] == (values[2], values[1], values[0])
    assert [events[i][1] for i in (1, 3, 5, 7)] == [
        "q_gen_NR_d_t", "q_gen_OR_d_t", "q_gen_MR_d_t", "q_gen_d_t"
    ]

def test_prepare_local_ventilation_state_preserves_formula_63_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]
    frame = _FrameRecorder(events)
    monkeypatch.setattr(sut.dc, "get_V_vent_l_NR_d_t", lambda: events.append(("NR",)) or values[0])
    monkeypatch.setattr(sut.dc, "get_V_vent_l_OR_d_t", lambda: events.append(("OR",)) or values[1])
    monkeypatch.setattr(sut.dc, "get_V_vent_l_MR_d_t", lambda: events.append(("MR",)) or values[2])
    monkeypatch.setattr(sut.dc, "get_V_vent_l_d_t", lambda *x: events.append(("total", x)) or values[3])
    nr, total, next_frame = sut._prepare_local_ventilation_state(frame)
    assert (nr, total) == (values[0], values[3])
    assert next_frame.generation == 1
    assert [e[0] for e in events] == ["NR", "OR", "MR", "total", "assign"]
    assert events[3][1] == (values[2], values[1], values[0])
    assert tuple(name for name, _ in events[4][2]) == (
        "V_vent_l_NR_d_t", "V_vent_l_OR_d_t", "V_vent_l_MR_d_t", "V_vent_l_d_t"
    )

@pytest.mark.parametrize("direct", (True, False))
def test_prepare_general_ventilation_state_preserves_formula_62_branch(monkeypatch, direct):
    events = []
    base = object()
    adjusted = object()

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    monkeypatch.setattr(sut.dc, "get_V_vent_g_i", lambda *x: events.append(("base", x)) or base)
    monkeypatch.setattr(sut, "rescale_V_vent_g_i", lambda *x: events.append(("scale", x)) or adjusted)
    setting = SimpleNamespace(
        input_V_hs_min=(sut.最低風量直接入力.入力する if direct else sut.最低風量直接入力.入力しない),
        V_hs_min=500.0,
    )
    a_hcz, ratios = object(), object()
    result = sut._prepare_general_ventilation_state(Frame(), setting, a_hcz, ratios)
    assert result is (adjusted if direct else base)
    assert events[0] == ("base", (a_hcz, ratios))
    assert [e[0] for e in events] == (["base", "scale", "write"] if direct else ["base", "write"])
    if direct:
        assert events[1] == ("scale", (base, 500.0))
    assert events[-1][1] == "V_vent_g_i"
    assert events[-1][2] is result

def test_prepare_partition_state_preserves_formula_61_60_order(monkeypatch):
    events = []
    u_value, areas = object(), object()

    class Frame:
        def __init__(self, name): self.name = name
        def __setitem__(self, key, value): events.append(("write", self.name, key, value))

    monkeypatch.setattr(sut.dc, "get_U_prt", lambda: events.append(("U",)) or u_value)
    monkeypatch.setattr(sut.dc, "get_A_prt_i", lambda *x: events.append(("A", x)) or areas)
    house = SimpleNamespace(A_MR=30.0, A_OR=50.0)
    skin = SimpleNamespace(r_env=0.4)
    hcz, a_nr = object(), 40.0
    result = sut._prepare_partition_state(Frame("df2"), Frame("df3"), house, skin, hcz, a_nr)
    assert result == (u_value, areas)
    assert [e[0] for e in events] == ["U", "write", "A", "write", "write"]
    assert events[2] == ("A", (hcz, 0.4, 30.0, 40.0, 50.0))
    assert [(events[i][1], events[i][2]) for i in (1, 3, 4)] == [
        ("df3", "U_prt"), ("df3", "r_env"), ("df2", "A_prt_i")
    ]

def test_prepare_duct_geometry_state_preserves_formula_59_to_56_order(monkeypatch):
    events = []
    values = [object() for _ in range(4)]

    class Frame:
        def __init__(self, name):
            self.name = name

        def __setitem__(self, key, value):
            events.append(("write", self.name, key, value))

    monkeypatch.setattr(
        sut.dc, "get_Theta_SAT_d_t",
        lambda *args: events.append(("sat", args)) or values[0])
    monkeypatch.setattr(
        sut.dc, "get_l_duct_ex_i",
        lambda *args: events.append(("ex", args)) or values[1])
    monkeypatch.setattr(
        sut.dc, "get_l_duct_in_i",
        lambda *args: events.append(("in", args)) or values[2])
    monkeypatch.setattr(
        sut.dc, "get_l_duct__i",
        lambda *args: events.append(("total", args)) or values[3])

    theta_ex, solar = object(), object()
    result = sut._prepare_duct_geometry_state(
        Frame("df"), Frame("df2"), SimpleNamespace(A_A=120.0), theta_ex, solar)

    assert result == tuple(values)
    assert [event[0] for event in events] == [
        "sat", "write", "ex", "write", "in", "write", "total", "write"
    ]
    assert events[0][1] == (theta_ex, solar)
    assert events[2][1] == (120.0,)
    assert events[4][1] == (120.0,)
    assert events[6][1] == (values[2], values[1])
    assert [(events[i][1], events[i][2]) for i in (1, 3, 5, 7)] == [
        ("df", "Theta_SAT_d_t"),
        ("df2", "l_duct_ex_i"),
        ("df2", "l_duct_in_i"),
        ("df2", "l_duct_i"),
    ]


def test_prepare_balanced_room_and_duct_state_preserves_formula_order(monkeypatch):
    events = []
    values = [object(), object(), object(), tuple(object() for _ in range(5))]
    frame = _FrameRecorder(events)

    monkeypatch.setattr(
        sut.dc, "get_X_star_HBR_d_t",
        lambda *args: events.append(("humidity", args)) or values[0])
    monkeypatch.setattr(
        sut.dc, "get_Theta_star_HBR_d_t",
        lambda *args: events.append(("temperature", args)) or values[1])
    monkeypatch.setattr(
        sut.dc, "get_Theta_attic_d_t",
        lambda *args: events.append(("attic", args)) or values[2])
    monkeypatch.setattr(
        sut.dc, "get_Theta_sur_d_t_i",
        lambda *args: events.append(("surrounding", args)) or values[3])

    setting = SimpleNamespace(duct_insulation="outside")
    house = SimpleNamespace(region=6)
    x_ex, theta_ex, theta_sat, duct_in, duct_ex = [object() for _ in range(5)]
    result = sut._prepare_balanced_room_and_duct_state(
        frame, setting, house, x_ex, theta_ex, theta_sat, duct_in, duct_ex)

    assert result[:4] == tuple(values)
    assert result[4].generation == 1
    assert [event[0] for event in events] == [
        "humidity", "setitem", "temperature", "setitem",
        "attic", "setitem", "surrounding", "assign",
    ]
    assert events[0][1] == (x_ex, 6)
    assert events[2][1] == (theta_ex, 6)
    assert events[4][1] == (theta_sat, values[1])
    assert events[6][1] == (values[1], values[2], duct_in, duct_ex, "outside")
    assert [events[i][2] for i in (1, 3, 5)] == [
        "X_star_HBR_d_t", "Theta_star_HBR_d_t", "Theta_attic_d_t"
    ]
    assert tuple(name for name, _ in events[7][2]) == (
        "Theta_sur_d_t_i_1",
        "Theta_sur_d_t_i_2",
        "Theta_sur_d_t_i_3",
        "Theta_sur_d_t_i_4",
        "Theta_sur_d_t_i_5",
    )

def test_prepare_initial_heat_source_output_preserves_formula_40_arguments(monkeypatch):
    events = []
    values = (object(), object())
    frame = _FrameRecorder(events)

    monkeypatch.setattr(
        sut.dc,
        "calc_Q_hat_hs_d_t",
        lambda *args: events.append(("formula", args)) or values,
    )
    house = SimpleNamespace(A_A=120.0, region=6)
    skin = SimpleNamespace(Q=2.4, mu_H=0.08, mu_C=0.05)
    inputs = [object() for _ in range(12)]
    result = sut._prepare_initial_heat_source_output(sut._InitialHeatSourceOutputInputs(
        frame,
        house,
        skin,
        *inputs,
    ))

    assert result == values
    assert [event[0] for event in events] == ["formula", "setitem"]
    assert events[0][1] == (
        2.4,
        120.0,
        inputs[0],
        inputs[1],
        0.08,
        0.05,
        *inputs[2:],
        6,
    )
    assert events[1][2] == "Q_hat_hs_d_t"
    assert events[1][3] is values[0]

def test_prepare_minimum_heat_source_airflow_preserves_formula_39_write(monkeypatch):
    events = []
    value = object()

    class Frame:
        def __setitem__(self, key, item):
            events.append(("write", key, item))

    ventilation = object()
    monkeypatch.setattr(
        sut.dc,
        "get_V_hs_min",
        lambda arg: events.append(("formula", arg)) or value,
    )

    result = sut._prepare_minimum_heat_source_airflow(Frame(), ventilation)

    assert result is value
    assert events == [
        ("formula", ventilation),
        ("write", "V_hs_min", [value]),
    ]

def test_prepare_rated_heat_source_capacity_state_preserves_write_order(monkeypatch):
    events = []
    heating, cooling = object(), object()

    class Frame:
        def __setitem__(self, key, value):
            events.append(("write", key, value))

    inputs = [object() for _ in range(4)]
    monkeypatch.setattr(
        sut,
        "_get_rated_heat_source_capacities",
        lambda *args: events.append(("prepare", args))
        or sut._RatedHeatSourceCapacitiesResult(heating, cooling),
    )

    result = sut._prepare_rated_heat_source_capacity_state(Frame(), *inputs)

    assert result == (heating, cooling)
    assert events == [
        ("prepare", tuple(inputs)),
        ("write", "Q_hs_rtd_C", [cooling]),
        ("write", "Q_hs_rtd_H", [heating]),
    ]

@pytest.mark.parametrize("enabled", (True, False))
def test_prepare_underfloor_adjustment_state_preserves_ground_response_and_flag(
        monkeypatch, enabled):
    events = []
    ground = sut._UnderfloorGroundResponseResult(
        *(object() for _ in range(4)))
    setting, theta_ex = object(), object()
    flag = sut.床下空調ロジック.変更する if enabled else object()
    monkeypatch.setattr(
        sut,
        "_prepare_underfloor_ground_response",
        lambda *args: events.append(("ground", args)) or ground,
    )

    result = sut._prepare_underfloor_adjustment_state(
        setting, SimpleNamespace(new_ufac_flg=flag), theta_ex)

    assert result[:4] == ground
    assert result[4] is enabled
    assert events == [("ground", (setting, theta_ex))]

@pytest.mark.parametrize("should_adjust", (False, True))
def test_prepare_pre_vav_airflow_state_preserves_optional_recalculation(
        monkeypatch, should_adjust):
    events = []
    df_output = _FrameRecorder(events)

    class Output2:
        def __setitem__(self, key, value):
            events.append(("output2", key, value))

    hs_first, hs_second = object(), object()
    hs_outputs = [hs_first, hs_second]
    r_static = tuple(object() for _ in range(5))
    r_hourly = tuple(object() for _ in range(5))
    v_supply = tuple(object() for _ in range(5))
    q_initial, q_room, q_outdoor, q_ground = [object() for _ in range(4)]
    u_s, a_s, r_a, theta_uf = [object() for _ in range(4)]

    monkeypatch.setattr(
        sut,
        "_get_heat_source_supply_airflow_before_vav",
        lambda *args: events.append(("heat_airflow", args)) or hs_outputs.pop(0),
    )
    monkeypatch.setattr(
        sut,
        "_get_supply_airflow_before_vav",
        lambda *args: events.append(("supply_airflow", args))
        or sut._SupplyAirflowBeforeVavResult(
            r_static, r_hourly, v_supply),
    )
    monkeypatch.setattr(
        sut,
        "_adjust_heat_source_output_for_room_to_underfloor_transfer",
        lambda *args: events.append(("room", args))
        or sut._RoomToUnderfloorTransferResult(q_room, u_s, a_s, r_a),
    )
    monkeypatch.setattr(
        sut,
        "_adjust_heat_source_output_for_underfloor_to_outdoor_transfer",
        lambda *args: events.append(("outdoor", args)) or (q_outdoor, theta_uf),
    )
    monkeypatch.setattr(
        sut,
        "_adjust_heat_source_output_for_underfloor_to_ground_transfer",
        lambda *args: events.append(("ground", args)) or q_ground,
    )

    context = [object() for _ in range(18)]
    q_sensible = object()
    result = sut._prepare_pre_vav_airflow_state(sut._PreVavAirflowInputs(
        df_output,
        Output2(),
        *context[:12],
        q_initial,
        q_sensible,
        *context[12:],
        should_adjust,
    ))

    expected_names = ["heat_airflow", "setitem", "supply_airflow"]
    if should_adjust:
        expected_names += ["room", "outdoor", "ground", "heat_airflow", "setitem", "supply_airflow"]
    expected_names += ["output2", "assign", "assign"]
    assert [event[0] for event in events] == expected_names
    assert result[0] is (a_s if should_adjust else None)
    assert result[1] is (theta_uf if should_adjust else None)
    assert result[2:5] == (r_static, r_hourly, v_supply)
    assert result[5].generation == 2
    assert events[-3] == ("output2", "r_supply_des_i", r_static)
    assert tuple(name for name, _ in events[-2][2]) == tuple(
        f"r_supply_des_d_t_{i}" for i in range(1, 6))
    assert tuple(name for name, _ in events[-1][2]) == tuple(
        f"V_dash_supply_d_t_{i}" for i in range(1, 6))
    heat_calls = [event for event in events if event[0] == "heat_airflow"]
    assert heat_calls[0][1][-2] is q_initial
    if should_adjust:
        assert heat_calls[1][1][-2] is q_ground

def test_prepare_balanced_non_room_humidity_preserves_formula_53_arguments(monkeypatch):
    events = []
    value = object()
    frame = _FrameRecorder(events)
    house = SimpleNamespace(region=6)
    load = SimpleNamespace(L_CL_d_t_i=object())
    inputs = [object() for _ in range(4)]
    monkeypatch.setattr(
        sut.dc,
        "get_X_star_NR_d_t",
        lambda *args: events.append(("formula", args)) or value,
    )

    result = sut._prepare_balanced_non_room_humidity(
        frame, house, load, *inputs)

    assert result is value
    assert events[0] == (
        "formula",
        (inputs[0], load.L_CL_d_t_i, inputs[1], inputs[2], inputs[3], 6),
    )
    assert events[1] == ("setitem", 0, "X_star_NR_d_t", value)

@pytest.mark.parametrize("enabled", (True, False))
def test_prepare_balanced_non_room_temperature_preserves_formula_52_branch(
        monkeypatch, enabled):
    events = []
    frame = _FrameRecorder(events)
    theta, ratio = object(), object()
    flag = sut.床下空調ロジック.変更する if enabled else object()
    new_ufac = SimpleNamespace(new_ufac_flg=flag)
    house = SimpleNamespace(region=6)
    skin = SimpleNamespace(Q=2.4)
    load = SimpleNamespace(L_H_d_t_i=object(), L_CS_d_t_i=object())
    inputs = [object() for _ in range(8)]
    monkeypatch.setattr(
        sut,
        "_get_new_balanced_non_room_temperature",
        lambda *args: events.append(("new", args)) or (theta, ratio),
    )
    monkeypatch.setattr(
        sut.dc,
        "get_Theta_star_NR_d_t",
        lambda *args: events.append(("legacy", args)) or theta,
    )

    result = sut._prepare_balanced_non_room_temperature(sut._BalancedNonRoomTemperatureInputs(
        frame, new_ufac, house, skin, object(), load, *inputs))

    assert result == (theta, ratio if enabled else None)
    assert [event[0] for event in events] == [
        "new" if enabled else "legacy", "setitem"
    ]
    assert events[-1] == ("setitem", 0, "Theta_star_NR_d_t", theta)
    if not enabled:
        assert events[0][1] == (
            inputs[5], 2.4, inputs[0], inputs[3], inputs[4], inputs[2],
            inputs[1], load.L_H_d_t_i, load.L_CS_d_t_i, 6,
        )

def test_prepare_actual_humidity_state_preserves_formula_49_47_order(monkeypatch):
    events = []
    frame, next_frame = object(), object()
    x_nr, x_hbr = object(), object()
    star_nr, star_hbr = object(), object()
    monkeypatch.setattr(
        sut,
        "_get_actual_non_room_humidity",
        lambda *args: events.append(("non_room", args)) or x_nr,
    )
    monkeypatch.setattr(
        sut,
        "_get_actual_room_humidities",
        lambda *args: events.append(("room", args)) or (x_hbr, next_frame),
    )

    result = sut._prepare_actual_humidity_state(frame, star_nr, star_hbr)

    assert result == (x_nr, x_hbr, next_frame)
    assert events == [
        ("non_room", (frame, star_nr)),
        ("room", (frame, star_hbr)),
    ]

def test_prepare_balanced_load_state_preserves_formula_11_10_generations(monkeypatch):
    events = []
    first_frame, second_frame, final_frame = object(), object(), object()
    transfer, latent = object(), object()
    inputs = [object() for _ in range(6)]
    monkeypatch.setattr(
        sut,
        "_get_partition_heat_transfers",
        lambda *args: events.append(("transfer", args)) or (transfer, second_frame),
    )
    monkeypatch.setattr(
        sut,
        "_get_balanced_latent_cooling_loads",
        lambda *args: events.append(("latent", args)) or (latent, final_frame),
    )

    result = sut._prepare_balanced_load_state(first_frame, *inputs)

    assert result == (transfer, latent, final_frame)
    assert events == [
        ("transfer", (first_frame, *inputs[:4])),
        ("latent", (second_frame, inputs[4], inputs[5])),
    ]

def test_initialize_carryover_hourly_state_preserves_shapes_and_season_order(monkeypatch):
    events = []
    arrays = []
    seasons = tuple(object() for _ in range(3))

    def zeros(shape):
        value = object()
        arrays.append(value)
        events.append(("zeros", shape))
        return value

    monkeypatch.setattr(sut.np, "zeros", zeros)
    monkeypatch.setattr(
        sut.dc,
        "get_season_array_d_t",
        lambda region: events.append(("season", region)) or seasons,
    )

    result = sut._initialize_carryover_hourly_state(6)

    assert result == (*arrays, *seasons)
    assert events == [
        ("zeros", (5, 24 * 365)),
        ("zeros", (5, 24 * 365)),
        ("zeros", 24 * 365),
        ("zeros", (5, 24 * 365)),
        ("zeros", 24 * 365),
        ("zeros", (5, 24 * 365)),
        ("season", 6),
    ]

@pytest.mark.parametrize("enabled", (False, True))
def test_prepare_no_carryover_balanced_loads_preserves_formula_and_adjustment_order(
        monkeypatch, enabled):
    events = []
    sensible_c, heating = object(), object()
    adjusted_h, adjusted_c = object(), object()
    flag = sut.床下空調ロジック.変更する if enabled else object()
    house = SimpleNamespace(region=6)
    new_ufac = SimpleNamespace(new_ufac_flg=flag)
    load = SimpleNamespace(L_CS_d_t_i=object(), L_H_d_t_i=object())
    inputs = [object() for _ in range(5)]
    monkeypatch.setattr(sut.dc, "get_L_star_CS_d_t_i", lambda *a: events.append(("cool", a)) or sensible_c)
    monkeypatch.setattr(sut.dc, "get_L_star_H_d_t_i", lambda *a: events.append(("heat", a)) or heating)
    monkeypatch.setattr(
        sut, "_adjust_new_underfloor_balanced_loads",
        lambda *a: events.append(("adjust", a)) or (adjusted_h, adjusted_c))

    result = sut._prepare_no_carryover_balanced_loads(
        house, new_ufac, inputs[0], load, *inputs[1:])

    assert result == ((adjusted_h, adjusted_c) if enabled else (heating, sensible_c))
    assert [e[0] for e in events] == (["cool", "heat", "adjust"] if enabled else ["cool", "heat"])
    assert events[0][1] == (load.L_CS_d_t_i, inputs[4], 6)
    assert events[1][1] == (load.L_H_d_t_i, inputs[4], 6)

@pytest.mark.parametrize("standard", (True, False))
def test_prepare_no_carryover_capacity_state_preserves_model_branch(monkeypatch, standard):
    events = []
    model = (sut.計算モデル.ダクト式セントラル空調機 if standard
             else sut.計算モデル.電中研モデル)
    setting = SimpleNamespace(type=model)
    inputs = [object() for _ in range(8)]
    standard_loads = sut._BalancedCoolingLoadsResult(
        *(object() for _ in range(6)))
    standard_caps = sut._StandardCapacityLimitsResult(
        *(object() for _ in range(5)))
    heat_caps = sut._RacHeatingCapacityResult(
        *(object() for _ in range(3)))
    cool_caps = sut._RacCoolingCapacityResult(
        *(object() for _ in range(10)))

    class Climate:
        def get_C_df_H_d_t(self):
            events.append(("defrost",))
            return "defrost"

    monkeypatch.setattr(sut, "_get_balanced_cooling_loads", lambda *a: events.append(("loads", a)) or standard_loads)
    monkeypatch.setattr(sut, "_get_standard_heat_source_capacity_limits", lambda *a: events.append(("standard", a)) or standard_caps)
    monkeypatch.setattr(sut, "_get_rac_heating_capacity", lambda *a, **k: events.append(("rac_heat", a, k)) or heat_caps)
    monkeypatch.setattr(sut, "_get_rac_cooling_capacity", lambda *a, **k: events.append(("rac_cool", a, k)) or cool_caps)
    monkeypatch.setattr(sut._logger, "debug", lambda message: events.append(("log", message)))

    result = sut._prepare_no_carryover_capacity_state(
        setting, *inputs[:4], Climate(), *inputs[4:])

    assert result[:4] == ((standard_caps[0], standard_caps[1], standard_caps[2], standard_caps[4])
                      if standard else (cool_caps[2], cool_caps[9], cool_caps[8], heat_caps[2]))
    assert [e[0] for e in events] == (["loads", "standard"] if standard else ["defrost", "log", "rac_heat", "rac_cool"])

def test_prepare_balanced_heat_source_inlet_state_preserves_formula_20_19_order(monkeypatch):
    events = []
    humidity, temperature = object(), object()
    star_humidity, star_temperature = object(), object()
    monkeypatch.setattr(sut.dc, "get_X_star_hs_in_d_t", lambda x: events.append(("humidity", x)) or humidity)
    monkeypatch.setattr(sut.dc, "get_Theta_star_hs_in_d_t", lambda x: events.append(("temperature", x)) or temperature)

    result = sut._prepare_balanced_heat_source_inlet_state(
        star_humidity, star_temperature)

    assert result == (humidity, temperature)
    assert events == [("humidity", star_humidity), ("temperature", star_temperature)]

@pytest.mark.parametrize("mode", ("none", "new", "legacy"))
def test_prepare_no_carryover_outlet_requirements_preserves_first_pass(monkeypatch, mode):
    events = []
    x_min, x_req, theta_req, adjusted = [object() for _ in range(4)]
    new_ufac = SimpleNamespace(
        new_ufac_flg=(sut.床下空調ロジック.変更する if mode == "new" else object()))
    skin = SimpleNamespace(
        underfloor_air_conditioning_air_supply=(mode == "legacy"), r_A_ufac=0.5)
    house = SimpleNamespace(region=6)
    context = [object() for _ in range(15)]
    monkeypatch.setattr(
        sut, "_get_heat_source_outlet_requirements",
        lambda *a: events.append(("requirements", a))
        or sut._HeatSourceOutletRequirementsResult(x_min, x_req, theta_req))
    monkeypatch.setattr(
        sut, "_get_new_underfloor_requested_temperatures",
        lambda *a: events.append(("new", a)) or adjusted)
    monkeypatch.setattr(
        sut, "_adjust_legacy_underfloor_requested_temperatures",
        lambda *a: events.append(("legacy", a)) or np.zeros((5, 8760)))

    result = sut._prepare_no_carryover_outlet_requirements(sut._NoCarryoverOutletRequirementInputs(
        context[0], house, skin, context[1], new_ufac, *context[2:]))

    assert result[:2] == (x_min, x_req)
    assert [e[0] for e in events] == ["requirements"] + ([] if mode == "none" else [mode])
    assert result[2] is (theta_req if mode == "none" else adjusted) if mode != "legacy" else result[2].shape == (5, 8760)

@pytest.mark.parametrize("mode", ("none", "new", "legacy"))
def test_prepare_no_carryover_supply_state_preserves_second_pass(monkeypatch, mode):
    events = []
    x_out = object()
    temperatures = sut._HeatSourceOutletTemperaturesResult(
        *(object() for _ in range(3)))
    airflows = sut._CappedSupplyAirflowsResult(
        *(object() for _ in range(2)))
    base_supply = tuple(object() for _ in range(5))
    adjusted_supply = tuple(object() for _ in range(5))
    theta_nr = object()
    house = SimpleNamespace(region=6)
    skin = SimpleNamespace(underfloor_air_conditioning_air_supply=(mode == "legacy"))
    new_ufac = SimpleNamespace(
        new_ufac_flg=(sut.床下空調ロジック.変更する if mode == "new" else object()))
    context = [object() for _ in range(22)]
    monkeypatch.setattr(sut, "_get_heat_source_outlet_humidity", lambda *a: events.append(("humidity", a)) or x_out)
    monkeypatch.setattr(sut.np, "zeros", lambda shape: events.append(("zeros", shape)) or theta_nr)
    monkeypatch.setattr(sut, "_get_heat_source_outlet_temperatures", lambda *a: events.append(("temperatures", a)) or temperatures)
    monkeypatch.setattr(sut, "_get_capped_supply_airflows", lambda *a, **k: events.append(("airflows", a, k)) or airflows)
    monkeypatch.setattr(sut, "_get_supply_air_temperatures", lambda *a: events.append(("supply", a)) or base_supply)
    monkeypatch.setattr(sut, "_get_new_underfloor_supply_temperatures", lambda *a: events.append(("new", a)) or adjusted_supply)
    monkeypatch.setattr(sut, "_adjust_legacy_underfloor_supply_temperatures", lambda *a: events.append(("legacy", a)) or adjusted_supply)
    monkeypatch.setattr(sut._logger, "NDdebug", lambda *a: events.append(("debug", a)))

    result = sut._prepare_no_carryover_supply_state(sut._NoCarryoverSupplyInputs(
        context[0], context[1], house, skin, context[2], new_ufac,
        context[3], *context[4:22]))

    expected = ["humidity", "zeros", "temperatures", "airflows", "supply"]
    expected += ["debug"] * 5
    if mode != "none":
        expected.append(mode)
    expected += ["debug"] * 5
    assert [e[0] for e in events] == expected
    assert result[:6] == (x_out, *temperatures, *airflows)
    assert result[6] == (base_supply if mode == "none" else adjusted_supply)


@pytest.mark.parametrize("standard", (True, False))
def test_prepare_carryover_capacity_state_preserves_model_branch(monkeypatch, standard):
    events = []
    model = (sut.計算モデル.ダクト式セントラル空調機 if standard
             else sut.計算モデル.電中研モデル)
    setting = SimpleNamespace(type=model)
    inputs = [object() for _ in range(8)]
    standard_loads = sut._BalancedCoolingLoadsResult(
        *(object() for _ in range(6)))
    standard_caps = sut._StandardCapacityLimitsResult(
        *(object() for _ in range(5)))
    heat_caps = sut._RacHeatingCapacityResult(
        *(object() for _ in range(3)))
    cool_caps = sut._RacCoolingCapacityResult(
        *(object() for _ in range(10)))
    monkeypatch.setattr(
        sut, "_get_balanced_cooling_loads",
        lambda *a: events.append(("loads", a)) or standard_loads)
    monkeypatch.setattr(
        sut, "_get_standard_heat_source_capacity_limits",
        lambda *a: events.append(("standard", a)) or standard_caps)
    monkeypatch.setattr(
        sut.dc, "get_C_df_H_d_t",
        lambda *a: events.append(("defrost", a)) or "defrost")
    monkeypatch.setattr(
        sut, "_get_rac_heating_capacity",
        lambda *a, **k: events.append(("rac_heat", a, k)) or heat_caps)
    monkeypatch.setattr(
        sut, "_get_rac_cooling_capacity",
        lambda *a, **k: events.append(("rac_cool", a, k)) or cool_caps)

    result = sut._prepare_carryover_capacity_state(setting, *inputs)

    expected = (["loads", "standard"] if standard
                else ["defrost", "rac_heat", "rac_cool"])
    assert [event[0] for event in events] == expected
    assert result[:4] == (
        (standard_caps[0], standard_caps[1], standard_caps[2], standard_caps[4])
        if standard else (cool_caps[2], cool_caps[9], cool_caps[8], heat_caps[2]))


@pytest.mark.parametrize(
    ("t", "is_first", "heating", "cooling", "expected"),
    ((0, True, True, False, 10.0), (1, False, False, False, 20.0),
     (1, False, True, False, 31.0)),
)
def test_prepare_carryover_heat_source_inlet_state_preserves_formula_20_19(
        monkeypatch, t, is_first, heating, cooling, expected):
    events = []
    inlet_humidity = object()
    star_humidity = object()
    star_temperature = object()
    h = np.array([False, heating])
    c = np.array([False, cooling])
    actual_non_room = np.array([31.0, 32.0])
    inlet_temperature = np.zeros(2)
    monkeypatch.setattr(
        sut.dc, "get_X_star_hs_in_d_t",
        lambda value: events.append(("humidity", value)) or inlet_humidity)
    monkeypatch.setattr(
        sut.dc, "get_Theta_star_hs_in_d_t",
        lambda value: events.append(("temperature", value))
        or np.array([10.0, 20.0]))

    result = sut._prepare_carryover_heat_source_inlet_state(
        t, is_first, h, c, star_humidity, star_temperature,
        actual_non_room, inlet_temperature)

    assert result == (inlet_humidity, inlet_temperature)
    assert inlet_temperature[t] == expected
    assert events == [
        ("humidity", star_humidity), ("temperature", star_temperature)]


@pytest.mark.parametrize("enabled", (False, True))
def test_prepare_carryover_outlet_requirements_preserves_first_pass(
        monkeypatch, enabled):
    events = []
    humidity_min, humidity_req, temperature_req = (
        object(), object(), object())
    adjusted = object()
    house = SimpleNamespace(region=6)
    skin = SimpleNamespace(
        underfloor_air_conditioning_air_supply=enabled,
        YUCACO_r_A_ufvnt=0.25)
    inputs = [object() for _ in range(13)]
    monkeypatch.setattr(
        sut, "_get_heat_source_outlet_requirements",
        lambda *a: events.append(("requirements", a))
        or sut._HeatSourceOutletRequirementsResult(
            humidity_min, humidity_req, temperature_req))
    monkeypatch.setattr(
        sut, "_adjust_legacy_underfloor_requested_temperatures",
        lambda *a: events.append(("adjust", a)) or adjusted)

    result = sut._prepare_carryover_outlet_requirements(sut._CarryoverOutletRequirementInputs(
        inputs[0], house, skin, inputs[1], *inputs[2:]))

    assert result == (
        humidity_min, humidity_req, adjusted if enabled else temperature_req)
    assert [event[0] for event in events] == (
        ["requirements", "adjust"] if enabled else ["requirements"])
    if enabled:
        assert events[1][1][4] == skin.YUCACO_r_A_ufvnt


@pytest.mark.parametrize("enabled", (False, True))
def test_prepare_carryover_supply_state_preserves_second_pass(
        monkeypatch, enabled):
    events = []
    outlet_humidity = object()
    outlet_temperatures = sut._HeatSourceOutletTemperaturesResult(
        *(object() for _ in range(3)))
    airflows = sut._CappedSupplyAirflowsResult(
        *(object() for _ in range(2)))
    supply_temperature = object()
    adjusted = object()
    house = SimpleNamespace(region=6)
    skin = SimpleNamespace(underfloor_air_conditioning_air_supply=enabled)
    inputs = [object() for _ in range(22)]
    monkeypatch.setattr(
        sut, "_get_heat_source_outlet_humidity",
        lambda *a: events.append(("humidity", a)) or outlet_humidity)
    monkeypatch.setattr(
        sut, "_get_heat_source_outlet_temperatures",
        lambda *a: events.append(("temperatures", a)) or outlet_temperatures)
    monkeypatch.setattr(
        sut, "_get_capped_supply_airflows",
        lambda *a, **k: events.append(("airflows", a, k)) or airflows)
    monkeypatch.setattr(
        sut, "_get_supply_air_temperatures",
        lambda *a: events.append(("supply", a)) or supply_temperature)
    monkeypatch.setattr(
        sut, "_adjust_carryover_underfloor_supply_temperatures",
        lambda *a: events.append(("adjust", a)) or adjusted)

    result = sut._prepare_carryover_supply_state(sut._CarryoverSupplyInputs(
        inputs[0], inputs[1], house, skin, inputs[2], *inputs[3:]))

    assert result == (
        outlet_humidity, *outlet_temperatures, *airflows,
        adjusted if enabled else supply_temperature)
    assert [event[0] for event in events] == (
        ["humidity", "temperatures", "airflows", "supply", "adjust"]
        if enabled else ["humidity", "temperatures", "airflows", "supply"])
    assert events[2][2] == {"print_exec": False}


def test_update_carryover_actual_temperature_state_preserves_formula_order(
        monkeypatch):
    events = []
    room_state = np.zeros((5, 2))
    non_room_state = np.zeros(2)
    room_hour = np.full((5, 1), 7.0)
    inputs = [object() for _ in range(16)]
    monkeypatch.setattr(
        sut, "_get_actual_room_temperatures_at_hour",
        lambda *a: events.append(("room", a)) or room_hour)
    monkeypatch.setattr(
        sut, "_get_actual_non_room_temperature_at_hour",
        lambda *a: events.append(("non_room", a)) or 8.0)

    result = sut._update_carryover_actual_temperature_state(sut._CarryoverActualTemperatureInputs(
        1, False, *inputs[:12], room_state,
        *inputs[12:], non_room_state))

    assert result[0] is room_state
    assert result[1] is non_room_state
    assert np.all(room_state[:, 1:2] == room_hour)
    assert non_room_state[1] == 8.0
    assert [event[0] for event in events] == ["room", "non_room"]
    assert events[1][1][7] is room_state


@pytest.mark.parametrize("enabled", (False, True))
def test_prepare_no_carryover_actual_temperature_state_preserves_formula_order(
        monkeypatch, enabled):
    events = []
    room = object()
    non_room = object()
    flag = sut.床下空調ロジック.変更する if enabled else object()
    new_ufac = SimpleNamespace(new_ufac_flg=flag)
    inputs = [object() for _ in range(15)]
    theta_uf = object()
    non_room_ratio = object()
    monkeypatch.setattr(
        sut, "_get_actual_room_temperatures_without_carryover",
        lambda *a: events.append(("room", a)) or room)
    monkeypatch.setattr(
        sut, "_get_actual_non_room_temperatures_without_carryover",
        lambda *a: events.append(("non_room", a)) or non_room)

    result = sut._prepare_no_carryover_actual_temperature_state(sut._NoCarryoverActualTemperatureInputs(
        inputs[0], inputs[1], new_ufac, *inputs[2:11], theta_uf,
        *inputs[11:], non_room_ratio))

    assert result == (room, non_room)
    assert [event[0] for event in events] == ["room", "non_room"]
    assert events[0][1][-1] is (theta_uf if enabled else None)
    assert events[1][1][-2] is (theta_uf if enabled else None)
    assert events[1][1][-1] is (non_room_ratio if enabled else None)


def test_log_actual_temperature_state_preserves_diagnostic_order(monkeypatch):
    events = []
    room = [object() for _ in range(5)]
    non_room = object()
    monkeypatch.setattr(
        sut._logger, "NDdebug",
        lambda name, value: events.append((name, value)))

    sut._log_actual_temperature_state(room, non_room)

    assert events == [
        ("Theta_HBR_d_t_1", room[0]),
        ("Theta_HBR_d_t_2", room[1]),
        ("Theta_HBR_d_t_3", room[2]),
        ("Theta_HBR_d_t_4", room[3]),
        ("Theta_HBR_d_t_5", room[4]),
        ("Theta_NR_d_t", non_room),
    ]


@pytest.mark.parametrize(("mode", "rated", "suffix"), (
    ("disabled", (object(), None), None),
    ("heating", (object(), None), "_H_carryover_output.csv"),
    ("cooling", (None, object()), "_C_carryover_output.csv"),
))
def test_export_carryover_diagnostics_preserves_columns_and_filename(
        monkeypatch, mode, rated, suffix):
    events = []

    class Frame:
        def assign(self, **values):
            events.append(("assign", tuple(values), values))
            return self

        def to_csv(self, path, **kwargs):
            events.append(("csv", path, kwargs))

    enabled = sut.過剰熱量繰越計算.行う
    carryover = SimpleNamespace(
        carry_over_heat=enabled if mode != "disabled" else object())
    monkeypatch.setattr(sut, "_get_q_hs_rtd_H", lambda *a: rated[0])
    monkeypatch.setattr(sut, "_get_q_hs_rtd_C", lambda *a: rated[1])
    monkeypatch.setattr(sut.jjj_consts, "version_info", lambda: "_version")
    values = [object() for _ in range(5)]

    sut._export_carryover_diagnostics(
        "case", object(), object(), carryover, Frame(), values)

    if mode == "disabled":
        assert events == []
    else:
        assert events[0][1] == tuple(
            f"carryovers_i_{i}" for i in range(1, 6))
        assert events[1] == (
            "csv", "case_version" + suffix, {"encoding": "cp932"})


def test_record_capacity_state_outputs_preserves_frame_generations_and_order():
    events = []

    class Frame:
        def __init__(self, name):
            self.name = name

        def assign(self, **values):
            events.append((self.name, "assign", tuple(values), values))
            return self

        def __setitem__(self, key, value):
            events.append((self.name, "setitem", key, value))

    output = Frame("output")
    output3 = Frame("output3")
    values = [object() for _ in range(17)]

    result = sut._record_capacity_state_outputs(sut._CapacityStateOutputInputs(output, output3, *values))

    assert result == (output, output3)
    assert [(event[0], event[1]) for event in events] == [
        ("output", "assign"),
        ("output3", "assign"),
        ("output", "setitem"),
        ("output", "assign"),
    ]
    assert events[0][2] == (
        "L_star_CL_d_t", "L_star_CS_d_t", "L_star_dash_CL_d_t",
        "L_star_dash_C_d_t", "C_df_H_d_t", "Q_r_max_H_d_t",
        "Q_r_max_C_d_t", "L_max_CL_d_t", "L_dash_CL_d_t",
        "L_dash_C_d_t")
    assert events[1][2] == ("q_r_max_H", "q_r_max_C", "SHF_L_min_c")
    assert events[1][3]["q_r_max_H"] is None
    assert events[3][2] == (
        "Q_hs_max_C_d_t", "Q_hs_max_CL_d_t",
        "Q_hs_max_CS_d_t", "Q_hs_max_H_d_t")


def test_record_common_outlet_and_supply_outputs_preserves_generation_order(
        monkeypatch):
    events = []
    original = object()
    outlet_frame = object()
    supply_frame = object()
    inputs = [object() for _ in range(14)]
    monkeypatch.setattr(
        sut, "_record_heat_source_outlet_outputs",
        lambda *a: events.append(("outlet", a)) or outlet_frame)
    monkeypatch.setattr(
        sut, "_record_supply_state_outputs",
        lambda *a: events.append(("supply", a)) or supply_frame)

    result = sut._record_common_outlet_and_supply_outputs(sut._CommonOutletSupplyOutputInputs(
        original, *inputs))

    assert result is supply_frame
    assert [event[0] for event in events] == ["outlet", "supply"]
    assert events[0][1][0] is original
    assert events[1][1][0] is outlet_frame
    assert events[0][1][1:] == tuple(inputs[:9])
    assert events[1][1][1:] == tuple(inputs[9:])


def test_prepare_heat_source_outlet_temperature_output_preserves_formula_14(
        monkeypatch):
    events = []
    temperature = object()
    setting = SimpleNamespace(VAV=object())
    house = SimpleNamespace(region=6)
    inputs = [object() for _ in range(7)]

    class Frame:
        def __setitem__(self, key, value):
            events.append(("setitem", key, value))

    frame = Frame()
    monkeypatch.setattr(
        sut.dc, "get_Theta_hs_out_d_t",
        lambda *a: events.append(("formula", a)) or temperature)

    result = sut._prepare_heat_source_outlet_temperature_output(
        frame, setting, house, *inputs)

    assert result == (temperature, frame)
    assert [event[0] for event in events] == ["formula", "setitem"]
    assert events[0][1][0] is setting.VAV
    assert events[0][1][5] == house.region
    assert events[1] == ("setitem", "Theta_hs_out_d_t", temperature)


def test_prepare_supply_humidity_output_preserves_formula_42_column_order(
        monkeypatch):
    events = []
    humidity = [object() for _ in range(5)]

    class Frame:
        def assign(self, **values):
            events.append(("assign", tuple(values), values))
            return self

    frame = Frame()
    inputs = [object() for _ in range(4)]
    monkeypatch.setattr(
        sut.dc, "get_X_supply_d_t_i",
        lambda *a: events.append(("formula", a)) or humidity)

    result = sut._prepare_supply_humidity_output(frame, *inputs)

    assert result == (humidity, frame)
    assert events[0] == ("formula", tuple(inputs))
    assert events[1][1] == tuple(f"X_supply_d_t_{i}" for i in range(1, 6))
    assert list(events[1][2].values()) == humidity


def test_prepare_heat_source_ventilation_airflow_output_preserves_formula_35(
        monkeypatch):
    events = []
    value = object()
    inputs = [object(), object()]

    class Frame:
        def __setitem__(self, key, item):
            events.append(("setitem", key, item))

    frame = Frame()
    monkeypatch.setattr(
        sut.dc, "get_V_hs_vent_d_t",
        lambda *args: events.append(("formula", args)) or value)

    assert sut._prepare_heat_source_ventilation_airflow_output(
        frame, *inputs) == (value, frame)
    assert events == [
        ("formula", tuple(inputs)),
        ("setitem", "V_hs_vent_d_t", value),
    ]


def test_prepare_heat_source_supply_airflow_output_preserves_formula_34(
        monkeypatch):
    events = []
    value = object()
    source = object()

    class Frame:
        def __setitem__(self, key, item):
            events.append(("setitem", key, item))

    frame = Frame()
    monkeypatch.setattr(
        sut.dc, "get_V_hs_supply_d_t",
        lambda arg: events.append(("formula", arg)) or value)

    assert sut._prepare_heat_source_supply_airflow_output(
        frame, source) == (value, frame)
    assert events == [
        ("formula", source),
        ("setitem", "V_hs_supply_d_t", value),
    ]


def test_prepare_heat_source_inlet_humidity_output_preserves_formula_13(
        monkeypatch):
    events = []
    value = object()
    source = object()

    class Frame:
        def __setitem__(self, key, item):
            events.append(("setitem", key, item))

    frame = Frame()
    monkeypatch.setattr(
        sut.dc, "get_X_hs_in_d_t",
        lambda arg: events.append(("formula", arg)) or value)

    assert sut._prepare_heat_source_inlet_humidity_output(
        frame, source) == (value, frame)
    assert events == [
        ("formula", source),
        ("setitem", "X_hs_in_d_t", value),
    ]


def test_prepare_heat_source_inlet_temperature_output_preserves_formula_12(
        monkeypatch):
    events = []
    value = object()
    source = object()

    class Frame:
        def __setitem__(self, key, item):
            events.append(("setitem", key, item))

    frame = Frame()
    monkeypatch.setattr(
        sut.dc, "get_Theta_hs_in_d_t",
        lambda arg: events.append(("formula", arg)) or value)

    assert sut._prepare_heat_source_inlet_temperature_output(
        frame, source) == (value, frame)
    assert events == [
        ("formula", source),
        ("setitem", "Theta_hs_in_d_t", value),
    ]


def test_prepare_actual_load_state_preserves_calculate_record_order(
        monkeypatch):
    events = []
    loads = sut._ActualLoadsResult(*(object() for _ in range(3)))
    original = object()
    recorded = object()
    inputs = [object() for _ in range(7)]
    monkeypatch.setattr(
        sut, "_get_actual_loads",
        lambda *args: events.append(("calculate", args)) or loads)
    monkeypatch.setattr(
        sut, "_record_actual_load_outputs",
        lambda *args: events.append(("record", args)) or recorded)

    result = sut._prepare_actual_load_state(original, *inputs)

    assert result == (*loads, recorded)
    assert events == [
        ("calculate", tuple(inputs)),
        ("record", (original, *loads)),
    ]


def test_prepare_unprocessed_load_state_preserves_calculate_record_order(
        monkeypatch):
    events = []
    loads = sut._UnprocessedLoadsResult(*(object() for _ in range(3)))
    original = object()
    recorded = object()
    inputs = [object() for _ in range(6)]
    monkeypatch.setattr(
        sut, "_get_unprocessed_loads",
        lambda *args: events.append(("calculate", args)) or loads)
    monkeypatch.setattr(
        sut, "_record_unprocessed_load_outputs",
        lambda *args: events.append(("record", args)) or recorded)

    result = sut._prepare_unprocessed_load_state(original, *inputs)

    assert result == (*loads, recorded)
    assert events == [
        ("calculate", tuple(inputs)),
        ("record", (original, *loads)),
    ]


def test_prepare_unprocessed_energy_state_preserves_calculate_record_order(
        monkeypatch):
    events = []
    energy = object()
    output_name = object()
    original = object()
    recorded = object()
    inputs = [object() for _ in range(5)]
    monkeypatch.setattr(
        sut, "_get_unprocessed_energy",
        lambda *args: events.append(("calculate", args))
        or (energy, output_name))
    monkeypatch.setattr(
        sut, "_record_unprocessed_energy_output",
        lambda *args: events.append(("record", args)) or recorded)

    result = sut._prepare_unprocessed_energy_state(original, *inputs)

    assert result == (energy, recorded)
    assert events == [
        ("calculate", tuple(inputs)),
        ("record", (original, output_name, energy)),
    ]


def test_export_and_build_calculation_result_preserves_order(monkeypatch):
    events = []
    inputs = [object() for _ in range(15)]
    monkeypatch.setattr(
        sut, "_export_underfloor_output",
        lambda *args: events.append(("underfloor", args)))
    monkeypatch.setattr(
        sut, "_export_standard_outputs",
        lambda *args: events.append(("standard", args)))

    result = sut._export_and_build_calculation_result(sut._CalculationExportInputs(*inputs))

    assert events == [
        ("underfloor", (inputs[0], inputs[1], inputs[3], inputs[4])),
        ("standard", (
            inputs[0], inputs[1], inputs[2],
            inputs[5], inputs[6], inputs[7])),
    ]
    assert result == tuple(inputs[8:])


def test_rated_heat_source_capacities_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(2))
    result = sut._RatedHeatSourceCapacitiesResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("Q_hs_rtd_H", "Q_hs_rtd_C",)


def test_underfloor_ground_response_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(4))
    result = sut._UnderfloorGroundResponseResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("Theta_in_d_t", "Phi_A_0", "Theta_g_avg", "sum_Theta_dash_g_surf_A_m",)


def test_supply_airflow_before_vav_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._SupplyAirflowBeforeVavResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("r_supply_des_i", "r_supply_des_d_t_i", "V_dash_supply_d_t_i",)


def test_room_to_underfloor_transfer_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(4))
    result = sut._RoomToUnderfloorTransferResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("Q_hat_hs_d_t", "U_s_input", "A_s_ufac_i", "r_A_s_ufac",)


def test_heat_source_outlet_requirements_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._HeatSourceOutletRequirementsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("X_hs_out_min_C_d_t", "X_req_d_t_i", "Theta_req_d_t_i",)


def test_heat_source_outlet_temperatures_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._HeatSourceOutletTemperaturesResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("Theta_hs_out_min_C_d_t", "Theta_hs_out_max_H_d_t", "Theta_hs_out_d_t",)


def test_capped_supply_airflows_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(2))
    result = sut._CappedSupplyAirflowsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("V_supply_d_t_i_before", "V_supply_d_t_i",)


def test_balanced_cooling_loads_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(6))
    result = sut._BalancedCoolingLoadsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("L_star_CL_d_t", "L_star_CS_d_t", "L_star_CL_max_d_t", "L_star_dash_CL_d_t", "L_star_dash_C_d_t", "SHF_dash_d_t",)


def test_standard_capacity_limits_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(5))
    result = sut._StandardCapacityLimitsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("Q_hs_max_C_d_t", "Q_hs_max_CL_d_t", "Q_hs_max_CS_d_t", "C_df_H_d_t", "Q_hs_max_H_d_t",)


def test_rac_heating_capacity_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._RacHeatingCapacityResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == ("q_r_max_H", "Q_r_max_H_d_t", "Q_max_H_d_t",)


def test_rac_cooling_capacity_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(10))
    result = sut._RacCoolingCapacityResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "q_r_max_C",
        "Q_r_max_C_d_t",
        "Q_max_C_d_t",
        "SHF_L_min_c",
        "L_max_CL_d_t",
        "L_dash_CL_d_t",
        "L_dash_C_d_t",
        "SHF_dash_d_t",
        "Q_max_CS_d_t",
        "Q_max_CL_d_t",
    )


def test_actual_loads_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._ActualLoadsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "L_dash_CL_d_t_i",
        "L_dash_CS_d_t_i",
        "L_dash_H_d_t_i",
    )


def test_unprocessed_loads_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(3))
    result = sut._UnprocessedLoadsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "Q_UT_CL_d_t_i",
        "Q_UT_CS_d_t_i",
        "Q_UT_H_d_t_i",
    )


def test_climate_conditions_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(5))
    result = sut._ClimateConditionsResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "climate",
        "Theta_ex_d_t",
        "X_ex_d_t",
        "J_d_t",
        "h_ex_d_t",
    )


def test_dwelling_areas_and_water_heat_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(4))
    result = sut._DwellingAreasAndWaterHeatResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "A_HCZ_i",
        "A_HCZ_R_i",
        "A_NR",
        "L_wtr",
    )


def test_balanced_room_and_duct_state_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(5))
    result = sut._BalancedRoomAndDuctStateResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "X_star_HBR_d_t",
        "Theta_star_HBR_d_t",
        "Theta_attic_d_t",
        "Theta_sur_d_t_i",
        "df_output",
    )


def test_pre_vav_airflow_state_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(6))
    result = sut._PreVavAirflowStateResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "A_s_ufac_i",
        "Theta_uf_d_t",
        "r_supply_des_i",
        "r_supply_des_d_t_i",
        "V_dash_supply_d_t_i",
        "df_output",
    )


def test_carryover_hourly_state_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(9))
    result = sut._CarryoverHourlyStateResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "L_star_CS_d_t_i",
        "L_star_H_d_t_i",
        "Theta_star_hs_in_d_t",
        "Theta_HBR_d_t_i",
        "Theta_NR_d_t",
        "carryovers",
        "H",
        "C",
        "M",
    )


def test_capacity_state_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(18))
    result = sut._CapacityStateResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "Q_hs_max_C_d_t",
        "Q_hs_max_CL_d_t",
        "Q_hs_max_CS_d_t",
        "Q_hs_max_H_d_t",
        "L_star_CL_d_t",
        "L_star_CS_d_t",
        "L_star_dash_CL_d_t",
        "L_star_dash_C_d_t",
        "C_df_H_d_t",
        "Q_r_max_H_d_t",
        "Q_r_max_C_d_t",
        "L_max_CL_d_t",
        "L_dash_CL_d_t",
        "L_dash_C_d_t",
        "q_r_max_H",
        "q_r_max_C",
        "SHF_L_min_c",
        "SHF_dash_d_t",
    )


def test_supply_state_result_preserves_tuple_contract():
    values = tuple(object() for _ in range(7))
    result = sut._SupplyStateResult(*values)

    assert isinstance(result, tuple)
    assert tuple(result) == values
    assert result._fields == (
        "X_hs_out_d_t",
        "Theta_hs_out_min_C_d_t",
        "Theta_hs_out_max_H_d_t",
        "Theta_hs_out_d_t",
        "V_supply_d_t_i_before",
        "V_supply_d_t_i",
        "Theta_supply_d_t_i",
    )


def test_initial_heat_source_output_inputs_preserve_field_order():
    values = tuple(object() for _ in range(15))
    inputs = sut._InitialHeatSourceOutputInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "df_output",
        "house",
        "skin",
        "V_vent_l_d_t",
        "V_vent_g_i",
        "J_d_t",
        "q_gen_d_t",
        "n_p_d_t",
        "q_p_H",
        "q_p_CS",
        "q_p_CL",
        "X_ex_d_t",
        "w_gen_d_t",
        "Theta_ex_d_t",
        "L_wtr",
    )


def test_pre_vav_airflow_inputs_preserve_field_order():
    values = tuple(object() for _ in range(23))
    inputs = sut._PreVavAirflowInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "df_output",
        "df_output2",
        "ac_setting",
        "house",
        "skin",
        "load",
        "new_ufac",
        "climate",
        "A_HCZ_i",
        "V_hs_dsgn_H",
        "V_hs_dsgn_C",
        "V_hs_min",
        "Q_hs_rtd_H",
        "Q_hs_rtd_C",
        "Q_hat_hs_d_t",
        "Q_hat_hs_CS_d_t",
        "V_vent_g_i",
        "Theta_in_d_t",
        "Theta_ex_d_t",
        "Phi_A_0",
        "Theta_g_avg",
        "sum_Theta_dash_g_surf_A_m",
        "should_adjust",
    )


def test_balanced_non_room_temperature_inputs_preserve_field_order():
    values = tuple(object() for _ in range(14))
    inputs = sut._BalancedNonRoomTemperatureInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "df_output",
        "new_ufac",
        "house",
        "skin",
        "climate",
        "load",
        "A_NR",
        "A_prt_i",
        "U_prt",
        "V_vent_l_NR_d_t",
        "V_dash_supply_d_t_i",
        "Theta_star_HBR_d_t",
        "Theta_in_d_t",
        "Theta_uf_d_t",
    )


def test_no_carryover_outlet_requirement_inputs_preserve_field_order():
    values = tuple(object() for _ in range(18))
    inputs = sut._NoCarryoverOutletRequirementInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "ac_setting",
        "house",
        "skin",
        "load",
        "new_ufac",
        "new_ufac_df",
        "X_star_hs_in_d_t",
        "Q_hs_max_CL_d_t",
        "V_dash_supply_d_t_i",
        "X_star_HBR_d_t",
        "L_star_CL_d_t_i",
        "Theta_sur_d_t_i",
        "Theta_star_HBR_d_t",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "l_duct_i",
        "Theta_ex_d_t",
        "Theta_in_d_t",
    )


def test_no_carryover_supply_inputs_preserve_field_order():
    values = tuple(object() for _ in range(25))
    inputs = sut._NoCarryoverSupplyInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "v_supply_cap_dto",
        "ac_setting",
        "house",
        "skin",
        "load",
        "new_ufac",
        "new_ufac_df",
        "X_NR_d_t",
        "X_req_d_t_i",
        "Theta_req_d_t_i",
        "V_dash_supply_d_t_i",
        "X_hs_out_min_C_d_t",
        "L_star_CL_d_t_i",
        "Theta_star_hs_in_d_t",
        "Q_hs_max_CS_d_t",
        "Q_hs_max_H_d_t",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_sur_d_t_i",
        "l_duct_i",
        "Theta_star_HBR_d_t",
        "V_vent_g_i",
        "V_hs_dsgn_H",
        "V_hs_dsgn_C",
        "Theta_ex_d_t",
    )


def test_no_carryover_actual_temperature_inputs_preserve_field_order():
    values = tuple(object() for _ in range(18))
    inputs = sut._NoCarryoverActualTemperatureInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "house",
        "skin",
        "new_ufac",
        "climate",
        "Theta_star_HBR_d_t",
        "V_supply_d_t_i",
        "Theta_supply_d_t_i",
        "U_prt",
        "A_prt_i",
        "A_HCZ_i",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_uf_d_t",
        "Theta_star_NR_d_t",
        "A_NR",
        "V_vent_l_NR_d_t",
        "V_dash_supply_d_t_i",
        "r_A_NR_uf_1F_excl_bath",
    )


def test_carryover_outlet_requirement_inputs_preserve_field_order():
    values = tuple(object() for _ in range(15))
    inputs = sut._CarryoverOutletRequirementInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "ac_setting",
        "house",
        "skin",
        "load",
        "X_star_hs_in_d_t",
        "Q_hs_max_CL_d_t",
        "V_dash_supply_d_t_i",
        "X_star_HBR_d_t",
        "L_star_CL_d_t_i",
        "Theta_sur_d_t_i",
        "Theta_star_HBR_d_t",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "l_duct_i",
        "Theta_ex_d_t",
    )


def test_carryover_supply_inputs_preserve_field_order():
    values = tuple(object() for _ in range(24))
    inputs = sut._CarryoverSupplyInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "v_supply_cap_dto",
        "ac_setting",
        "house",
        "skin",
        "load",
        "X_NR_d_t",
        "X_req_d_t_i",
        "V_dash_supply_d_t_i",
        "X_hs_out_min_C_d_t",
        "L_star_CL_d_t_i",
        "Theta_star_hs_in_d_t",
        "Q_hs_max_CS_d_t",
        "Q_hs_max_H_d_t",
        "Theta_req_d_t_i",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_NR_d_t",
        "Theta_sur_d_t_i",
        "l_duct_i",
        "Theta_star_HBR_d_t",
        "V_vent_g_i",
        "V_hs_dsgn_H",
        "V_hs_dsgn_C",
        "Theta_ex_d_t",
    )


def test_carryover_actual_temperature_inputs_preserve_field_order():
    values = tuple(object() for _ in range(20))
    inputs = sut._CarryoverActualTemperatureInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "t",
        "isFirst",
        "H",
        "C",
        "M",
        "Theta_star_HBR_d_t",
        "V_supply_d_t_i",
        "Theta_supply_d_t_i",
        "U_prt",
        "A_prt_i",
        "Q",
        "A_HCZ_i",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_HBR_d_t_i",
        "Theta_star_NR_d_t",
        "A_NR",
        "V_vent_l_NR_d_t",
        "V_dash_supply_d_t_i",
        "Theta_NR_d_t",
    )


def test_common_outlet_supply_output_inputs_preserve_field_order():
    values = tuple(object() for _ in range(15))
    inputs = sut._CommonOutletSupplyOutputInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "df_output",
        "X_star_hs_in_d_t",
        "Theta_star_hs_in_d_t",
        "X_hs_out_min_C_d_t",
        "X_req_d_t_i",
        "Theta_req_d_t_i",
        "X_hs_out_d_t",
        "Theta_hs_out_min_C_d_t",
        "Theta_hs_out_max_H_d_t",
        "Theta_hs_out_d_t",
        "V_supply_d_t_i_before",
        "V_supply_d_t_i",
        "Theta_supply_d_t_i",
        "Theta_HBR_d_t_i",
        "Theta_NR_d_t",
    )


def test_capacity_state_output_inputs_preserve_field_order():
    values = tuple(object() for _ in range(19))
    inputs = sut._CapacityStateOutputInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "df_output",
        "df_output3",
        "L_star_CL_d_t",
        "L_star_CS_d_t",
        "L_star_dash_CL_d_t",
        "L_star_dash_C_d_t",
        "C_df_H_d_t",
        "Q_r_max_H_d_t",
        "Q_r_max_C_d_t",
        "L_max_CL_d_t",
        "L_dash_CL_d_t",
        "L_dash_C_d_t",
        "q_r_max_C",
        "SHF_L_min_c",
        "SHF_dash_d_t",
        "Q_hs_max_C_d_t",
        "Q_hs_max_CL_d_t",
        "Q_hs_max_CS_d_t",
        "Q_hs_max_H_d_t",
    )


def test_calculation_export_inputs_preserve_field_order():
    values = tuple(object() for _ in range(15))
    inputs = sut._CalculationExportInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "case_name",
        "ac_setting",
        "house",
        "new_ufac",
        "new_ufac_df",
        "df_output3",
        "df_output2",
        "df_output",
        "E_UT_d_t",
        "Theta_hs_out_d_t",
        "Theta_hs_in_d_t",
        "X_hs_out_d_t",
        "X_hs_in_d_t",
        "V_hs_supply_d_t",
        "V_hs_vent_d_t",
    )


def test_capped_supply_airflow_inputs_preserve_field_order():
    values = tuple(object() for _ in range(14))
    inputs = sut._CappedSupplyAirflowInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "v_supply_cap_dto",
        "ac_setting",
        "house",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_sur_d_t_i",
        "l_duct_i",
        "Theta_star_HBR_d_t",
        "V_vent_g_i",
        "V_dash_supply_d_t_i",
        "Theta_hs_out_d_t",
        "V_hs_dsgn_H",
        "V_hs_dsgn_C",
        "print_exec",
    )


def test_actual_room_temperature_hour_inputs_preserve_field_order():
    values = tuple(object() for _ in range(14))
    inputs = sut._ActualRoomTemperatureHourInputs(*values)

    assert tuple(inputs) == values
    assert inputs._fields == (
        "t",
        "H",
        "C",
        "M",
        "Theta_star_HBR_d_t",
        "V_supply_d_t_i",
        "Theta_supply_d_t_i",
        "U_prt",
        "A_prt_i",
        "Q",
        "A_HCZ_i",
        "L_star_H_d_t_i",
        "L_star_CS_d_t_i",
        "Theta_HBR_d_t_i",
    )
