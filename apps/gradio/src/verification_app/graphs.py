from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import matplotlib.dates as mdates
import matplotlib_fontja  # noqa: F401
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

GRAPH_LABELS = (
    "暖房時系列",
    "暖房負荷順",
    "冷房時系列",
    "冷房負荷順",
    "sCOP",
)

_WINTER = slice("2023-02-05 00:00:00", "2023-02-13 00:00:00")
_SUMMER = slice("2023-08-06 00:00:00", "2023-08-14 00:00:00")


def build_result_graphs(
    input_data: Mapping[str, Any], output_dir: Path, version: str
) -> tuple[Figure, ...]:
    """Build the five graphs provided by the legacy 260715 notebook."""
    prefix = f"{input_data.get('case_name', 'default')}{version}"
    output2 = _read_output(output_dir / f"{prefix}_output2.csv")
    output5_heating = _read_output(output_dir / f"{prefix}_H_output5.csv")
    output5_cooling = _read_output(output_dir / f"{prefix}_C_output5.csv")

    winter = output2.loc[_WINTER]
    summer = output2.loc[_SUMMER]
    winter_detail = output5_heating.loc[_WINTER]
    summer_detail = output5_cooling.loc[_SUMMER]

    heating_sorted = output2.sort_values("q_hs_H_d_t [Wh/h]", ascending=False).copy()
    heating_sorted.loc[heating_sorted["q_hs_H_d_t [Wh/h]"] <= 0.0] = np.nan

    cooling_sorted = output2.copy()
    cooling_sorted["q_hs_C_d_t [Wh/h]"] = (
        cooling_sorted["q_hs_CS_d_t [Wh/h]"]
        + cooling_sorted["q_hs_CL_d_t [Wh/h]"]
    )
    cooling_sorted = cooling_sorted.sort_values("q_hs_C_d_t [Wh/h]", ascending=False)
    cooling_sorted.loc[cooling_sorted["q_hs_C_d_t [Wh/h]"] <= 0.0] = np.nan

    return (
        _season_timeseries(winter, winter_detail, heating=True),
        _load_duration(heating_sorted, heating=True),
        _season_timeseries(summer, summer_detail, heating=False),
        _load_duration(cooling_sorted, heating=False),
        _scop(winter, summer),
    )


def _read_output(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="cp932", index_col=0)
    frame.index = pd.to_datetime(frame.index)
    return frame


def _season_timeseries(
    output2: pd.DataFrame, output5: pd.DataFrame, *, heating: bool
) -> Figure:
    figure = Figure(figsize=(18, 8), layout="constrained")
    axes = figure.subplots(2, 2)
    suffix = "H" if heating else "C"

    axes[0, 0].plot(
        output2.index,
        output2["Theta_ex_d_t [℃]"],
        label="外気温[℃]",
        color="lightblue",
    )
    axes[0, 0].plot(
        output5.index,
        output5["X_ex_d_t"] * 1000,
        label="外気絶対湿度[g/kg]",
        color="orange",
    )
    _style_axis(axes[0, 0], "温度[℃]、絶対湿度[g/kg]", ylim=(-10, 40), legend=True)

    if heating:
        processed_heat = output2["q_hs_H_d_t [Wh/h]"] / 1000
    else:
        processed_heat = (
            output2["q_hs_CS_d_t [Wh/h]"] + output2["q_hs_CL_d_t [Wh/h]"]
        ) / 1000
    axes[0, 1].plot(output2.index, processed_heat, label="処理熱量[kWh/h]", color="red")
    axes[0, 1].plot(
        output2.index,
        output2[f"E_E_{suffix}_d_t [kWh/h]"],
        label="AC+FAN消費電力[kWh/h]",
        color="blue",
    )
    axes[0, 1].plot(
        output2.index,
        output2[f"E_E_fan_{suffix}_d_t [kWh/h]"],
        label="FAN消費電力[kWh/h]",
        color="green",
    )
    _style_axis(
        axes[0, 1],
        "処理熱量[kWh/h]、消費電力[kWh/h]",
        ylim=(0, 10),
        legend=True,
    )

    axes[1, 0].plot(
        output2.index,
        output2[f"E_UT_{suffix}_d_t [MJ/h]"],
        label="未処理負荷",
        color="red",
    )
    _style_axis(
        axes[1, 0],
        "未処理負荷（一次エネルギー相当分）[MJ/h]",
        ylim=(0, 10),
        legend=True,
    )

    axes[1, 1].plot(
        output2.index,
        _safe_ratio(processed_heat, output2[f"E_E_{suffix}_d_t [kWh/h]"]),
        label="sCOP[-]",
        color="black",
    )
    _style_axis(axes[1, 1], "sCOP[-]", ylim=(0, 10), legend=True)

    for axis in axes.flat:
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    figure.suptitle("暖房代表期間" if heating else "冷房代表期間")
    return figure


