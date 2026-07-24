import numpy as np

from jjjexperiment.inputs.options import 計算モデル
import jjjexperiment.section4_2_a_jjj as sut


def _record(monkeypatch, owner, name, events, result):
    def replacement(*args, **kwargs):
        events.append((name, args, kwargs))
        return result

    monkeypatch.setattr(owner, name, replacement)


def _heating_type1_and3_args(model):
    values = [np.array([float(index)]) for index in range(1, 8)]
    return (
        model,
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        8000.0,
        1000.0,
        4000.0,
        1200.0,
        500.0,
        100.0,
        7000.0,
        200.0,
        900.0,
        2100.0,
        "equipment-spec",
    )


def test_type1_heating_preserves_formula_call_order_and_fan_sum(monkeypatch):
    events = []
    e_th_H_d_t = np.array([4.0])
    e_r_H_d_t = np.array([8.0])
    e_hs_H_d_t = np.array([9.0])
    E_E_comp_H_d_t = np.array([10.0])
    args = _heating_type1_and3_args(計算モデル.ダクト式セントラル空調機)

    _record(monkeypatch, sut.dc_a, "calc_e_th_mid_H", events, 2.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_rtd_H", events, 3.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_H_d_t", events, e_th_H_d_t)
    _record(monkeypatch, sut.dc_a, "get_e_r_rtd_H", events, 5.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_min_H", events, 6.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_mid_H", events, 7.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_H_d_t", events, e_r_H_d_t)
    _record(monkeypatch, sut.dc_a, "get_e_hs_H_d_t", events, e_hs_H_d_t)
    _record(monkeypatch, sut.dc_a, "get_E_E_comp_H_d_t", events, E_E_comp_H_d_t)

    actual = sut.calc_E_E_H_d_t_type1_and_type3(*args)

    assert [event[0] for event in events] == [
        "calc_e_th_mid_H",
        "calc_e_th_rtd_H",
        "calc_e_th_H_d_t",
        "get_e_r_rtd_H",
        "get_e_r_min_H",
        "get_e_r_mid_H",
        "get_e_r_H_d_t",
        "get_e_hs_H_d_t",
        "get_E_E_comp_H_d_t",
    ]
    assert events[-2][1] == (e_th_H_d_t, e_r_H_d_t)
    assert events[-1][1] == (args[2],)
    assert events[-1][2] == {"e_hs_H_d_t": e_hs_H_d_t}
    np.testing.assert_array_equal(actual, E_E_comp_H_d_t + args[1])


def test_type3_heating_preserves_latent_efficiency_branch(monkeypatch):
    events = []
    args = _heating_type1_and3_args(計算モデル.RAC活用型全館空調_潜熱評価モデル)

    _record(monkeypatch, sut.dc_a, "calc_e_th_mid_H", events, 2.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_rtd_H", events, 3.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_H_d_t", events, np.array([4.0]))
    _record(monkeypatch, sut.jjj_latent, "get_e_r_H_d_t", events, np.array([8.0]))
    _record(monkeypatch, sut.dc_a, "get_e_hs_H_d_t", events, np.array([9.0]))
    _record(monkeypatch, sut.dc_a, "get_E_E_comp_H_d_t", events, np.array([10.0]))

    sut.calc_E_E_H_d_t_type1_and_type3(*args)

    assert [event[0] for event in events] == [
        "calc_e_th_mid_H",
        "calc_e_th_rtd_H",
        "calc_e_th_H_d_t",
        "get_e_r_H_d_t",
        "get_e_hs_H_d_t",
        "get_E_E_comp_H_d_t",
    ]
    assert events[3][1] == (args[2],)


def test_type2_heating_preserves_unit_conversion_argument_order_and_sum(monkeypatch):
    events = []
    fan = np.array([1.0, 2.0])
    q_hs = np.array([1000.0, 2000.0])
    rac = np.array([3.0, 4.0])
    _record(monkeypatch, sut.pyhees.section4_3, "calc_E_E_H_d_t_2024", events, rac)

    actual = sut.calc_E_E_H_d_t_type2(
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        6,
        "climate.csv",
        fan,
        q_hs,
        3.2,
        6000.0,
        5600.0,
        7000.0,
        6800.0,
        1.0,
        False,
    )

    assert [event[0] for event in events] == ["calc_E_E_H_d_t_2024"]
    assert events[0][1][:5] == (6, 5600.0, 6000.0, 3.2, False)
    np.testing.assert_array_equal(events[0][1][5], q_hs * 3.6 / 1000)
    assert events[0][1][6:] == (6800.0, 7000.0, 1.0, "climate.csv")
    np.testing.assert_array_equal(actual, fan + rac)


def _cooling_type1_and3_args(model):
    values = [np.array([float(index)]) for index in range(1, 9)]
    return (
        model,
        6,
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        values[6],
        1000.0,
        4000.0,
        1200.0,
        500.0,
        100.0,
        7000.0,
        200.0,
        900.0,
        2100.0,
        "equipment-spec",
    )


def test_type1_cooling_preserves_formula_call_order_and_fan_sum(monkeypatch):
    events = []
    q_hs_CS_d_t = np.array([10.0])
    q_hs_CL_d_t = np.array([20.0])
    e_th_C_d_t = np.array([4.0])
    e_r_C_d_t = np.array([8.0])
    e_hs_C_d_t = np.array([9.0])
    E_E_comp_C_d_t = np.array([10.0])
    args = _cooling_type1_and3_args(計算モデル.ダクト式セントラル空調機)

    _record(monkeypatch, sut.dc_a, "get_q_hs_C_d_t", events, (q_hs_CS_d_t, q_hs_CL_d_t))
    _record(monkeypatch, sut.dc_a, "calc_e_th_mid_C", events, 2.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_rtd_C", events, 3.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_C_d_t", events, e_th_C_d_t)
    _record(monkeypatch, sut.dc_a, "get_e_r_rtd_C", events, 5.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_min_C", events, 6.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_mid_C", events, 7.0)
    _record(monkeypatch, sut.dc_a, "get_e_r_C_d_t", events, e_r_C_d_t)
    _record(monkeypatch, sut.dc_a, "get_e_hs_C_d_t", events, e_hs_C_d_t)
    _record(monkeypatch, sut.dc_a, "get_E_E_comp_C_d_t", events, E_E_comp_C_d_t)

    actual = sut.calc_E_E_C_d_t_type1_and_type3(*args)

    assert [event[0] for event in events] == [
        "get_q_hs_C_d_t",
        "calc_e_th_mid_C",
        "calc_e_th_rtd_C",
        "calc_e_th_C_d_t",
        "get_e_r_rtd_C",
        "get_e_r_min_C",
        "get_e_r_mid_C",
        "get_e_r_C_d_t",
        "get_e_hs_C_d_t",
        "get_E_E_comp_C_d_t",
    ]
    np.testing.assert_array_equal(events[7][1][0], q_hs_CS_d_t + q_hs_CL_d_t)
    assert events[-2][1] == (e_th_C_d_t, e_r_C_d_t)
    np.testing.assert_array_equal(actual, E_E_comp_C_d_t + args[2])


def test_type3_cooling_preserves_latent_efficiency_branch(monkeypatch):
    events = []
    args = _cooling_type1_and3_args(計算モデル.RAC活用型全館空調_潜熱評価モデル)
    q_hs_CS_d_t = np.array([10.0])
    q_hs_CL_d_t = np.array([20.0])

    _record(monkeypatch, sut.dc_a, "get_q_hs_C_d_t", events, (q_hs_CS_d_t, q_hs_CL_d_t))
    _record(monkeypatch, sut.dc_a, "calc_e_th_mid_C", events, 2.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_rtd_C", events, 3.0)
    _record(monkeypatch, sut.dc_a, "calc_e_th_C_d_t", events, np.array([4.0]))
    _record(monkeypatch, sut.jjj_latent, "get_e_r_C_d_t", events, np.array([8.0]))
    _record(monkeypatch, sut.dc_a, "get_e_hs_C_d_t", events, np.array([9.0]))
    _record(monkeypatch, sut.dc_a, "get_E_E_comp_C_d_t", events, np.array([10.0]))

    sut.calc_E_E_C_d_t_type1_and_type3(*args)

    assert [event[0] for event in events] == [
        "get_q_hs_C_d_t",
        "calc_e_th_mid_C",
        "calc_e_th_rtd_C",
        "calc_e_th_C_d_t",
        "get_e_r_C_d_t",
        "get_e_hs_C_d_t",
        "get_E_E_comp_C_d_t",
    ]
    np.testing.assert_array_equal(events[4][1][0], q_hs_CS_d_t + q_hs_CL_d_t)


def test_type2_cooling_preserves_unit_conversion_argument_order_log_and_sum(monkeypatch):
    events = []
    fan = np.array([1.0, 2.0])
    q_hs_CS = np.array([1000.0, 2000.0])
    q_hs_CL = np.array([300.0, 400.0])
    rac = np.array([3.0, 4.0])
    _record(monkeypatch, sut.pyhees.section4_3, "calc_E_E_C_d_t_2024", events, rac)
    _record(monkeypatch, sut._logger, "NDdebug", events, None)

    actual = sut.calc_E_E_C_d_t_type2(
        計算モデル.RAC活用型全館空調_現行省エネ法RACモデル,
        6,
        "climate.csv",
        fan,
        q_hs_CS,
        q_hs_CL,
        3.2,
        5600.0,
        6800.0,
        1.0,
        False,
    )

    assert [event[0] for event in events] == ["calc_E_E_C_d_t_2024", "NDdebug"]
    assert events[0][1][:4] == (6, 5600.0, 3.2, False)
    np.testing.assert_array_equal(events[0][1][4], q_hs_CS * 3.6 / 1000)
    np.testing.assert_array_equal(events[0][1][5], q_hs_CL * 3.6 / 1000)
    assert events[0][1][6:] == (6800.0, 1.0, "climate.csv")
    assert events[1][1] == ("E_E_CRAC_C_d_t", rac)
    np.testing.assert_array_equal(actual, fan + rac)
