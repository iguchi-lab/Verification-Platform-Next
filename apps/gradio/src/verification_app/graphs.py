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
    input_data: Mapping[str, Any],
    output_dir: Path,
    version: str,
    csv_exports: Any | None = None,
) -> tuple[Figure, ...]:
    """Build the five graphs provided by the legacy 260715 notebook."""
    prefix = f"{input_data.get('case_name', 'default')}{version}"
    output2 = _read_output(output_dir / f"{prefix}_output2.csv", csv_exports)
    output5_heating = _read_output(
        output_dir / f"{prefix}_H_output5.csv",
        csv_exports,
    )
    output5_cooling = _read_output(
        output_dir / f"{prefix}_C_output5.csv",
        csv_exports,
    )

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
        _scop(output2, winter, summer),
    )


def _read_output(path: Path, csv_exports: Any | None = None) -> pd.DataFrame:
    dataframe = getattr(csv_exports, "dataframe", None)
    captured = None if dataframe is None else dataframe(path)
    frame = (
        pd.read_csv(path, encoding="cp932", index_col=0)
        if captured is None
        else captured.copy(deep=False)
    )
    frame.index = pd.to_datetime(frame.index)
    return frame


def _season_timeseries(
    output2: pd.DataFrame, output5: pd.DataFrame, *, heating: bool
) -> Figure:
    figure = Figure(figsize=(18, 12), layout="constrained")
    axes = figure.subplots(3, 2)
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

    _humidity_timeseries(axes[2, 0], axes[2, 1], output2, output5)
    for axis in axes.flat:
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
    figure.get_layout_engine().set(rect=(0, 0.07, 1, 0.93))
    figure.text(
        0.02, 0.015,
        "湿度は計算モデルの値：居室の絶対湿度は暖房期・中間期に外気と同値、冷房期に設定値で一定。\n"
        "相対湿度は各区画の室温と絶対湿度から換算（標準大気圧）。"
        "絶対湿度が同じ区画はまとめて表示。居室1＝主たる居室、居室2～5＝その他の居室。",
        fontsize=10,
    )
    figure.suptitle("暖房代表期間" if heating else "冷房代表期間")
    return figure


def _relative_humidity(temperature: pd.Series, humidity: pd.Series) -> pd.Series:
    """Convert kg/kg(DA) to % using section11_5 equations at 101325 Pa.

    The engine helper allocates 8760 values; this equivalent vector expression
    also supports the representative-period slices used by the plots.
    """
    kelvin = temperature + 273.16
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        water = (
            -6096.9385 / kelvin + 21.2409642 - 0.02711193 * kelvin
            + 0.00001673952 * kelvin ** 2 + 2.433502 * np.log(kelvin)
        )
        ice = (
            -6024.5282 / kelvin + 29.32707 + 0.010613863 * kelvin
            - 0.000013198825 * kelvin ** 2 - 0.49382577 * np.log(kelvin)
        )
        saturation = np.exp(water.where(temperature > 0, ice))
        relative = 100 * 101325 * humidity / (0.622 + humidity) / saturation
    valid = (
        np.isfinite(temperature) & np.isfinite(humidity) & (humidity >= 0)
        & (kelvin > 0) & np.isfinite(relative)
    )
    # Preserve values above 100% so inconsistent model states are not concealed.
    return relative.where(valid)


def _humidity_timeseries(
    absolute_axis: Any, relative_axis: Any,
    output2: pd.DataFrame, output5: pd.DataFrame,
) -> None:
    absolute_axis.set_title("屋内・外気の絶対湿度")
    relative_axis.set_title("屋内・外気の相対湿度")
    room_series = []
    indoor_count = 0
    for index in range(1, 6):
        x_key, t_key = f"X_HBR_d_t_{index}", f"Theta_HBR_d_t_{index}"
        if x_key not in output5:
            continue
        indoor_count += 1
        humidity = output5[x_key].where(np.isfinite(output5[x_key]) & (output5[x_key] >= 0))
        color = f"C{index - 1}"
        # Only collapse genuinely equal series; retain differing room humidity.
        match = next((item for item in room_series if item[0].equals(humidity)), None)
        if match is None:
            room_series.append((humidity, [str(index)], color))
        else:
            match[1].append(str(index))
        if t_key in output5:
            relative_axis.plot(
                output5.index, _relative_humidity(output5[t_key], humidity),
                label=f"居室{index}", color=color,
            )
    for humidity, rooms, color in room_series:
        absolute_axis.plot(
            output5.index, humidity * 1000, color=color,
            label="居室" + ("1～5（同値）" if len(rooms) == 5 else "・".join(rooms)),
        )
    for x_key, t_key, label, color, style in (
        ("X_NR_d_t", "Theta_NR_d_t", "非居室", "C5", "-"),
        ("X_ex_d_t", "Theta_ex_d_t [℃]", "外気", "dimgray", "--"),
    ):
        if x_key not in output5:
            continue
        humidity = output5[x_key].where(np.isfinite(output5[x_key]) & (output5[x_key] >= 0))
        absolute_axis.plot(output5.index, humidity * 1000, label=label, color=color, ls=style)
        temperature = output2[t_key].reindex(output5.index) if label == "外気" else output5.get(t_key)
        if temperature is not None:
            relative_axis.plot(
                output5.index, _relative_humidity(temperature, humidity),
                label=label, color=color, ls=style,
            )
        if label == "非居室":
            indoor_count += 1
    for axis, ylabel in (
        (absolute_axis, "絶対湿度 [g/kg(DA)]"), (relative_axis, "相対湿度 [%]"),
    ):
        _style_axis(axis, ylabel, legend=bool(axis.lines))
        axis.set_ylim(bottom=0)
        if axis is relative_axis:
            axis.set_ylim(top=max(100, axis.get_ylim()[1]))
        if not indoor_count:
            axis.text(0.5, 0.95, "室内湿度データなし", ha="center", va="top", transform=axis.transAxes)


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


def _scop(
    annual: pd.DataFrame,
    winter: pd.DataFrame,
    summer: pd.DataFrame,
) -> Figure:
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
    annual_heating_heat = annual["q_hs_H_d_t [Wh/h]"] / 1000
    annual_cooling_heat = (
        annual["q_hs_CS_d_t [Wh/h]"] + annual["q_hs_CL_d_t [Wh/h]"]
    ) / 1000
    heating_apf = _ratio_of_sums(
        annual_heating_heat,
        annual["E_E_H_d_t [kWh/h]"],
    )
    cooling_apf = _ratio_of_sums(
        annual_cooling_heat,
        annual["E_E_C_d_t [kWh/h]"],
    )
    annual_apf = _ratio_of_sums(
        annual_heating_heat + annual_cooling_heat,
        annual["E_E_H_d_t [kWh/h]"] + annual["E_E_C_d_t [kWh/h]"],
    )
    figure.suptitle(
        "部分負荷効率（sCOP）\n"
        f"年間APF = {_format_apf(annual_apf)}"
        f"（暖房 {_format_apf(heating_apf)}／冷房 {_format_apf(cooling_apf)}）"
    )
    return figure


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.replace(0, np.nan)


def _ratio_of_sums(numerator: pd.Series, denominator: pd.Series) -> float:
    denominator_sum = float(denominator.sum())
    if denominator_sum <= 0.0:
        return float("nan")
    return float(numerator.sum()) / denominator_sum


def _format_apf(value: float) -> str:
    return "算定不能" if not np.isfinite(value) else f"{value:.2f}"


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
