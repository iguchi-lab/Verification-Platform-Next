from __future__ import annotations

import csv
import io
import math
import os
import shutil
import threading
import time
import traceback
from contextlib import nullcontext, redirect_stderr, redirect_stdout
from dataclasses import dataclass, field, replace
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Callable, ContextManager, Mapping
from uuid import uuid4

from verification_core import build_input_data, load_compatible_input_json

CalculationFunction = Callable[[dict[str, Any]], Any]
VersionFunction = Callable[[], str]
GraphFunction = Callable[[Mapping[str, Any], Path, str, Any | None], tuple[Any, ...]]
RunIdFactory = Callable[[], str]
CsvExportSessionFactory = Callable[[], ContextManager[Any]]

_CALCULATION_CWD_LOCK = threading.Lock()
_MAX_INPUT_JSON_BYTES = 5 * 1024 * 1024


def _captured_dataframe(csv_exports: Any | None, path: Path) -> Any | None:
    if csv_exports is None:
        return None
    dataframe = getattr(csv_exports, "dataframe", None)
    return None if dataframe is None else dataframe(path)


def _pending_csv_count(csv_exports: Any | None) -> int:
    if csv_exports is None:
        return 0
    try:
        return len(csv_exports)
    except TypeError:
        return 0


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
    annual_summary: AnnualSummary | None = None
    csv_status: str = "CSVファイルはまだ出力されていません。"
    csv_exports: Any | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class AnnualMetrics:
    primary_energy_mj: float
    unprocessed_load_mj: float
    air_conditioner_electricity_kwh: float
    fan_electricity_kwh: float


@dataclass(frozen=True, slots=True)
class AnnualSummary:
    heating: AnnualMetrics
    cooling: AnnualMetrics


