from __future__ import annotations

import io
import os
import shutil
import threading
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Callable, Mapping
from uuid import uuid4

from verification_core import build_input_data

CalculationFunction = Callable[[dict[str, Any]], Any]
VersionFunction = Callable[[], str]
GraphFunction = Callable[[Mapping[str, Any], Path, str], tuple[Any, ...]]
RunIdFactory = Callable[[], str]

_CALCULATION_CWD_LOCK = threading.Lock()


@dataclass(frozen=True, slots=True)
class CalculationResult:
    succeeded: bool
    status: str
    input_data: dict[str, Any] | None
    run_id: str | None
    artifact_dir: str | None
    log: str
    files: tuple[str, ...]
    graph_status: str
    graphs: tuple[Any, ...]


class CalculationService:
    def __init__(
        self,
        calculate: CalculationFunction,
        version_info: VersionFunction,
        workdir: Path | None = None,
        build_graphs: GraphFunction | None = None,
        result_ttl_seconds: float | None = 24 * 60 * 60,
        run_id_factory: RunIdFactory | None = None,
    ) -> None:
        self._calculate = calculate
        self._version_info = version_info
        self._workdir = workdir
        self._build_graphs = build_graphs
        self._result_ttl_seconds = result_ttl_seconds
        self._run_id_factory = run_id_factory or (lambda: uuid4().hex)

    def run(
        self,
        values: Mapping[str, Any],
        *,
        include_graphs: bool = True,
    ) -> CalculationResult:
        input_data: dict[str, Any] | None = None
        run_id: str | None = None
        artifact_dir: Path | None = None
        output = io.StringIO()
        try:
            input_data = build_input_data(values)
            _validate_case_name(input_data.get("case_name", "default"))
            with _CALCULATION_CWD_LOCK, redirect_stdout(output), redirect_stderr(output):
                output_root = (self._workdir or Path.cwd()).resolve()
                output_root.mkdir(parents=True, exist_ok=True)
                self._remove_expired_results(output_root)
                run_id, artifact_dir = self._create_artifact_dir(output_root)
                previous_cwd = Path.cwd()
                try:
                    os.chdir(artifact_dir)
                    self._calculate(input_data)
                finally:
                    os.chdir(previous_cwd)
            if run_id is None or artifact_dir is None:
                raise RuntimeError("Calculation directory was not initialized")
            files = self._result_files(input_data, artifact_dir)
            result = CalculationResult(
                succeeded=True,
                status=f"✅ 計算が完了しました。（計算ID: {run_id[:12]}）",
                input_data=input_data,
                run_id=run_id,
                artifact_dir=str(artifact_dir),
                log=output.getvalue(),
                files=files,
                graph_status="計算完了後にグラフを表示します。",
                graphs=(),
            )
            return self.generate_graphs(result) if include_graphs else result
        except Exception:
            log = output.getvalue() + traceback.format_exc()
            return CalculationResult(
                succeeded=False,
                status=(
                    f"❌ 計算エラー（計算ID: {run_id[:12]}）"
                    if run_id is not None
                    else "❌ 計算エラー"
                ),
                input_data=input_data,
                run_id=run_id,
                artifact_dir=str(artifact_dir) if artifact_dir is not None else None,
                log=log,
                files=(),
                graph_status="計算完了後にグラフを表示します。",
                graphs=(),
            )

    def generate_graphs(self, result: CalculationResult) -> CalculationResult:
        if not result.succeeded or result.input_data is None:
            return result
        if self._build_graphs is None:
            return replace(result, graph_status="グラフ生成は設定されていません。")
        try:
            artifact_dir = (
                Path(result.artifact_dir)
                if result.artifact_dir is not None
                else (self._workdir or Path.cwd()).resolve()
            )
            graphs = self._build_graphs(
                result.input_data,
                artifact_dir,
                self._version_info(),
            )
            return replace(
                result,
                graph_status=f"✅ {len(graphs)}件のグラフを生成しました。",
                graphs=graphs,
            )
        except Exception:
            log = result.log + "\n===== グラフ生成エラー =====\n" + traceback.format_exc()
            return replace(
                result,
                log=log,
                graph_status="❌ グラフ生成エラー（計算結果CSVは正常に作成されています）",
                graphs=(),
            )

    def _result_files(
        self,
        input_data: Mapping[str, Any],
        artifact_dir: Path,
    ) -> tuple[str, ...]:
        prefix = f"{input_data.get('case_name', 'default')}{self._version_info()}"
        return tuple(
            str(path.resolve())
            for path in sorted(artifact_dir.glob(prefix + "*"))
            if path.is_file()
        )

    def _create_artifact_dir(self, output_root: Path) -> tuple[str, Path]:
        for _ in range(10):
            run_id = self._run_id_factory()
            if (
                not run_id
                or not run_id.isascii()
                or any(not (character.isalnum() or character in "-_") for character in run_id)
            ):
                raise ValueError("Calculation run ID must be an ASCII identifier")
            artifact_dir = output_root / f"run-{run_id}"
            try:
                artifact_dir.mkdir()
            except FileExistsError:
                continue
            return run_id, artifact_dir
        raise RuntimeError("Could not allocate a unique calculation directory")

    def _remove_expired_results(self, output_root: Path) -> None:
        if self._result_ttl_seconds is None:
            return
        cutoff = time.time() - self._result_ttl_seconds
        for artifact_dir in output_root.glob("run-*"):
            try:
                if artifact_dir.is_dir() and artifact_dir.stat().st_mtime < cutoff:
                    shutil.rmtree(artifact_dir)
            except OSError:
                # Cleanup is best effort and must not prevent a calculation.
                continue


def _validate_case_name(value: object) -> None:
    case_name = str(value)
    if (
        not case_name
        or case_name in {".", ".."}
        or "\x00" in case_name
        or PurePosixPath(case_name).name != case_name
        or PureWindowsPath(case_name).name != case_name
    ):
        raise ValueError("計算条件名にパスとして解釈される文字は使用できません。")
