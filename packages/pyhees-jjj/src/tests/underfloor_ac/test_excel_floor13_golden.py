from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from jjjexperiment.main import calc
from jjjexperiment.underfloor_ac.hourly_solver import (
    calculate_ground_response_history,
)
from pyhees.section11_1 import load_climate


FIXTURE_DIR = Path(__file__).with_name("fixtures")
MANIFEST_PATH = FIXTURE_DIR / "excel_floor13_golden_manifest.json"
GOLDEN_PATH = FIXTURE_DIR / "excel_floor13_golden.npz"
INPUT_PATH = FIXTURE_DIR / "excel_floor13_input.json"

OUTPUT5_SERIES = {
    "q_hat_hs": "Q_hat_hs_d_t",
    "v_dash_supply_1": "V_dash_supply_d_t_1",
    "v_dash_supply_2": "V_dash_supply_d_t_2",
    "theta_star_nr": "Theta_star_NR_d_t",
    "theta_hs_out": "Theta_hs_out_d_t",
    "v_supply_1": "V_supply_d_t_1",
    "v_supply_2": "V_supply_d_t_2",
    "theta_supply_1": "Theta_supply_d_t_1",
    "theta_supply_2": "Theta_supply_d_t_2",
    "theta_hbr_1": "Theta_HBR_d_t_1",
    "theta_hbr_2": "Theta_HBR_d_t_2",
    "theta_nr": "Theta_NR_d_t",
}


def _latest_column(frame: pd.DataFrame, base: str) -> np.ndarray:
    matches = [
        column
        for column in frame.columns
        if column == base
        or (
            column.startswith(f"{base}.")
            and column[len(base) + 1 :].isdigit()
        )
    ]
    if not matches:
        raise KeyError(base)
    return frame[matches[-1]].to_numpy(dtype=float)


def _assert_display_equal(
    actual: np.ndarray,
    expected: np.ndarray,
    mask: np.ndarray,
    *,
    name: str,
    manifest: dict,
) -> None:
    series = manifest["series"][name]
    decimals = int(series["decimals"])
    tolerance = 0.5 * 10.0 ** (-decimals)
    delta = np.abs(actual[mask] - expected[mask])
    mismatches = np.flatnonzero(mask)[delta >= tolerance]
    if mismatches.size:
        cells = [
            f"{series['column']}{series['first_row'] + int(index)}"
            for index in mismatches[:10]
        ]
        max_abs = float(np.max(delta))
        raise AssertionError(
            f"{series['sheet']}!{name} has {mismatches.size} "
            f"display-level mismatches; first={cells}; "
            f"max_abs={max_abs}; decimals={decimals}"
        )


def _single_output(directory: Path, suffix: str) -> Path:
    matches = list(directory.glob(f"*{suffix}"))
    assert len(matches) == 1, matches
    return matches[0]


def test_ground_response_matches_all_8760_excel_cached_values():
    golden = np.load(GOLDEN_PATH)
    theta_ex = load_climate(6)["外気温[℃]"].to_numpy()

    actual = calculate_ground_response_history(
        golden["actual_floor_temperature"],
        theta_ex,
        True,
    )

    np.testing.assert_allclose(
        actual,
        golden["ground_response"],
        rtol=0.0,
        atol=5e-13,
    )


def test_excel_floor13_golden_outputs(tmp_path, monkeypatch):
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    inputs = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    monkeypatch.chdir(tmp_path)

    result = calc(copy.deepcopy(inputs), test_mode=True)

    annual = manifest["annual_MJ_per_year"]
    tolerance = annual["comparison_absolute_tolerance"]
    assert result["TValue"].E_H == pytest.approx(
        annual["heating"],
        abs=tolerance,
    )
    assert result["TValue"].E_C == pytest.approx(
        annual["cooling"],
        abs=tolerance,
    )

    golden = np.load(GOLDEN_PATH)
    season_code = golden["season_code"]
    assert int(np.count_nonzero(season_code == 1)) == 4056
    assert int(np.count_nonzero(season_code == 2)) == 2808
    assert int(np.count_nonzero(season_code == 0)) == 1896

    for mode, season_value in (("H", 1), ("C", 2)):
        mask = season_code == season_value
        output5 = pd.read_csv(
            _single_output(tmp_path, f"_{mode}_output5.csv"),
            encoding="cp932",
        )
        output_uf = pd.read_csv(
            _single_output(tmp_path, f"_{mode}_output_uf.csv"),
            encoding="cp932",
        )
        for name, column in OUTPUT5_SERIES.items():
            _assert_display_equal(
                _latest_column(output5, column),
                golden[name],
                mask,
                name=name,
                manifest=manifest,
            )

        load_series = (
            {
                "l_star_h_1": "L_star_H_d_t_i_1",
                "l_star_h_2": "L_star_H_d_t_i_2",
            }
            if mode == "H"
            else {
                "l_star_cs_1": "L_star_CS_d_t_i_1",
                "l_star_cs_2": "L_star_CS_d_t_i_2",
            }
        )
        for name, column in load_series.items():
            _assert_display_equal(
                _latest_column(output5, column),
                golden[name],
                mask,
                name=name,
                manifest=manifest,
            )

        target_name = (
            "heating_target" if mode == "H" else "cooling_target"
        )
        _assert_display_equal(
            _latest_column(output_uf, "Theta_uf_d_t_2023"),
            golden[target_name],
            mask,
            name=target_name,
            manifest=manifest,
        )
        _assert_display_equal(
            _latest_column(output_uf, "Theta_uf_d_t"),
            golden["actual_floor_temperature"],
            mask,
            name="actual_floor_temperature",
            manifest=manifest,
        )
