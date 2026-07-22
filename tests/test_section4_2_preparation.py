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

    result = sut._get_capped_supply_airflows(
        cap,
        setting,
        house,
        *inputs,
        print_exec=print_exec,
    )

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