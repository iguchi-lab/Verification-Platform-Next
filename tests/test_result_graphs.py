from pathlib import Path

import gradio as gr
import numpy as np
import pandas as pd
import pytest
from jjjexperiment.csv_artifacts import capture_csv_exports, write_dataframe_csv
from matplotlib.figure import Figure

from verification_app.graphs import (
    GRAPH_LABELS,
    _format_apf,
    _ratio_of_sums,
    _relative_humidity,
    build_result_graphs,
)


def test_build_result_graphs_recreates_the_five_legacy_views(tmp_path: Path) -> None:
    index = pd.to_datetime(
        [
            "2023-02-05 00:00:00",
            "2023-02-06 00:00:00",
            "2023-08-06 00:00:00",
            "2023-08-07 00:00:00",
        ]
    )
    output2 = pd.DataFrame(
        {
            "Theta_ex_d_t [℃]": [2.0, 4.0, 30.0, 32.0],
            "q_hs_H_d_t [Wh/h]": [3000.0, 2000.0, 0.0, 0.0],
            "q_hs_CS_d_t [Wh/h]": [0.0, 0.0, 2500.0, 2000.0],
            "q_hs_CL_d_t [Wh/h]": [0.0, 0.0, 500.0, 400.0],
            "E_E_H_d_t [kWh/h]": [1.0, 0.8, 0.0, 0.0],
            "E_E_C_d_t [kWh/h]": [0.0, 0.0, 1.0, 0.9],
            "E_E_fan_H_d_t [kWh/h]": [0.1, 0.1, 0.0, 0.0],
            "E_E_fan_C_d_t [kWh/h]": [0.0, 0.0, 0.1, 0.1],
            "E_UT_H_d_t [MJ/h]": [0.0, 0.1, 0.0, 0.0],
            "E_UT_C_d_t [MJ/h]": [0.0, 0.0, 0.1, 0.0],
            "Theta_hs_H_out_d_t [℃]": [35.0, 34.0, 0.0, 0.0],
            "Theta_hs_H_in_d_t [℃]": [20.0, 20.0, 0.0, 0.0],
            "Theta_hs_C_out_d_t [℃]": [0.0, 0.0, 16.0, 17.0],
            "Theta_hs_C_in_d_t [℃]": [0.0, 0.0, 27.0, 27.0],
            "V_hs_supply_H_d_t [m3/h]": [1000.0, 900.0, 0.0, 0.0],
            "V_hs_supply_C_d_t [m3/h]": [0.0, 0.0, 1000.0, 900.0],
            "E_H_d_t [MJ/h]": [10.0, 8.0, 0.0, 0.0],
            "E_C_d_t [MJ/h]": [0.0, 0.0, 9.0, 8.0],
        },
        index=index,
    )
    output5 = pd.DataFrame({"X_ex_d_t": [0.004, 0.005, 0.012, 0.013]}, index=index)
    for room in range(1, 6):
        output5[f"X_HBR_d_t_{room}"] = [0.004, 0.005, 0.013425743, 0.013425743]
        output5[f"Theta_HBR_d_t_{room}"] = [20.0, 21.0, 27.0 + room, 27.0]
    output5["X_NR_d_t"] = [0.004, 0.005, 0.014, 0.015]
    output5["Theta_NR_d_t"] = [19.0, 20.0, 29.0, 30.0]
    prefix = tmp_path / "graphsv1"
    output2.to_csv(f"{prefix}_output2.csv", encoding="cp932")
    output5.to_csv(f"{prefix}_H_output5.csv", encoding="cp932")
    output5.to_csv(f"{prefix}_C_output5.csv", encoding="cp932")

    figures = build_result_graphs({"case_name": "graphs"}, tmp_path, "v1")

    assert len(GRAPH_LABELS) == 5
    assert all(isinstance(figure, Figure) for figure in figures)
    assert [len(figure.axes) for figure in figures] == [6, 8, 6, 8, 2]
    absolute = figures[2].axes[4]
    relative = figures[2].axes[5]
    assert [line.get_label() for line in absolute.lines] == ["居室1～5（同値）", "非居室", "外気"]
    assert absolute.lines[0].get_ydata() == pytest.approx([13.425743, 13.425743])
    assert len(relative.lines) == 7
    # Higher room temperatures give lower RH even with identical absolute humidity.
    assert relative.lines[0].get_ydata()[0] > relative.lines[4].get_ydata()[0]
    assert relative.lines[0].get_ydata()[1] == pytest.approx(60.0, abs=0.05)
    assert [figure._suptitle.get_text() for figure in figures] == [
        "暖房代表期間",
        "暖房負荷順",
        "冷房代表期間",
        "冷房負荷順",
        "部分負荷効率（sCOP）\n年間APF = 2.81（暖房 2.78／冷房 2.84）",
    ]
    plot_data = gr.Plot().postprocess(figures[0])
    assert plot_data is not None
    assert plot_data.type == "matplotlib"
    assert plot_data.plot.startswith("data:image/")


