import os
from pathlib import Path

import pytest

from verification_app.services import CalculationService


def test_service_builds_input_captures_log_and_collects_outputs(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        print("engine log")
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")
        Path("unrelated.txt").write_text("ignore", encoding="utf-8")

    def build_graphs(
        input_data: dict[str, object], output_dir: Path, version: str
    ) -> tuple[str, ...]:
        assert input_data["case_name"] == "service"
        assert output_dir == tmp_path / "run-first"
        assert version == "v1"
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
    assert result.log == "engine log\n"
    assert {Path(path).suffix for path in result.files} == {".csv"}
    assert result.graph_status == "✅ 2件のグラフを生成しました。"
    assert result.graphs == ("heating", "cooling")
    assert (tmp_path / "run-first" / "servicev1.csv").is_file()


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
    assert result.files == ()
    assert result.graph_status == "計算完了後にグラフを表示します。"
    assert result.graphs == ()


def test_service_preserves_successful_calculation_when_graphs_fail(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")

    def build_graphs(
        input_data: dict[str, object], output_dir: Path, version: str
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
        input_data: dict[str, object], output_dir: Path, version: str
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
