from pathlib import Path

import gradio as gr
import pandas as pd
from matplotlib.figure import Figure

from verification_app.graphs import GRAPH_LABELS, build_result_graphs


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
    prefix = tmp_path / "graphsv1"
    output2.to_csv(f"{prefix}_output2.csv", encoding="cp932")
    output5.to_csv(f"{prefix}_H_output5.csv", encoding="cp932")
    output5.to_csv(f"{prefix}_C_output5.csv", encoding="cp932")

    figures = build_result_graphs({"case_name": "graphs"}, tmp_path, "v1")

    assert len(GRAPH_LABELS) == 5
    assert all(isinstance(figure, Figure) for figure in figures)
    assert [len(figure.axes) for figure in figures] == [4, 8, 4, 8, 2]
    assert [figure._suptitle.get_text() for figure in figures] == [
        "暖房代表期間",
        "暖房負荷順",
        "冷房代表期間",
        "冷房負荷順",
        "部分負荷効率（sCOP）",
    ]
    plot_data = gr.Plot().postprocess(figures[0])
    assert plot_data is not None
    assert plot_data.type == "matplotlib"
    assert plot_data.plot.startswith("data:image/")
