import copy
import os
from pathlib import Path

import pandas as pd
import pytest

from jjjexperiment.csv_artifacts import capture_csv_exports, write_dataframe_csv
from verification_app.services import CalculationService


def test_service_builds_input_captures_log_and_collects_outputs(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        print("engine log")
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")
        Path("unrelated.txt").write_text("ignore", encoding="utf-8")

    def build_graphs(
        input_data: dict[str, object],
        output_dir: Path,
        version: str,
        csv_exports: object | None,
    ) -> tuple[str, ...]:
        assert input_data["case_name"] == "service"
        assert output_dir == tmp_path / "run-first"
        assert version == "v1"
        assert csv_exports is None
        return ("heating", "cooling")

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        build_graphs=build_graphs,
        run_id_factory=lambda: "first",
    )

    result = service.run({"case_name__0": "service"})

    assert result.succeeded
    assert result.status == "✅ 計算が完了しました。（計算ID: first）"
    assert result.run_id == "first"
    assert result.artifact_dir == str(tmp_path / "run-first")
    assert result.input_data is not None
    assert result.input_data["case_name"] == "service"
    assert "===== 1. 計算条件 =====" in result.log
    assert "暖房方式:" in result.log
    assert "===== 2. 実行した処理 =====" in result.log
    assert "===== 5. 計算エンジン詳細ログ =====" in result.log
    assert "engine log" in result.log
    assert {Path(path).suffix for path in result.files} == {".csv"}
    assert result.graph_status == "✅ 2件のグラフを生成しました。"
    assert result.graphs == ("heating", "cooling")
    assert (tmp_path / "run-first" / "servicev1.csv").is_file()


def test_service_builds_annual_heating_and_cooling_summary(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}_output1.csv").write_text(
            ",E_H [MJ/year],E_C [MJ/year]\n合計値,100,200\n",
            encoding="cp932",
        )
        Path(f"{prefix}_output2.csv").write_text(
            ",E_E_H_d_t [kWh/h],E_E_C_d_t [kWh/h],"
            "E_UT_H_d_t [MJ/h],E_UT_C_d_t [MJ/h],"
            "E_E_fan_H_d_t [kWh/h],E_E_fan_C_d_t [kWh/h]\n"
            "2023-01-01 00:00:00,1,3,10,30,0.2,0.5\n"
            "2023-01-01 01:00:00,2,4,20,40,0.3,1.0\n",
            encoding="cp932",
        )

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        run_id_factory=lambda: "summary",
    )

    result = service.run({"case_name__0": "annual"}, include_graphs=False)

    assert result.succeeded
    assert result.annual_summary is not None
    assert result.annual_summary.heating.primary_energy_mj == 100
    assert result.annual_summary.heating.unprocessed_load_mj == 30
    assert result.annual_summary.heating.air_conditioner_electricity_kwh == 2.5
    assert result.annual_summary.heating.fan_electricity_kwh == 0.5
    assert result.annual_summary.cooling.primary_energy_mj == 200
    assert result.annual_summary.cooling.unprocessed_load_mj == 70
    assert result.annual_summary.cooling.air_conditioner_electricity_kwh == 5.5
    assert result.annual_summary.cooling.fan_electricity_kwh == 1.5
    assert "暖房 一次エネルギー消費量: 100.000 MJ/年" in result.log
    assert "冷房 消費電力量（ファン）: 1.500 kWh/年" in result.log
    assert "一次エネルギー消費量には未処理負荷" in result.log


def test_service_returns_traceback_on_error(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        print("before failure")
        raise RuntimeError("engine failed")

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        run_id_factory=lambda: "failed",
    )

    result = service.run({})

    assert not result.succeeded
    assert result.status == "❌ 計算エラー（計算ID: failed）"
    assert result.run_id == "failed"
    assert result.artifact_dir == str(tmp_path / "run-failed")
    assert "before failure" in result.log
    assert "RuntimeError: engine failed" in result.log
    assert "===== 4. エラー詳細 =====" in result.log
    assert result.files == ()
    assert result.graph_status == "計算完了後にグラフを表示します。"
    assert result.graphs == ()


def test_service_preserves_successful_calculation_when_graphs_fail(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")

    def build_graphs(
        input_data: dict[str, object],
        output_dir: Path,
        version: str,
        csv_exports: object | None,
    ) -> tuple[object, ...]:
        raise KeyError("missing graph column")

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        build_graphs=build_graphs,
        run_id_factory=lambda: "graph-error",
    )

    result = service.run({"case_name__0": "service"})

    assert result.succeeded
    assert result.status == "✅ 計算が完了しました。（計算ID: graph-error）"
    assert result.graph_status.startswith("❌ グラフ生成エラー")
    assert "KeyError: 'missing graph column'" in result.log
    assert result.graphs == ()


