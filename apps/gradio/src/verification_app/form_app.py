from __future__ import annotations

import os
import time
from collections.abc import Iterable
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import gradio as gr
from jjjexperiment.release import DISPLAY_VERSION
from verification_core import FieldDefinition, FieldKind

from .form_model import FormField, FormModel, load_form_model
from .graphs import GRAPH_LABELS
from .services import CalculationResult, CalculationService

_UNDERFLOOR_INPUT_GUIDE_URL = (
    "https://github.com/iguchi-lab/Verification-Platform-Next/"
    "blob/main/docs/underfloor_ac_input_guide.md"
)


def build_app(
    service: CalculationService | None = None,
    model: FormModel | None = None,
) -> gr.Blocks:
    form = model or load_form_model()
    calculation_service = service or _default_service()

    with gr.Blocks(
        title=f"Verification Platform Next {DISPLAY_VERSION}",
        fill_width=True,
    ) as demo:
        gr.Markdown(f"# Verification Platform Next {DISPLAY_VERSION}")
        gr.Markdown(f"共通入力スキーマから生成した {len(form.fields)} 項目の計算フォームです。")

        components: dict[str, Any] = {}
        containers: dict[str, Any] = {}
        for section_index, section in enumerate(form.sections):
            with gr.Accordion(
                section.name,
                open=section_index == 0,
                key=f"section:{section_index}",
            ):
                if section.name == "⑥ その他":
                    gr.Markdown(
                        "📘 床下関係の方式選択、推奨値、入力例は"
                        f"[床下関連設定の入力ガイド]({_UNDERFLOOR_INPUT_GUIDE_URL})"
                        "を参照してください。"
                    )
                for group_index, group in enumerate(section.groups):
                    gr.Markdown(f"### {group.name}")
                    for row_index, row_fields in enumerate(_chunks(group.fields, 3)):
                        with gr.Row(key=f"row:{section_index}:{group_index}:{row_index}"):
                            for form_field in row_fields:
                                with gr.Column(
                                    visible=form_field.visible,
                                    min_width=280,
                                    key=f"field-container:{form_field.key}",
                                ) as container:
                                    component = _input_component(form_field.definition)
                                components[form_field.key] = component
                                containers[form_field.key] = container

        run = gr.Button("▶ 計算を実行", variant="primary", size="lg")
        status = gr.Markdown("**状態: 未実行**")
        result_state = gr.State()
        with gr.Tabs():
            with gr.Tab("計算入力"):
                preview = gr.JSON(label="計算に使用した input_data")
            with gr.Tab("計算ログ"):
                log = gr.Textbox(
                    label="標準出力・エラー",
                    lines=16,
                    interactive=False,
                )
            with gr.Tab("グラフ"):
                graph_status = gr.Markdown("計算完了後にグラフを表示します。")
                graphs = [gr.Plot(label=label) for label in GRAPH_LABELS]
            with gr.Tab("出力ファイル", render_children=True):
                files = gr.File(
                    label="計算出力",
                    file_count="multiple",
                    interactive=False,
                )

        ordered_components = [components[field.key] for field in form.schema.fields]

        def calculate(*raw_values: Any) -> tuple[Any, ...]:
            values = form.values_from_sequence(raw_values)
            result = calculation_service.run(values, include_graphs=False)
            return _calculation_outputs(result)

        def generate_graphs(result: CalculationResult | None) -> tuple[Any, ...]:
            if result is None:
                return _graph_outputs(None)
            return _graph_outputs(calculation_service.generate_graphs(result))

        calculation_started = run.click(
            _calculation_started_outputs,
            outputs=[status, preview, log, graph_status, *graphs, files],
            queue=False,
            api_visibility="private",
        )
        calculation_finished = calculation_started.then(
            calculate,
            inputs=ordered_components,
            outputs=[result_state, status, preview, log, graph_status, files],
            concurrency_limit=1,
            concurrency_id="calculation",
            show_progress="full",
        )
        calculation_finished.then(
            generate_graphs,
            inputs=result_state,
            outputs=[graph_status, log, *graphs],
            concurrency_limit=1,
            concurrency_id="calculation",
            show_progress="full",
        )

        conditional_fields = tuple(
            field for field in form.schema.fields if field.enabled_when is not None
        )
        control_keys = tuple(dict.fromkeys(
            field.enabled_when.path[0] for field in conditional_fields
        ))
        control_inputs = [components[key] for key in control_keys]

        for control_key in control_keys:
            affected_fields = _visibility_descendants(
                form.schema.fields,
                control_key,
            )

            def update_visibility(
                *selected: Any,
                fields: tuple[FieldDefinition, ...] = affected_fields,
            ) -> tuple[Any, ...]:
                values = form.schema.defaults()
                values.update(zip(control_keys, selected, strict=True))
                visibility = form.visibility(values)
                return tuple(
                    gr.Column(visible=visibility[field.key])
                    for field in fields
                )

            components[control_key].change(
                update_visibility,
                inputs=control_inputs,
                outputs=[containers[field.key] for field in affected_fields],
                queue=False,
                api_visibility="private",
            )
    return demo


