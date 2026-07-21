#!/usr/bin/env python3
"""Run the Phase 5 legacy-to-monorepo numerical regression suite."""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import os
import shutil
import sys
import tempfile
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "regression" / "phase5" / "manifest.json"
BASELINE_SUFFIXES = ("input.json", "output1.csv", "output2.csv")


class RegressionMismatch(AssertionError):
    """Raised when a generated artifact differs from its frozen baseline."""


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _selected_cases(
    manifest: dict[str, Any], requested: Iterable[str]
) -> list[dict[str, Any]]:
    cases = manifest["cases"]
    requested_ids = set(requested)
    if not requested_ids:
        return cases
    known_ids = {case["id"] for case in cases}
    unknown_ids = requested_ids - known_ids
    if unknown_ids:
        raise ValueError(f"Unknown Phase 5 case(s): {', '.join(sorted(unknown_ids))}")
    return [case for case in cases if case["id"] in requested_ids]


def _build_case_input(case: dict[str, Any], *, legacy: bool) -> dict[str, Any]:
    from verification_core import (
        build_input_data,
        build_legacy_input_data,
        default_ui_values,
    )

    values = default_ui_values()
    values.update(case["ui_overrides"])
    canonical_input = build_input_data(values)
    legacy_input = build_legacy_input_data(values)
    if canonical_input != legacy_input:
        raise RegressionMismatch(
            f"{case['id']}: canonical input no longer matches the legacy form builder"
        )
    return legacy_input if legacy else canonical_input


def _run_engine(case: dict[str, Any], workdir: Path, *, legacy: bool) -> dict[str, Path]:
    from jjjexperiment.constants import version_info
    from jjjexperiment.main import calc

    input_data = _build_case_input(case, legacy=legacy)
    version = version_info()
    case_name = str(input_data["case_name"])
    case_workdir = Path(tempfile.mkdtemp(prefix=f"{case['id']}-", dir=workdir))
    output = io.StringIO()
    previous_cwd = Path.cwd()
    try:
        os.chdir(case_workdir)
        with warnings.catch_warnings(), redirect_stdout(output), redirect_stderr(output):
            warnings.filterwarnings("ignore", message="DataFrame is highly fragmented.*")
            calc(input_data)
    except Exception as error:
        raise RuntimeError(
            f"{case['id']}: engine execution failed\n{output.getvalue()}"
        ) from error
    finally:
        os.chdir(previous_cwd)

    prefix = f"{case_name}{version}_"
    artifacts = {
        suffix: case_workdir / f"{prefix}{suffix}" for suffix in BASELINE_SUFFIXES
    }
    missing = [str(path) for path in artifacts.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{case['id']}: engine did not create: {', '.join(missing)}"
        )
    return artifacts