def test_service_can_return_files_before_generating_graphs(tmp_path: Path) -> None:
    graph_calls: list[str] = []

    def calculate(input_data: dict[str, object]) -> None:
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")

    def build_graphs(
        input_data: dict[str, object],
        output_dir: Path,
        version: str,
        csv_exports: object | None,
    ) -> tuple[str, ...]:
        graph_calls.append(str(input_data["case_name"]))
        return ("heating", "cooling")

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        build_graphs=build_graphs,
        run_id_factory=lambda: "deferred",
    )

    calculation = service.run(
        {"case_name__0": "deferred"},
        include_graphs=False,
    )

    assert calculation.succeeded
    assert calculation.files
    assert calculation.graphs == ()
    assert graph_calls == []

    completed = service.generate_graphs(calculation)

    assert graph_calls == ["deferred"]
    assert completed.graph_status == "✅ 2件のグラフを生成しました。"
    assert completed.graphs == ("heating", "cooling")


def test_service_defers_csv_until_explicit_export(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        prefix = f"{input_data['case_name']}v1"
        output1 = pd.DataFrame(
            {"E_H [MJ/year]": [100.0], "E_C [MJ/year]": [200.0]},
            index=["合計値"],
        )
        output2 = pd.DataFrame(
            {
                "E_E_H_d_t [kWh/h]": [1.0, 2.0],
                "E_E_C_d_t [kWh/h]": [3.0, 4.0],
                "E_UT_H_d_t [MJ/h]": [10.0, 20.0],
                "E_UT_C_d_t [MJ/h]": [30.0, 40.0],
                "E_E_fan_H_d_t [kWh/h]": [0.2, 0.3],
                "E_E_fan_C_d_t [kWh/h]": [0.5, 1.0],
            }
        )
        write_dataframe_csv(output1, f"{prefix}_output1.csv", encoding="cp932")
        write_dataframe_csv(output2, f"{prefix}_output2.csv", encoding="cp932")

    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        run_id_factory=lambda: "deferred-csv",
        csv_export_session=capture_csv_exports,
    )

    result = service.run({"case_name__0": "deferred"}, include_graphs=False)
    artifact_dir = tmp_path / "run-deferred-csv"

    assert result.succeeded
    assert result.annual_summary is not None
    assert result.annual_summary.heating.primary_energy_mj == 100.0
    assert result.annual_summary.cooling.unprocessed_load_mj == 70.0
    assert not tuple(artifact_dir.glob("*.csv"))
    assert result.csv_status.startswith("CSVファイルは未出力")
    assert copy.deepcopy(result).csv_exports is result.csv_exports

    exported = service.export_csv(result)

    assert exported.csv_status == "✅ 2件のCSVファイルを出力しました。"
    assert len(tuple(artifact_dir.glob("*.csv"))) == 2
    assert {Path(path).suffix for path in exported.files} == {".csv"}


def test_same_case_name_uses_independent_artifact_directories(tmp_path: Path) -> None:
    call_number = 0

    def calculate(input_data: dict[str, object]) -> None:
        nonlocal call_number
        call_number += 1
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text(str(call_number), encoding="utf-8")

    run_ids = iter(("first", "second"))
    service = CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
        run_id_factory=lambda: next(run_ids),
    )

    first = service.run({"case_name__0": "same"}, include_graphs=False)
    second = service.run({"case_name__0": "same"}, include_graphs=False)

    first_file = Path(first.files[0])
    second_file = Path(second.files[0])
    assert first_file.parent == tmp_path / "run-first"
    assert second_file.parent == tmp_path / "run-second"
    assert first_file.read_text(encoding="utf-8") == "1"
    assert second_file.read_text(encoding="utf-8") == "2"


def test_expired_artifact_directories_are_removed_before_calculation(
    tmp_path: Path,
) -> None:
    expired = tmp_path / "run-expired"
    expired.mkdir()
    (expired / "old.csv").write_text("old", encoding="utf-8")
    expired.touch()
    os.utime(expired, (0, 0))

    service = CalculationService(
        lambda input_data: None,
        lambda: "v1",
        workdir=tmp_path,
        result_ttl_seconds=60,
        run_id_factory=lambda: "current",
    )

    result = service.run({}, include_graphs=False)

    assert result.succeeded
    assert not expired.exists()
    assert (tmp_path / "run-current").is_dir()


@pytest.mark.parametrize("case_name", ("../escape", "folder/name", r"folder\name"))
def test_case_name_cannot_escape_the_artifact_directory(
    tmp_path: Path,
    case_name: str,
) -> None:
    service = CalculationService(lambda input_data: None, lambda: "v1", workdir=tmp_path)

    result = service.run({"case_name__0": case_name}, include_graphs=False)

    assert not result.succeeded
    assert "計算条件名にパスとして解釈される文字" in result.log
    assert not tuple(tmp_path.glob("run-*"))