class CalculationService:
    def __init__(
        self,
        calculate: CalculationFunction,
        version_info: VersionFunction,
        workdir: Path | None = None,
        build_graphs: GraphFunction | None = None,
        result_ttl_seconds: float | None = 24 * 60 * 60,
        run_id_factory: RunIdFactory | None = None,
        csv_export_session: CsvExportSessionFactory | None = None,
    ) -> None:
        self._calculate = calculate
        self._version_info = version_info
        self._workdir = workdir
        self._build_graphs = build_graphs
        self._result_ttl_seconds = result_ttl_seconds
        self._run_id_factory = run_id_factory or (lambda: uuid4().hex)
        self._csv_export_session = csv_export_session

    def run(
        self,
        values: Mapping[str, Any],
        *,
        include_graphs: bool = True,
        prepared_input_data: Mapping[str, Any] | None = None,
        input_source: str = "画面入力",
    ) -> CalculationResult:
        input_data: dict[str, Any] | None = None
        run_id: str | None = None
        artifact_dir: Path | None = None
        csv_exports: Any | None = None
        output = io.StringIO()
        try:
            input_data = (
                dict(prepared_input_data)
                if prepared_input_data is not None
                else build_input_data(values)
            )
            _validate_case_name(input_data.get("case_name", "default"))
            csv_session = (
                self._csv_export_session()
                if self._csv_export_session is not None
                else nullcontext(None)
            )
            with (
                _CALCULATION_CWD_LOCK,
                csv_session as csv_exports,
                redirect_stdout(output),
                redirect_stderr(output),
            ):
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
            annual_summary = self._annual_summary(
                input_data,
                artifact_dir,
                csv_exports,
            )
            pending_csv_count = _pending_csv_count(csv_exports)
            result = CalculationResult(
                succeeded=True,
                status=f"✅ 計算が完了しました。（計算ID: {run_id[:12]}）",
                input_data=input_data,
                run_id=run_id,
                artifact_dir=str(artifact_dir),
                log=_format_success_log(
                    input_data,
                    run_id,
                    self._version_info(),
                    artifact_dir,
                    files,
                    annual_summary,
                    output.getvalue(),
                    pending_csv_count,
                    input_source,
                ),
                files=files,
                graph_status="計算完了後にグラフを表示します。",
                graphs=(),
                annual_summary=annual_summary,
                csv_status=(
                    f"CSVファイルは未出力です（{pending_csv_count}件）。"
                    "必要な場合だけ下のボタンで作成してください。"
                    if pending_csv_count
                    else "CSVファイルは計算時に出力済みです。"
                ),
                csv_exports=csv_exports,
            )
            return self.generate_graphs(result) if include_graphs else result
        except Exception:
            error = traceback.format_exc()
            log = _format_failure_log(
                input_data,
                run_id,
                self._version_info(),
                artifact_dir,
                output.getvalue(),
                error,
            )
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

    def run_uploaded_json(
        self,
        uploaded_file: str | Path | None,
        *,
        include_graphs: bool = True,
    ) -> CalculationResult:
        """Run an input JSON saved by an old or current platform version."""

        try:
            if uploaded_file is None:
                raise ValueError("実行するJSONファイルを選択してください。")
            path = Path(uploaded_file)
            if not path.is_file():
                raise ValueError("選択したJSONファイルを読み取れません。")
            if path.stat().st_size > _MAX_INPUT_JSON_BYTES:
                raise ValueError("入力JSONは5 MB以下にしてください。")
            compatible = load_compatible_input_json(path.read_bytes())
            count = len(compatible.supplemented_paths)
            input_source = (
                "アップロードJSON（不足項目なし）"
                if count == 0
                else f"アップロードJSON（不足していた{count}項目を現行デフォルトで補完）"
            )
            return self.run(
                {},
                include_graphs=include_graphs,
                prepared_input_data=compatible.input_data,
                input_source=input_source,
            )
        except Exception:
            return CalculationResult(
                succeeded=False,
                status="❌ 入力JSONエラー",
                input_data=None,
                run_id=None,
                artifact_dir=None,
                log=_format_failure_log(
                    None,
                    None,
                    self._version_info(),
                    None,
                    "",
                    traceback.format_exc(),
                ),
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
                result.csv_exports,
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
                graph_status="❌ グラフ生成エラー（計算自体は完了しています）",
                graphs=(),
            )

    def export_csv(self, result: CalculationResult) -> CalculationResult:
        """Serialize deferred CSV artifacts for a completed calculation."""
        if not result.succeeded or result.artifact_dir is None:
            return replace(result, csv_status="CSV出力対象の計算結果がありません。")
        if result.csv_exports is None:
            return replace(result, csv_status="CSVファイルはすでに出力されています。")
        try:
            exported = tuple(result.csv_exports.write_all())
            artifact_dir = Path(result.artifact_dir)
            files = self._result_files(result.input_data or {}, artifact_dir)
            return replace(
                result,
                files=files,
                csv_status=f"✅ {len(exported)}件のCSVファイルを出力しました。",
                log=(
                    result.log.rstrip()
                    + "\n\n===== CSV出力 =====\n"
                    + f"{len(exported)}件のCSVファイルを作成しました。\n"
                ),
            )
        except Exception:
            return replace(
                result,
                csv_status="❌ CSVファイルの出力に失敗しました。計算ログを確認してください。",
                log=(
                    result.log.rstrip()
                    + "\n\n===== CSV出力エラー =====\n"
                    + traceback.format_exc()
                ),
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

    def _annual_summary(
        self,
        input_data: Mapping[str, Any],
        artifact_dir: Path,
        csv_exports: Any | None = None,
    ) -> AnnualSummary | None:
        prefix = f"{input_data.get('case_name', 'default')}{self._version_info()}"
        output1_path = artifact_dir / f"{prefix}_output1.csv"
        output2_path = artifact_dir / f"{prefix}_output2.csv"
        try:
            output1_frame = _captured_dataframe(csv_exports, output1_path)
            output2_frame = _captured_dataframe(csv_exports, output2_path)
            if output1_frame is not None and output2_frame is not None:
                if output1_frame.empty or output2_frame.empty:
                    return None
                annual = output1_frame.iloc[0]

                def sum_column(name: str) -> float:
                    return math.fsum(float(value) for value in output2_frame[name])

            else:
                if not output1_path.is_file() or not output2_path.is_file():
                    return None
                with output1_path.open(encoding="cp932", newline="") as file:
                    output1_rows = tuple(csv.DictReader(file))
                if not output1_rows:
                    return None
                annual = output1_rows[0]

                with output2_path.open(encoding="cp932", newline="") as file:
                    hourly = tuple(csv.DictReader(file))
                if not hourly:
                    return None

                def sum_column(name: str) -> float:
                    return math.fsum(float(row[name]) for row in hourly)

            def metrics(suffix: str) -> AnnualMetrics:
                total_electricity = sum_column(f"E_E_{suffix}_d_t [kWh/h]")
                fan_electricity = sum_column(f"E_E_fan_{suffix}_d_t [kWh/h]")
                air_conditioner_electricity = total_electricity - fan_electricity
                if abs(air_conditioner_electricity) < 1e-9:
                    air_conditioner_electricity = 0.0
                return AnnualMetrics(
                    primary_energy_mj=float(annual[f"E_{suffix} [MJ/year]"]),
                    unprocessed_load_mj=sum_column(f"E_UT_{suffix}_d_t [MJ/h]"),
                    air_conditioner_electricity_kwh=air_conditioner_electricity,
                    fan_electricity_kwh=fan_electricity,
                )

            return AnnualSummary(heating=metrics("H"), cooling=metrics("C"))
        except (OSError, KeyError, TypeError, ValueError):
            # The calculation itself succeeded. A missing optional summary must not
            # discard the engine outputs or prevent users from downloading them.
            return None

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


_MODEL_NAMES = {
    1: "ダクト式セントラル空調機",
    2: "RAC活用型全館空調（現行省エネ法RACモデル）",
    3: "RAC活用型全館空調（潜熱評価モデル）",
    4: "電中研モデル",
}


def _format_input_summary(input_data: Mapping[str, Any] | None) -> list[str]:
    if input_data is None:
        return ["入力データの構築前にエラーが発生しました。"]
    heating = input_data.get("H_A")
    cooling = input_data.get("C_A")
    heating = heating if isinstance(heating, Mapping) else {}
    cooling = cooling if isinstance(cooling, Mapping) else {}
    return [
        f"計算条件名: {input_data.get('case_name', 'default')}",
        f"地域区分: {input_data.get('region', '不明')}地域",
        f"暖房方式: {_MODEL_NAMES.get(heating.get('type'), heating.get('type', '不明'))}",
        f"冷房方式: {_MODEL_NAMES.get(cooling.get('type'), cooling.get('type', '不明'))}",
        "暖房VAV / 全般換気: "
        f"{_yes_no(heating.get('VAV'))} / {_yes_no(heating.get('general_ventilation'))}",
        "冷房VAV / 全般換気: "
        f"{_yes_no(cooling.get('VAV'))} / {_yes_no(cooling.get('general_ventilation'))}",
        "床下換気 / 床下空調: "
        f"{_enabled_when_two(input_data.get('underfloor_ventilation'))} / "
        f"{_enabled_when_two(input_data.get('change_underfloor_temperature'))}",
        f"気象データ: {_file_source(input_data.get('climateFile'))}",
        f"暖冷房負荷データ: {_file_source(input_data.get('loadFile'))}",
        f"入力項目数（エンジン入力）: {len(input_data)}",
    ]


def _yes_no(value: object) -> str:
    return "あり" if str(value) == "1" else "なし" if str(value) == "2" else str(value)


def _enabled_when_two(value: object) -> str:
    return "使用する" if str(value) == "2" else "使用しない" if str(value) == "1" else str(value)


def _file_source(value: object) -> str:
    return "標準データを使用" if value in (None, "", "-") else str(value)


def _format_annual_summary(summary: AnnualSummary | None) -> list[str]:
    if summary is None:
        return ["年間集計: 対象のoutput1/output2がないため表示できません。"]
    lines = [
        "注: 一次エネルギー消費量には未処理負荷の一次エネルギー相当分を含みます。",
        "注: エアコンの消費電力量は、熱源機とファンの合計からファン分を除いた値です。",
    ]
    for label, metrics in (("暖房", summary.heating), ("冷房", summary.cooling)):
        lines.extend((
            f"{label} 一次エネルギー消費量: {metrics.primary_energy_mj:,.3f} MJ/年",
            f"{label} 未処理負荷（一次エネルギー相当）: {metrics.unprocessed_load_mj:,.3f} MJ/年",
            f"{label} 消費電力量（エアコン）: {metrics.air_conditioner_electricity_kwh:,.3f} kWh/年",
            f"{label} 消費電力量（ファン）: {metrics.fan_electricity_kwh:,.3f} kWh/年",
        ))
    return lines


def _format_success_log(
    input_data: Mapping[str, Any],
    run_id: str,
    version: str,
    artifact_dir: Path,
    files: tuple[str, ...],
    annual_summary: AnnualSummary | None,
    engine_log: str,
    pending_csv_count: int = 0,
    input_source: str = "画面入力",
) -> str:
    output_step = (
        f"4) 詳細CSV {pending_csv_count}件をメモリに保持（画面のボタンで出力）"
        if pending_csv_count
        else "4) CSV、入力JSON、計算条件マニフェストを計算ID別に保存"
    )
    lines = [
        "===== 1. 計算条件 =====",
        *_format_input_summary(input_data),
        f"計算ID: {run_id[:12]}",
        f"成果物版: {version}",
        "",
        "===== 2. 実行した処理 =====",
        f"1) {input_source}を検証し、計算エンジン用input_dataを準備",
        "2) 暖房・冷房の8760時間計算を順番に実行",
        "3) 一次エネルギー、未処理負荷、機器・ファン電力を集計",
        output_step,
        "",
        "===== 3. 年間結果 =====",
        *_format_annual_summary(annual_summary),
        "",
        "===== 4. 出力 =====",
        f"保存先: {artifact_dir}",
        f"計算時に保存したファイル数: {len(files)}",
        *(f"- {Path(path).name}" for path in files),
        *(
            (
                f"詳細CSV: 未出力（{pending_csv_count}件）",
                "必要な場合は、画面の「CSVファイルを出力」ボタンを押してください。",
            )
            if pending_csv_count
            else ()
        ),
        "",
        "===== 5. 計算エンジン詳細ログ =====",
        "以下は式・分岐・機器能力などを確認するための詳細ログです。",
        engine_log.rstrip() or "（詳細ログの出力はありません）",
        "",
        "===== 計算完了 =====",
        "計算と画面表示用データの準備が正常に終了しました。",
    ]
    return "\n".join(lines) + "\n"


def _format_failure_log(
    input_data: Mapping[str, Any] | None,
    run_id: str | None,
    version: str,
    artifact_dir: Path | None,
    engine_log: str,
    error: str,
) -> str:
    lines = [
        "===== 1. 計算条件 =====",
        *_format_input_summary(input_data),
        f"計算ID: {run_id[:12] if run_id else '未採番'}",
        f"成果物版: {version}",
        "",
        "===== 2. エラー発生位置 =====",
        f"作業フォルダー: {artifact_dir if artifact_dir else '作成前'}",
        "入力変換、8760時間計算、または成果物保存の途中で停止しました。",
        "",
        "===== 3. 停止前の計算エンジンログ =====",
        engine_log.rstrip() or "（停止前の詳細ログはありません）",
        "",
        "===== 4. エラー詳細 =====",
        error.rstrip(),
    ]
    return "\n".join(lines) + "\n"
