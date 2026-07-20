from __future__ import annotations

import io
import os
import threading
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from verification_core import build_input_data

CalculationFunction = Callable[[dict[str, Any]], Any]
VersionFunction = Callable[[], str]

_GRAPH_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}


@dataclass(frozen=True, slots=True)
class CalculationResult:
    succeeded: bool
    status: str
    input_data: dict[str, Any] | None
    log: str
    files: tuple[str, ...]
    graphs: tuple[str, ...]


class CalculationService:
    def __init__(
        self,
        calculate: CalculationFunction,
        version_info: VersionFunction,
        workdir: Path | None = None,
    ) -> None:
        self._calculate = calculate
        self._version_info = version_info
        self._workdir = workdir
        self._lock = threading.Lock()

    def run(self, values: Mapping[str, Any]) -> CalculationResult:
        input_data: dict[str, Any] | None = None
        output = io.StringIO()
        try:
            input_data = build_input_data(values)
            with self._lock, redirect_stdout(output), redirect_stderr(output):
                workdir = (self._workdir or Path.cwd()).resolve()
                workdir.mkdir(parents=True, exist_ok=True)
                previous_cwd = Path.cwd()
                try:
                    os.chdir(workdir)
                    self._calculate(input_data)
                finally:
                    os.chdir(previous_cwd)
            files = self._result_files(input_data)
            return CalculationResult(
                succeeded=True,
                status="✅ 計算が完了しました。",
                input_data=input_data,
                log=output.getvalue(),
                files=files,
                graphs=tuple(
                    path for path in files if Path(path).suffix.lower() in _GRAPH_SUFFIXES
                ),
            )
        except Exception:
            log = output.getvalue() + traceback.format_exc()
            return CalculationResult(
                succeeded=False,
                status="❌ 計算エラー",
                input_data=input_data,
                log=log,
                files=(),
                graphs=(),
            )

    def _result_files(self, input_data: Mapping[str, Any]) -> tuple[str, ...]:
        prefix = f"{input_data.get('case_name', 'default')}{self._version_info()}"
        root = (self._workdir or Path.cwd()).resolve()
        return tuple(
            str(path.resolve()) for path in sorted(root.glob(prefix + "*")) if path.is_file()
        )