def test_humidity_conversion_matches_engine_and_handles_invalid_values() -> None:
    from pyhees.section11_5 import calc_h_ex

    temperatures = np.linspace(-20, 40, 8760)
    humidity = np.linspace(0.001, 0.020, 8760)
    actual = _relative_humidity(pd.Series(temperatures), pd.Series(humidity))
    np.testing.assert_allclose(actual, calc_h_ex(humidity, temperatures), rtol=1e-12)
    values = _relative_humidity(
        pd.Series([20, 20, np.nan, 20, -274]), pd.Series([0.03, -0.01, 0.01, np.inf, 0.01]),
    )
    assert values.iloc[0] > 100  # Do not silently clip supersaturated model states.
    assert values.iloc[1:].isna().all()


def test_annual_apf_is_unavailable_without_electricity() -> None:
    apf = _ratio_of_sums(pd.Series([1.0, 2.0]), pd.Series([0.0, 0.0]))

    assert _format_apf(apf) == "算定不能"


def test_build_result_graphs_reads_deferred_dataframes(tmp_path: Path) -> None:
    index = pd.to_datetime(["2023-02-05", "2023-08-06"])
    output2 = pd.DataFrame(
        {
            "Theta_ex_d_t [℃]": [2.0, 30.0],
            "q_hs_H_d_t [Wh/h]": [3000.0, 0.0],
            "q_hs_CS_d_t [Wh/h]": [0.0, 2500.0],
            "q_hs_CL_d_t [Wh/h]": [0.0, 500.0],
            "E_E_H_d_t [kWh/h]": [1.0, 0.0],
            "E_E_C_d_t [kWh/h]": [0.0, 1.0],
            "E_E_fan_H_d_t [kWh/h]": [0.1, 0.0],
            "E_E_fan_C_d_t [kWh/h]": [0.0, 0.1],
            "E_UT_H_d_t [MJ/h]": [0.0, 0.0],
            "E_UT_C_d_t [MJ/h]": [0.0, 0.0],
            "Theta_hs_H_out_d_t [℃]": [35.0, 0.0],
            "Theta_hs_H_in_d_t [℃]": [20.0, 0.0],
            "Theta_hs_C_out_d_t [℃]": [0.0, 16.0],
            "Theta_hs_C_in_d_t [℃]": [0.0, 27.0],
            "V_hs_supply_H_d_t [m3/h]": [1000.0, 0.0],
            "V_hs_supply_C_d_t [m3/h]": [0.0, 1000.0],
            "E_H_d_t [MJ/h]": [10.0, 0.0],
            "E_C_d_t [MJ/h]": [0.0, 9.0],
        },
        index=index,
    )
    output5 = pd.DataFrame({"X_ex_d_t": [0.004, 0.012]}, index=index)
    prefix = tmp_path / "graphsv1"
    with capture_csv_exports() as exports:
        write_dataframe_csv(output2, f"{prefix}_output2.csv", encoding="cp932")
        write_dataframe_csv(output5, f"{prefix}_H_output5.csv", encoding="cp932")
        write_dataframe_csv(output5, f"{prefix}_C_output5.csv", encoding="cp932")

    figures = build_result_graphs({"case_name": "graphs"}, tmp_path, "v1", exports)

    assert len(figures) == 5
    assert not tuple(tmp_path.glob("*.csv"))