def _write_gzip(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as input_file, destination.open("wb") as raw_output:
        with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as gzip_output:
            shutil.copyfileobj(input_file, gzip_output)


def _read_gzip_json(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def _compare_json(case_id: str, actual: Path, expected: Path) -> None:
    actual_value = json.loads(actual.read_text(encoding="utf-8"))
    expected_value = _read_gzip_json(expected)
    if actual_value != expected_value:
        raise RegressionMismatch(f"{case_id}: calculation input JSON changed")


def _as_number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _compare_csv(
    case_id: str,
    actual: Path,
    expected: Path,
    *,
    relative_tolerance: float,
    absolute_tolerance: float,
) -> None:
    with actual.open("r", encoding="cp932", newline="") as actual_file:
        actual_rows = list(csv.reader(actual_file))
    with gzip.open(expected, "rt", encoding="cp932", newline="") as expected_file:
        expected_rows = list(csv.reader(expected_file))

    if len(actual_rows) != len(expected_rows):
        raise RegressionMismatch(
            f"{case_id}/{actual.name}: row count changed from "
            f"{len(expected_rows)} to {len(actual_rows)}"
        )
    if actual_rows and actual_rows[0] != expected_rows[0]:
        raise RegressionMismatch(f"{case_id}/{actual.name}: CSV header changed")

    for row_number, (actual_row, expected_row) in enumerate(
        zip(actual_rows[1:], expected_rows[1:], strict=True), start=2
    ):
        if len(actual_row) != len(expected_row):
            raise RegressionMismatch(
                f"{case_id}/{actual.name}:{row_number}: column count changed"
            )
        for column_number, (actual_cell, expected_cell) in enumerate(
            zip(actual_row, expected_row, strict=True), start=1
        ):
            actual_number = _as_number(actual_cell)
            expected_number = _as_number(expected_cell)
            if actual_number is None or expected_number is None:
                matches = actual_cell == expected_cell
            elif math.isnan(actual_number) or math.isnan(expected_number):
                matches = math.isnan(actual_number) and math.isnan(expected_number)
            else:
                matches = math.isclose(
                    actual_number,
                    expected_number,
                    rel_tol=relative_tolerance,
                    abs_tol=absolute_tolerance,
                )
            if not matches:
                raise RegressionMismatch(
                    f"{case_id}/{actual.name}:{row_number}:{column_number}: "
                    f"expected {expected_cell!r}, found {actual_cell!r}"
                )


def _baseline_path(manifest_path: Path, case_id: str, suffix: str) -> Path:
    return manifest_path.parent / "baselines" / f"{case_id}.{suffix}.gz"


def _update_case_baselines(
    manifest_path: Path, case: dict[str, Any], artifacts: dict[str, Path]
) -> None:
    for suffix, artifact in artifacts.items():
        _write_gzip(artifact, _baseline_path(manifest_path, case["id"], suffix))


def _verify_case(
    manifest_path: Path,
    manifest: dict[str, Any],
    case: dict[str, Any],
    artifacts: dict[str, Path],
) -> None:
    baseline_paths = {
        suffix: _baseline_path(manifest_path, case["id"], suffix)
        for suffix in BASELINE_SUFFIXES
    }
    missing = [str(path) for path in baseline_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing Phase 5 baseline(s): {', '.join(missing)}")

    _compare_json(case["id"], artifacts["input.json"], baseline_paths["input.json"])
    tolerances = manifest["tolerances"]
    for suffix in ("output1.csv", "output2.csv"):
        _compare_csv(
            case["id"],
            artifacts[suffix],
            baseline_paths[suffix],
            relative_tolerance=float(tolerances["relative"]),
            absolute_tolerance=float(tolerances["absolute"]),
        )


def run(args: argparse.Namespace) -> None:
    manifest_path = args.manifest.resolve()
    manifest = _load_manifest(manifest_path)
    if args.update_baselines and args.engine_commit != manifest["engine_commit"]:
        raise ValueError(
            "Baseline updates require --engine-commit to exactly match the manifest"
        )

    from jjjexperiment.constants import version_info

    actual_version = version_info()
    if actual_version != manifest["engine_version"]:
        raise RegressionMismatch(
            f"Engine version changed from {manifest['engine_version']} to {actual_version}"
        )

    cases = _selected_cases(manifest, args.case)
    temporary_root: tempfile.TemporaryDirectory[str] | None = None
    if args.workdir is None:
        temporary_root = tempfile.TemporaryDirectory(prefix="phase5-regression-")
        workdir = Path(temporary_root.name)
    else:
        workdir = args.workdir.resolve()
        workdir.mkdir(parents=True, exist_ok=True)

    try:
        for case in cases:
            artifacts = _run_engine(case, workdir, legacy=args.update_baselines)
            if args.update_baselines:
                _update_case_baselines(manifest_path, case, artifacts)
                action = "updated"
            else:
                _verify_case(manifest_path, manifest, case, artifacts)
                action = "passed"
            print(f"Phase 5 {case['id']}: {action}")
    finally:
        if temporary_root is not None:
            temporary_root.cleanup()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--case", action="append", default=[], help="Run one case ID")
    parser.add_argument("--workdir", type=Path, help="Keep generated artifacts here")
    parser.add_argument("--update-baselines", action="store_true")
    parser.add_argument(
        "--engine-commit",
        help="Required confirmation when --update-baselines is used",
    )
    return parser


def main() -> int:
    try:
        run(_parser().parse_args())
    except Exception as error:
        print(f"Phase 5 regression failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