def _visibility_descendants(
    fields: tuple[FieldDefinition, ...],
    control_key: str,
) -> tuple[FieldDefinition, ...]:
    controls = {control_key}
    descendants: list[FieldDefinition] = []
    while True:
        added = tuple(
            field
            for field in fields
            if field not in descendants
            and field.enabled_when is not None
            and field.enabled_when.path[0] in controls
        )
        if not added:
            return tuple(descendants)
        descendants.extend(added)
        controls.update(field.key for field in added)


def _input_component(field: FieldDefinition) -> Any:
    common = {
        "label": field.label,
        "value": field.default,
        "info": field.description or None,
        "key": f"field:{field.key}",
    }
    if field.kind is FieldKind.TEXT:
        return gr.Textbox(**common)
    if field.kind in {FieldKind.NUMBER, FieldKind.INTEGER}:
        return gr.Number(**common)
    if field.kind is FieldKind.BOOLEAN:
        return gr.Checkbox(**common)
    if field.kind is FieldKind.SELECT:
        return gr.Dropdown(
            choices=list(field.choices),
            allow_custom_value=False,
            **common,
        )
    raise ValueError(f"Unsupported field kind: {field.kind}")


def _chunks(values: tuple[FormField, ...], size: int) -> Iterable[tuple[FormField, ...]]:
    iterator = iter(values)
    while chunk := tuple(islice(iterator, size)):
        yield chunk


def _calculation_started_outputs() -> tuple[Any, ...]:
    return (
        "⏳ 計算を実行しています。",
        None,
        "",
        "計算完了後にグラフを生成します。",
        *((None,) * len(GRAPH_LABELS)),
        [],
    )


def _calculation_outputs(result: CalculationResult) -> tuple[Any, ...]:
    graph_status = (
        "⏳ 計算結果と出力ファイルを表示しました。グラフを生成しています。"
        if result.succeeded
        else result.graph_status
    )
    return (
        result,
        result.status,
        result.input_data,
        result.log,
        graph_status,
        list(result.files),
    )


def _graph_outputs(result: CalculationResult | None) -> tuple[Any, ...]:
    if result is None:
        return (
            "グラフ生成対象の計算結果がありません。",
            "",
            *((None,) * len(GRAPH_LABELS)),
        )
    graphs = tuple(result.graphs[: len(GRAPH_LABELS)])
    graphs += (None,) * (len(GRAPH_LABELS) - len(graphs))
    return (
        result.graph_status,
        result.log,
        *graphs,
    )


def _default_service() -> CalculationService:
    import jjjexperiment.main
    from jjjexperiment.constants import version_info

    from .graphs import build_result_graphs

    output_dir = Path(os.environ.get("VERIFICATION_OUTPUT_DIR", "outputs"))
    return CalculationService(
        jjjexperiment.main.calc,
        version_info,
        workdir=output_dir,
        build_graphs=build_result_graphs,
    )


def main() -> None:
    running_in_colab = "COLAB_RELEASE_TAG" in os.environ
    share = _environment_flag("GRADIO_SHARE", default=running_in_colab)
    server_name = os.environ.get(
        "GRADIO_SERVER_NAME",
        "0.0.0.0" if running_in_colab else "127.0.0.1",
    )
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    debug = _environment_flag("GRADIO_DEBUG", default=running_in_colab)
    show_error = _environment_flag("GRADIO_SHOW_ERROR", default=True)
    status_update_rate = float(os.environ.get("GRADIO_STATUS_UPDATE_RATE", "1"))
    launch_options = {
        "share": share,
        "server_name": server_name,
        "server_port": server_port,
        "debug": debug,
        "show_error": show_error,
    }
    if not share:
        build_app().queue(status_update_rate=status_update_rate).launch(
            **launch_options,
        )
        return

    max_attempts = int(os.environ.get("GRADIO_SHARE_MAX_ATTEMPTS", "3"))
    health_timeout = float(os.environ.get("GRADIO_SHARE_HEALTH_TIMEOUT", "15"))
    share_launch_options = {**launch_options, "debug": False}
    for attempt in range(1, max_attempts + 1):
        demo = build_app().queue(status_update_rate=status_update_rate)
        demo.launch(**share_launch_options, prevent_thread_lock=True)
        share_url = demo.share_url
        if share_url and _share_url_is_healthy(share_url, health_timeout):
            print(f"Gradio Share health check passed: {share_url}")
            demo.block_thread()
            return

        print(
            "Gradio Share health check failed; "
            f"recreating tunnel ({attempt}/{max_attempts})."
        )
        demo.close()
        if attempt < max_attempts:
            time.sleep(1)

    raise RuntimeError(
        f"Gradio Share remained unavailable after {max_attempts} attempts."
    )


def _share_url_is_healthy(share_url: str, timeout: float) -> bool:
    try:
        with urlopen(f"{share_url.rstrip('/')}/config", timeout=timeout) as response:
            return response.status == 200
    except (OSError, TimeoutError):
        return False


def _environment_flag(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    main()
