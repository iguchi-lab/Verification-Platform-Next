from __future__ import annotations

import os
from itertools import islice
from pathlib import Path
from typing import Any, Iterable

import gradio as gr
from verification_core import FieldDefinition, FieldKind

from .form_model import FormField, FormModel, load_form_model
from .services import CalculationResult, CalculationService

_TYPE_CONTROLS = ("H_A_type__0", "C_A_type__0")


def build_app(
    service: CalculationService | None = None,
    model: FormModel | None = None,
) -> gr.Blocks:
    form = model or load_form_model()
    calculation_service = service or _default_service()

    with gr.Blocks(
        title="Verification Platform Next",
        fill_width=True,
    ) as demo:
        gr.Markdown("# Verification Platform Next")
        gr.Markdown(f"共通入力スキーマから生成した {len(form.fields)} 項目の計算フォームです。")

        components: dict[str, Any] = {}
        containers: dict[str, Any] = {}
        for section_index, section in enumerate(form.sections):
            with gr.Accordion(
                section.name,
                open=section_index == 0,
                key=f"section:{section_index}",
            ):
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
                graphs = gr.Gallery(
                    label="生成されたグラフ",
                    columns=2,
                    object_fit="contain",
                )
            with gr.Tab("出力ファイル", render_children=True):
                files = gr.File(
                    label="計算出力",
                    file_count="multiple",
                    interactive=False,
                )

        ordered_components = [components[field.key] for field in form.schema.fields]

        def calculate(*raw_values: Any) -> tuple[Any, ...]:
            values = form.values_from_sequence(raw_values)
            return _result_outputs(calculation_service.run(values))

        run.click(
            calculate,
            inputs=ordered_components,
            outputs=[status, preview, log, graphs, files],
            concurrency_limit=1,
            concurrency_id="calculation",
            show_progress="full",
        )

        for control_key in _TYPE_CONTROLS:
            dependent_fields = tuple(
                field
                for field in form.schema.fields
                if field.enabled_when is not None and field.enabled_when.path == (control_key,)
            )
            if not dependent_fields:
                continue

            def update_visibility(
                selected: Any,
                *,
                key: str = control_key,
                fields: tuple[FieldDefinition, ...] = dependent_fields,
            ) -> tuple[Any, ...]:
                values = form.schema.defaults()
                values[key] = selected
                visibility = form.visibility(values)
                return tuple(gr.Column(visible=visibility[field.key]) for field in fields)

            components[control_key].change(
                update_visibility,
                inputs=components[control_key],
                outputs=[containers[field.key] for field in dependent_fields],
                queue=False,
                api_visibility="private",
            )
    return demo


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


def _result_outputs(result: CalculationResult) -> tuple[Any, ...]:
    return (
        result.status,
        result.input_data,
        result.log,
        list(result.graphs),
        list(result.files),
    )


def _default_service() -> CalculationService:
    import jjjexperiment.main
    from jjjexperiment.constants import version_info

    output_dir = Path(os.environ.get("VERIFICATION_OUTPUT_DIR", "outputs"))
    return CalculationService(jjjexperiment.main.calc, version_info, workdir=output_dir)


def main() -> None:
    share = os.environ.get("GRADIO_SHARE", "").lower() in {"1", "true", "yes"}
    server_name = os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    build_app().queue().launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
