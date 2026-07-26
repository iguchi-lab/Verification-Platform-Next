from __future__ import annotations

import io
import os
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from verification_core import build_input_data

CalculationFunction = Callable[[dict[str, Any]], Any]
VersionFunction = Callable[[], str]
GraphFunction = Callable[[Mapping[str, Any], Path, str], tuple[Any, ...]]

_CALCULATION_CWD_LOCK = threading.Lock()


@dataclass(frozen=True, slots=True)
class CalculationResult:
    succeeded: bool
    status: str
    input_data: dict[str, Any] | None
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
    ) -> None:
        self._calculate = calculate
        self._version_info = version_info
        self._workdir = workdir
        self._build_graphs = build_graphs

    def run(
        self,
        values: Mapping[str, Any],
        *,
        include_graphs: bool = True,
    ) -> CalculationResult:
        input_data: dict[str, Any] | None = None
        output = io.StringIO()
        try:
            input_data = build_input_data(values)
            with _CALCULATION_CWD_LOCK, redirect_stdout(output), redirect_stderr(output):
                workdir = (self._workdir or Path.cwd()).resolve()
                workdir.mkdir(parents=True, exist_ok=True)
                previous_cwd = Path.cwd()
                try:
                    os.chdir(workdir)
                    self._calculate(input_data)
                finally:
                    os.chdir(previous_cwd)
            files = self._result_files(input_data)
            result = CalculationResult(
                succeeded=True,
                status="✅ 計算が完了しました。",
                input_data=input_data,
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
                status="❌ 計算エラー",
                input_data=input_data,
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
            graphs = self._build_graphs(
                result.input_data,
                (self._workdir or Path.cwd()).resolve(),
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

    def _result_files(self, input_data: Mapping[str, Any]) -> tuple[str, ...]:
        prefix = f"{input_data.get('case_name', 'default')}{self._version_info()}"
        root = (self._workdir or Path.cwd()).resolve()
        return tuple(
            str(path.resolve()) for path in sorted(root.glob(prefix + "*")) if path.is_file()
        )
