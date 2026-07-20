from pathlib import Path

from verification_app.services import CalculationService


def test_service_builds_input_captures_log_and_collects_outputs(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        print("engine log")
        prefix = f"{input_data['case_name']}v1"
        Path(f"{prefix}.csv").write_text("result", encoding="utf-8")
        Path(f"{prefix}.png").write_bytes(b"png")
        Path("unrelated.txt").write_text("ignore", encoding="utf-8")

    service = CalculationService(calculate, lambda: "v1", workdir=tmp_path)

    result = service.run({"case_name__0": "service"})

    assert result.succeeded
    assert result.status == "✅ 計算が完了しました。"
    assert result.input_data is not None
    assert result.input_data["case_name"] == "service"
    assert result.log == "engine log\n"
    assert {Path(path).suffix for path in result.files} == {".csv", ".png"}
    assert tuple(Path(path).suffix for path in result.graphs) == (".png",)
    assert (tmp_path / "servicev1.csv").is_file()


def test_service_returns_traceback_on_error(tmp_path: Path) -> None:
    def calculate(input_data: dict[str, object]) -> None:
        print("before failure")
        raise RuntimeError("engine failed")

    service = CalculationService(calculate, lambda: "v1", workdir=tmp_path)

    result = service.run({})

    assert not result.succeeded
    assert result.status == "❌ 計算エラー"
    assert "before failure" in result.log
    assert "RuntimeError: engine failed" in result.log
    assert result.files == ()
    assert result.graphs == ()