def _load_duration(output2: pd.DataFrame, *, heating: bool) -> Figure:
    figure = Figure(figsize=(18, 8), layout="constrained")
    axes = figure.subplots(2, 4)
    color = "orange" if heating else "lightblue"
    suffix = "H" if heating else "C"
    x_values = range(len(output2))
    heat_column = "q_hs_H_d_t [Wh/h]" if heating else "q_hs_C_d_t [Wh/h]"

    series = (
        (output2[heat_column] / 1000, "処理熱量[kWh/h]", (0, 10)),
        (output2[f"Theta_hs_{suffix}_out_d_t [℃]"], "室内機出口温度[℃]", (0, 50)),
        (output2[f"Theta_hs_{suffix}_in_d_t [℃]"], "室内機入口温度[℃]", (0, 50)),
        (output2[f"V_hs_supply_{suffix}_d_t [m3/h]"], "供給風量[m3/h]", (0, 2000)),
        (output2[f"E_{suffix}_d_t [MJ/h]"], "一次エネルギー消費量[MJ/h]", (0, 50)),
        (
            output2[f"E_UT_{suffix}_d_t [MJ/h]"],
            "未処理負荷（一次エネルギー相当分）[MJ/h]",
            (0, 50),
        ),
        (output2[f"E_E_{suffix}_d_t [kWh/h]"], "AC+FAN消費電力[kWh/h]", (0, 5)),
        (output2[f"E_E_fan_{suffix}_d_t [kWh/h]"], "FAN消費電力[kWh/h]", (0, 5)),
    )
    for axis, (values, ylabel, ylim) in zip(axes.flat, series, strict=True):
        axis.plot(x_values, values, color=color)
        _style_axis(axis, ylabel, xlabel="時間[h]", ylim=ylim)
    figure.suptitle("暖房負荷順" if heating else "冷房負荷順")
    return figure


def _scop(winter: pd.DataFrame, summer: pd.DataFrame) -> Figure:
    figure = Figure(figsize=(18, 7), layout="constrained")
    axes = figure.subplots(1, 2)
    heating_heat = winter["q_hs_H_d_t [Wh/h]"] / 1000
    cooling_heat = (
        summer["q_hs_CS_d_t [Wh/h]"] + summer["q_hs_CL_d_t [Wh/h]"]
    ) / 1000

    axes[0].scatter(
        heating_heat,
        _safe_ratio(heating_heat, winter["E_E_H_d_t [kWh/h]"]),
        label="sCOP[-]",
        color="orange",
    )
    axes[1].scatter(
        cooling_heat,
        _safe_ratio(cooling_heat, summer["E_E_C_d_t [kWh/h]"]),
        label="sCOP[-]",
        color="lightblue",
    )
    for axis, title in zip(axes, ("暖房", "冷房"), strict=True):
        _style_axis(
            axis,
            "sCOP[-]",
            xlabel="処理熱量 [kWh/h]",
            xlim=(0, 10),
            ylim=(0, 10),
            legend=True,
        )
        axis.set_title(title)
    figure.suptitle("部分負荷効率（sCOP）")
    return figure


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)


def _style_axis(
    axis: Any,
    ylabel: str,
    *,
    xlabel: str | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    legend: bool = False,
) -> None:
    axis.set_ylabel(ylabel)
    if xlabel is not None:
        axis.set_xlabel(xlabel)
    if xlim is not None:
        axis.set_xlim(*xlim)
    if ylim is not None:
        axis.set_ylim(*ylim)
    axis.grid()
    if legend:
        axis.legend()
