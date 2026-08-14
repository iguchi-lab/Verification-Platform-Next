from __future__ import annotations

import json
import os
import time
from collections.abc import Iterable
from html import escape
from itertools import islice
from pathlib import Path
from typing import Any
from urllib.request import urlopen

import gradio as gr
from jjjexperiment.release import DISPLAY_VERSION
from verification_core import FieldDefinition, FieldKind, FieldOrigin

from .form_model import FormField, FormModel, load_form_model
from .graphs import GRAPH_LABELS
from .services import AnnualMetrics, AnnualSummary, CalculationResult, CalculationService

_UNDERFLOOR_INPUT_GUIDE_URL = (
    "https://github.com/iguchi-lab/Verification-Platform-Next/"
    "blob/main/docs/underfloor_ac_input_guide.md"
)

_INPUT_ORIGIN_CSS = """
.input-origin-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  margin: 0.25rem 0 1rem;
}
.input-origin-legend__item {
  align-items: center;
  display: inline-flex;
  font-weight: 600;
  gap: 0.45rem;
}
.input-origin-legend__swatch {
  border-radius: 999px;
  display: inline-block;
  height: 0.8rem;
  width: 0.8rem;
}
.input-origin-legend__swatch--bri { background: #2563eb; }
.input-origin-legend__swatch--vp { background: #f59e0b; }
.input-origin-legend__swatch--modified { background: #22c55e; }
.input-origin-bri-web,
.input-origin-verification-platform {
  border-radius: 0.4rem;
  padding-left: 0.65rem !important;
}
div.block.input-origin-bri-web {
  box-shadow: inset 4px 0 0 #2563eb !important;
}
div.block.input-origin-verification-platform {
  background: color-mix(in srgb, #f59e0b 7%, transparent) !important;
  box-shadow: inset 4px 0 0 #f59e0b !important;
}
div.block.input-value-modified {
  background: color-mix(in srgb, #16a34a 22%, transparent) !important;
  box-shadow: inset 0 0 0 2px #16a34a !important;
}
.default-reset-row {
  align-items: center;
  margin: 0 0 0.75rem;
}
.default-reset-note p {
  color: var(--body-text-color-subdued);
  margin: 0 !important;
}
.input-section {
  overflow-x: clip !important;
}
.input-section > button > span:not(.icon) {
  font-size: 1.125rem !important;
  font-weight: 700 !important;
  line-height: 1.45 !important;
}
.input-group-heading h2 {
  font-size: 1rem !important;
  font-weight: 600 !important;
  line-height: 1.45 !important;
  margin: 0.65rem 0 0.2rem !important;
}
.input-section-description p,
.input-group-heading p {
  color: var(--body-text-color-subdued);
  font-size: 0.88rem !important;
  line-height: 1.55 !important;
}
.input-section-description p {
  margin: 0 0 0.75rem !important;
}
.input-group-heading p {
  margin: 0 0 0.45rem !important;
}
.annual-summary {
  margin: 0.85rem 0 1rem;
}
.annual-summary__title {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0 0 0.7rem;
}
.annual-summary__note {
  color: var(--body-text-color-subdued);
  font-size: 0.85rem;
  line-height: 1.55;
  margin: -0.35rem 0 0.8rem;
}
.annual-summary__seasons {
  display: grid;
  gap: 0.9rem;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}
.annual-summary__season {
  background: var(--block-background-fill);
  border: 1px solid var(--border-color-primary);
  border-radius: 0.65rem;
  padding: 1rem;
}
.annual-summary__season--heating { border-top: 5px solid #ef4444; }
.annual-summary__season--cooling { border-top: 5px solid #2563eb; }
.annual-summary__season h3 {
  font-size: 1.3rem;
  margin: 0 0 0.75rem;
}
.annual-summary__metrics {
  display: grid;
  gap: 0.65rem;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.annual-summary__metric {
  background: var(--background-fill-secondary);
  border-radius: 0.45rem;
  padding: 0.7rem;
}
.annual-summary__label {
  color: var(--body-text-color-subdued);
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
}
.annual-summary__value {
  display: block;
  font-size: 1.4rem;
  font-weight: 750;
  line-height: 1.3;
  margin-top: 0.15rem;
}
.annual-summary__unit {
  font-size: 0.82rem;
  font-weight: 500;
  white-space: nowrap;
}
@media (max-width: 700px) {
  .annual-summary__metrics { grid-template-columns: 1fr; }
}
"""


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
        gr.HTML(
            f"<style>{_INPUT_ORIGIN_CSS}</style>"
            '<div class="input-origin-legend">'
            '<span class="input-origin-legend__item">'
            '<span class="input-origin-legend__swatch '
            'input-origin-legend__swatch--bri"></span>'
            "建研Webにある入力"
            "</span>"
            '<span class="input-origin-legend__item">'
            '<span class="input-origin-legend__swatch '
            'input-origin-legend__swatch--vp"></span>'
            "Verification Platformで追加・拡張した入力"
            "</span>"
            '<span class="input-origin-legend__item">'
            '<span class="input-origin-legend__swatch '
            'input-origin-legend__swatch--modified"></span>'
            "デフォルトから変更した入力"
            "</span>"
            "</div>"
        )

        with gr.Row(elem_classes=["default-reset-row"]):
            reset = gr.Button(
                "↩ 入力をデフォルトに戻す",
                variant="secondary",
                size="sm",
                scale=0,
            )
            gr.Markdown(
                "変更した項目は濃い緑色で表示されます。",
                elem_classes=["default-reset-note"],
            )

        components: dict[str, Any] = {}
        containers: dict[str, Any] = {}
        field_dom_ids: dict[str, str] = {}
        section_containers: dict[str, Any] = {}
        section_dom_ids: dict[str, str] = {}
        group_targets: list[tuple[str, tuple[FieldDefinition, ...]]] = []
        section_fields = {
            section.name: tuple(
                form_field.definition
                for group in section.groups
                for form_field in group.fields
            )
            for section in form.sections
        }
        for section_index, section in enumerate(form.sections):
            section_dom_id = f"input-section-{section_index}"
            with gr.Accordion(
                section.name,
                open=False,
                visible=_section_is_visible(section.name, section_fields, {
                    field.key: field.visible for field in form.fields
                }),
                key=f"section:{section_index}",
                elem_id=section_dom_id,
                elem_classes=["input-section"],
            ) as section_container:
                section_containers[section.name] = section_container
                section_dom_ids[section.name] = section_dom_id
                if section.description:
                    gr.Markdown(
                        section.description,
                        elem_classes=["input-section-description"],
                    )
                if section.name == "④ 床下・空気搬送":
                    gr.Markdown(
                        "📘 床下関係の方式選択、推奨値、入力例は"
                        f"[床下関連設定の入力ガイド]({_UNDERFLOOR_INPUT_GUIDE_URL})"
                        "を参照してください。"
                    )
                for group_index, group in enumerate(section.groups):
                    group_dom_id = f"input-group-heading-{section_index}-{group_index}"
                    group_fields = tuple(
                        form_field.definition for form_field in group.fields
                    )
                    gr.Markdown(
                        f"## {group.name}"
                        + (f"\n\n{group.description}" if group.description else ""),
                        elem_id=group_dom_id,
                        elem_classes=["input-group-heading"],
                    )
                    group_targets.append((group_dom_id, group_fields))
                    for row_index, row_fields in enumerate(_chunks(group.fields, 3)):
                        with gr.Row(key=f"row:{section_index}:{group_index}:{row_index}"):
                            for form_field in row_fields:
                                field_dom_id = f"input-field-container-{len(components)}"
                                component = _input_component(
                                    form_field.definition,
                                    label=form_field.label,
                                    description=form_field.description,
                                    choices=form_field.choices,
                                    visible=form_field.visible,
                                    min_width=280,
                                    elem_id=field_dom_id,
                                    elem_classes=[
                                        _origin_css_class(form_field.definition.origin)
                                    ],
                                )
                                components[form_field.key] = component
                                containers[form_field.key] = component
                                field_dom_ids[form_field.key] = field_dom_id

        run = gr.Button("▶ 計算を実行", variant="primary", size="lg")
        status = gr.Markdown("**状態: 未実行**")
        annual_summary = gr.HTML(
            value="",
            visible=False,
            elem_classes=["annual-summary"],
        )
        result_state = gr.State()
        with gr.Tabs():
            with gr.Tab("計算入力"):
                preview = gr.JSON(label="計算に使用した input_data")
            with gr.Tab("計算ログ"):
                log = gr.Textbox(
                    label="計算の内容・年間結果・計算エンジン詳細ログ",
                    lines=28,
                    interactive=False,
                )
            with gr.Tab("グラフ"):
                graph_status = gr.Markdown("計算完了後にグラフを表示します。")
                graphs = [gr.Plot(label=label) for label in GRAPH_LABELS]
            with gr.Tab("出力ファイル", render_children=True):
                csv_status = gr.Markdown(
                    "計算完了後、必要な場合だけCSVファイルを出力できます。"
                )
                export_csv_button = gr.Button(
                    "CSVファイルを出力",
                    interactive=False,
                )
                files = gr.File(
                    label="ダウンロード可能な計算出力",
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

        def export_csv_files(
            result: CalculationResult | None,
        ) -> tuple[Any, ...]:
            if result is None:
                return (
                    None,
                    "CSV出力対象の計算結果がありません。",
                    gr.update(interactive=False),
                    [],
                    "",
                )
            exported = calculation_service.export_csv(result)
            return (
                exported,
                exported.csv_status,
                gr.update(interactive=exported.csv_status.startswith("❌")),
                list(exported.files),
                exported.log,
            )

        calculation_started = run.click(
            _calculation_started_outputs,
            outputs=[
                status,
                annual_summary,
                preview,
                log,
                graph_status,
                *graphs,
                csv_status,
                export_csv_button,
                files,
            ],
            queue=False,
            api_visibility="private",
        )
        calculation_finished = calculation_started.then(
            calculate,
            inputs=ordered_components,
            outputs=[
                result_state,
                status,
                annual_summary,
                preview,
                log,
                graph_status,
                csv_status,
                export_csv_button,
                files,
            ],
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
        export_csv_button.click(
            export_csv_files,
            inputs=result_state,
            outputs=[
                result_state,
                csv_status,
                export_csv_button,
                files,
                log,
            ],
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
            affected_sections = tuple(
                section_name
                for section_name in section_containers
                if _is_equipment_section(section_name)
                and any(
                    field.section == section_name for field in affected_fields
                )
            )

            def update_visibility(
                *selected: Any,
                fields: tuple[FieldDefinition, ...] = affected_fields,
                sections: tuple[str, ...] = affected_sections,
            ) -> Any:
                values = form.schema.defaults()
                values.update(zip(control_keys, selected, strict=True))
                visibility = form.visibility(values)
                field_updates = tuple(
                    gr.update(visible=visibility[field.key])
                    for field in fields
                )
                section_updates = tuple(
                    gr.update(
                        visible=_section_is_visible(
                            section_name,
                            section_fields,
                            visibility,
                        )
                    )
                    for section_name in sections
                )
                updates = (*field_updates, *section_updates)
                return updates[0] if len(updates) == 1 else updates

            components[control_key].change(
                update_visibility,
                inputs=control_inputs,
                outputs=[
                    *(containers[field.key] for field in affected_fields),
                    *(section_containers[name] for name in affected_sections),
                ],
                queue=False,
                api_visibility="private",
            )

        ordered_fields = tuple(form.schema.fields)
        equipment_section_names = tuple(
            name for name in section_containers if _is_equipment_section(name)
        )

        def reset_inputs() -> tuple[Any, ...]:
            visibility = form.visibility(form.schema.defaults())
            field_updates = tuple(
                gr.update(
                    value=field.default,
                    visible=visibility[field.key],
                )
                for field in ordered_fields
            )
            section_updates = tuple(
                gr.update(
                    visible=_section_is_visible(
                        section_name,
                        section_fields,
                        visibility,
                    )
                )
                for section_name in equipment_section_names
            )
            return (*field_updates, *section_updates)

        reset.click(
            reset_inputs,
            outputs=[
                *ordered_components,
                *(section_containers[name] for name in equipment_section_names),
            ],
            queue=False,
            api_visibility="private",
            js=_reset_highlight_js(
                ordered_fields,
                field_dom_ids,
                form.visibility(form.schema.defaults()),
                equipment_section_names,
                section_fields,
                section_dom_ids,
                tuple(group_targets),
            ),
        )

        demo.load(
            fn=None,
            queue=False,
            api_visibility="private",
            show_progress="hidden",
            js=_install_default_highlight_js(
                ordered_fields,
                field_dom_ids,
                control_keys,
                equipment_section_names,
                section_fields,
                section_dom_ids,
                tuple(group_targets),
            ),
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


def _is_equipment_section(section_name: str) -> bool:
    return section_name.startswith(("⑦-", "⑧-"))


def _section_is_visible(
    section_name: str,
    section_fields: dict[str, tuple[FieldDefinition, ...]],
    visibility: dict[str, bool],
) -> bool:
    if not _is_equipment_section(section_name):
        return True
    return any(visibility[field.key] for field in section_fields[section_name])


def _input_component(
    field: FieldDefinition,
    *,
    label: str | None = None,
    description: str | None = None,
    choices: tuple[Any, ...] | None = None,
    visible: bool = True,
    min_width: int | None = None,
    elem_id: str | None = None,
    elem_classes: list[str] | None = None,
) -> Any:
    common = {
        "label": label or field.label,
        "value": field.default,
        "info": description if description is not None else field.description or None,
        "key": f"field:{field.key}",
        "visible": visible,
        "min_width": min_width,
        "elem_id": elem_id,
        "elem_classes": elem_classes,
    }
    if field.kind is FieldKind.TEXT:
        return gr.Textbox(**common)
    if field.kind in {FieldKind.NUMBER, FieldKind.INTEGER}:
        return gr.Number(**common)
    if field.kind is FieldKind.BOOLEAN:
        return gr.Checkbox(**common)
    if field.kind is FieldKind.SELECT:
        return gr.Dropdown(
            choices=list(choices if choices is not None else field.choices),
            allow_custom_value=False,
            **common,
        )
    raise ValueError(f"Unsupported field kind: {field.kind}")


def _origin_css_class(origin: FieldOrigin) -> str:
    return f"input-origin-{origin.value.replace('_', '-')}"


def _install_default_highlight_js(
    fields: tuple[FieldDefinition, ...],
    field_dom_ids: dict[str, str],
    control_keys: tuple[str, ...] = (),
    equipment_section_names: tuple[str, ...] = (),
    section_fields: dict[str, tuple[FieldDefinition, ...]] | None = None,
    section_dom_ids: dict[str, str] | None = None,
    group_targets: tuple[tuple[str, tuple[FieldDefinition, ...]], ...] = (),
) -> str:
    defaults = json.dumps([field.default for field in fields], ensure_ascii=True)
    field_keys = json.dumps([field.key for field in fields])
    dom_ids = json.dumps([field_dom_ids[field.key] for field in fields])
    kinds = json.dumps([field.kind.value for field in fields])
    control_keys_json = json.dumps(control_keys)
    conditions = json.dumps({
        field.key: {
            "controller": field.enabled_when.path[0],
            "allowed": list(field.enabled_when.allowed_values),
        }
        for field in fields
        if field.enabled_when is not None
    }, ensure_ascii=True)
    section_fields = section_fields or {}
    section_dom_ids = section_dom_ids or {}
    section_targets = json.dumps([
        {
            "domId": section_dom_ids[section_name],
            "fieldKeys": [field.key for field in section_fields[section_name]],
        }
        for section_name in equipment_section_names
    ])
    group_targets_json = json.dumps([
        {
            "domId": dom_id,
            "fieldKeys": [field.key for field in group_fields],
        }
        for dom_id, group_fields in group_targets
    ])
    return f"""
() => {{
  const defaults = {defaults};
  const fieldKeys = {field_keys};
  const domIds = {dom_ids};
  const kinds = {kinds};
  const controlKeys = {control_keys_json};
  const conditions = {conditions};
  const sectionTargets = {section_targets};
  const groupTargets = {group_targets_json};
  const fieldIndexes = Object.fromEntries(fieldKeys.map((key, index) => [key, index]));
  const readValue = (container, kind) => {{
    if (kind === "boolean") {{
      return container.querySelector('input[type="checkbox"]')?.checked;
    }}
    const input = container.querySelector('textarea, input:not([type="hidden"])');
    if (!input) return undefined;
    if (kind === "number" || kind === "integer") {{
      return input.value === "" ? null : Number(input.value);
    }}
    return input.value;
  }};
  const normalizeValue = (value, defaultValue) => {{
    if (value === null || typeof defaultValue !== "number") return value;
    const numericValue = Number(value);
    return Number.isNaN(numericValue) ? value : numericValue;
  }};
  const update = (container, index) => {{
    const value = readValue(container, kinds[index]);
    if (value === undefined) return;
    const normalizedValue = normalizeValue(value, defaults[index]);
    const changed = JSON.stringify(normalizedValue) !== JSON.stringify(defaults[index]);
    container.classList.toggle("input-value-modified", changed);
  }};
  const setVisible = (container, visible) => {{
    if (!container) return;
    if (visible) container.style.removeProperty("display");
    else container.style.setProperty("display", "none", "important");
  }};
  const reconcileVisibility = () => {{
    const values = Object.fromEntries(controlKeys.map((key) => {{
      const index = fieldIndexes[key];
      const container = document.getElementById(domIds[index]);
      const value = container ? readValue(container, kinds[index]) : undefined;
      return [key, value ?? defaults[index]];
    }}));
    const visibility = {{}};
    const isVisible = (key) => {{
      if (key in visibility) return visibility[key];
      const condition = conditions[key];
      if (!condition) return true;
      const controllerVisible = isVisible(condition.controller);
      const selectedValue = values[condition.controller];
      const allowed = condition.allowed.some(
        (value) => JSON.stringify(value) === JSON.stringify(selectedValue),
      );
      visibility[key] = controllerVisible && allowed;
      return visibility[key];
    }};
    Object.keys(conditions).forEach((key) => {{
      const index = fieldIndexes[key];
      setVisible(document.getElementById(domIds[index]), isVisible(key));
    }});
    sectionTargets.forEach((section) => {{
      setVisible(
        document.getElementById(section.domId),
        section.fieldKeys.some((key) => isVisible(key)),
      );
    }});
    groupTargets.forEach((group) => {{
      setVisible(
        document.getElementById(group.domId),
        group.fieldKeys.some((key) => isVisible(key)),
      );
    }});
  }};
  const bindAll = () => domIds.forEach((domId, index) => {{
    const container = document.getElementById(domIds[index]);
    if (!container) return;
    if (container.dataset.defaultHighlightBound !== "true") {{
      container.dataset.defaultHighlightBound = "true";
      container.addEventListener("input", () => {{
        update(container, index);
        reconcileVisibility();
      }});
      container.addEventListener("change", () => {{
        update(container, index);
        reconcileVisibility();
      }});
      container.classList.remove("input-value-modified");
    }}
  }});
  const reconcileAll = () => domIds.forEach((domId, index) => {{
    const container = document.getElementById(domId);
    if (container) update(container, index);
  }});
  bindAll();
  window.__verificationDefaultHighlightObserver?.disconnect();
  window.__verificationDefaultHighlightObserver = new MutationObserver(() => {{
    bindAll();
    reconcileAll();
    reconcileVisibility();
  }});
  window.__verificationDefaultHighlightObserver.observe(document.body, {{
    childList: true,
    subtree: true,
  }});
  requestAnimationFrame(() => requestAnimationFrame(() => {{
    reconcileAll();
    reconcileVisibility();
  }}));
  return [];
}}
"""


def _reset_highlight_js(
    fields: tuple[FieldDefinition, ...],
    field_dom_ids: dict[str, str],
    visibility: dict[str, bool] | None = None,
    equipment_section_names: tuple[str, ...] = (),
    section_fields: dict[str, tuple[FieldDefinition, ...]] | None = None,
    section_dom_ids: dict[str, str] | None = None,
    group_targets: tuple[tuple[str, tuple[FieldDefinition, ...]], ...] = (),
) -> str:
    dom_ids = json.dumps([field_dom_ids[field.key] for field in fields])
    visible_fields = json.dumps(
        [visibility[field.key] for field in fields]
        if visibility is not None
        else [True] * len(fields)
    )
    section_fields = section_fields or {}
    section_dom_ids = section_dom_ids or {}
    section_targets = json.dumps([
        {
            "domId": section_dom_ids[section_name],
            "visible": any(
                visibility[field.key] for field in section_fields[section_name]
            ),
        }
        for section_name in equipment_section_names
    ])
    group_visibility = json.dumps([
        {
            "domId": dom_id,
            "visible": any(
                visibility[field.key] for field in group_fields
            ) if visibility is not None else True,
        }
        for dom_id, group_fields in group_targets
    ])
    return f"""
() => {{
  const domIds = {dom_ids};
  const visibleFields = {visible_fields};
  const sectionTargets = {section_targets};
  const groupVisibility = {group_visibility};
  const setVisible = (container, visible) => {{
    if (!container) return;
    if (visible) container.style.removeProperty("display");
    else container.style.setProperty("display", "none", "important");
  }};
  domIds.forEach((domId, index) => {{
    const container = document.getElementById(domId);
    container?.classList.remove("input-value-modified");
    setVisible(container, visibleFields[index]);
  }});
  sectionTargets.forEach((section) => {{
    setVisible(document.getElementById(section.domId), section.visible);
  }});
  groupVisibility.forEach((group) => {{
    setVisible(document.getElementById(group.domId), group.visible);
  }});
  return [];
}}
"""


def _chunks(values: tuple[FormField, ...], size: int) -> Iterable[tuple[FormField, ...]]:
    iterator = iter(values)
    while chunk := tuple(islice(iterator, size)):
        yield chunk


def _calculation_started_outputs() -> tuple[Any, ...]:
    return (
        "⏳ 計算要求を受け付けました。先行計算がある場合は、順番に実行します。"
        "画面を閉じずにお待ちください。",
        gr.update(value="", visible=False),
        None,
        "",
        "計算完了後にグラフを生成します。",
        *((None,) * len(GRAPH_LABELS)),
        "計算中です。CSVファイルはまだ出力できません。",
        gr.update(interactive=False),
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
        gr.update(
            value=_annual_summary_html(result.annual_summary),
            visible=result.succeeded and result.annual_summary is not None,
        ),
        result.input_data,
        result.log,
        graph_status,
        result.csv_status,
        gr.update(
            interactive=result.succeeded and result.csv_exports is not None,
        ),
        list(result.files),
    )


def _annual_summary_html(summary: AnnualSummary | None) -> str:
    if summary is None:
        return ""

    def metric(label: str, value: float, unit: str) -> str:
        return (
            '<div class="annual-summary__metric">'
            f'<span class="annual-summary__label">{escape(label)}</span>'
            f'<span class="annual-summary__value">{value:,.1f} '
            f'<span class="annual-summary__unit">{escape(unit)}</span></span>'
            "</div>"
        )

    def season(label: str, css_name: str, values: AnnualMetrics) -> str:
        return (
            f'<section class="annual-summary__season annual-summary__season--{css_name}">'
            f"<h3>{escape(label)}</h3>"
            '<div class="annual-summary__metrics">'
            + metric("一次エネルギー消費量", values.primary_energy_mj, "MJ/年")
            + metric(
                "未処理負荷（一次エネルギー相当）",
                values.unprocessed_load_mj,
                "MJ/年",
            )
            + metric(
                "消費電力量（エアコン）",
                values.air_conditioner_electricity_kwh,
                "kWh/年",
            )
            + metric(
                "消費電力量（ファン）",
                values.fan_electricity_kwh,
                "kWh/年",
            )
            + "</div></section>"
        )

    return (
        '<div class="annual-summary">'
        '<div class="annual-summary__title">年間計算結果</div>'
        '<div class="annual-summary__note">'
        '一次エネルギー消費量には未処理負荷の一次エネルギー相当分を含みます。'
        'エアコンの消費電力量は、熱源機とファンの合計からファン分を除いた値です。'
        "</div>"
        '<div class="annual-summary__seasons">'
        + season("暖房", "heating", summary.heating)
        + season("冷房", "cooling", summary.cooling)
        + "</div></div>"
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
    from jjjexperiment.csv_artifacts import capture_csv_exports

    from .graphs import build_result_graphs

    output_dir = Path(os.environ.get("VERIFICATION_OUTPUT_DIR", "outputs"))
    result_ttl_seconds = float(
        os.environ.get("VERIFICATION_RESULT_TTL_SECONDS", str(24 * 60 * 60))
    )
    return CalculationService(
        jjjexperiment.main.calc,
        version_info,
        workdir=output_dir,
        build_graphs=build_result_graphs,
        result_ttl_seconds=(result_ttl_seconds if result_ttl_seconds > 0 else None),
        csv_export_session=capture_csv_exports,
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
    queue_max_size_value = int(os.environ.get("GRADIO_QUEUE_MAX_SIZE", "5"))
    queue_options = {
        "status_update_rate": status_update_rate,
        "max_size": queue_max_size_value if queue_max_size_value > 0 else None,
        "default_concurrency_limit": 1,
    }
    launch_options = {
        "share": share,
        "server_name": server_name,
        "server_port": server_port,
        "debug": debug,
        "show_error": show_error,
    }
    if not share:
        build_app().queue(**queue_options).launch(
            **launch_options,
        )
        return

    max_attempts = int(os.environ.get("GRADIO_SHARE_MAX_ATTEMPTS", "3"))
    health_timeout = float(os.environ.get("GRADIO_SHARE_HEALTH_TIMEOUT", "15"))
    share_launch_options = {**launch_options, "debug": False}
    for attempt in range(1, max_attempts + 1):
        demo = build_app().queue(**queue_options)
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
