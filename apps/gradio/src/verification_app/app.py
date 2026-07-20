from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any

import gradio as gr
import jjjexperiment.main
from jjjexperiment.constants import version_info

_CALCULATION_LOCK = threading.Lock()


def _result_files(input_data: dict[str, Any]) -> list[str]:
    prefix = f"{input_data.get('case_name', 'default')}{version_info()}"
    return [
        str(path.resolve())
        for path in sorted(Path.cwd().glob(prefix + "*"))
        if path.is_file()
    ]


def calculate_json(source: str) -> tuple[str, dict[str, Any] | None, list[str]]:
    try:
        input_data = json.loads(source)
        if not isinstance(input_data, dict):
            raise ValueError("JSONの最上位はオブジェクトにしてください。")
        with _CALCULATION_LOCK:
            jjjexperiment.main.calc(input_data)
        return "✅ 計算が完了しました。", input_data, _result_files(input_data)
    except Exception:
        return "❌ 計算エラー\n\n" + traceback.format_exc(), None, []


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Verification Platform Next") as demo:
        gr.Markdown("# Verification Platform Next")
        gr.Markdown(
            "移行期間用のJSON実行画面です。222項目のフォームは共通スキーマへの移行後に統合します。"
        )
        source = gr.Code(
            value='{"case_name": "default"}',
            language="json",
            label="input_data JSON",
        )
        run = gr.Button("▶ 計算を実行", variant="primary")
        status = gr.Markdown("**状態：未実行**")
        with gr.Tabs():
            with gr.Tab("入力内容"):
                preview = gr.JSON(label="計算に使用した input_data")
            with gr.Tab("出力ファイル", render_children=True):
                files = gr.File(label="計算出力", file_count="multiple", interactive=False)
        run.click(
            calculate_json,
            inputs=source,
            outputs=[status, preview, files],
            concurrency_limit=1,
            concurrency_id="calculation",
            show_progress="full",
        )
    return demo


def main() -> None:
    build_app().queue().launch()


if __name__ == "__main__":
    main()
