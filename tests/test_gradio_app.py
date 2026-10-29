import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pytest

gradio = pytest.importorskip("gradio")

from verification_app import form_app  # noqa: E402
from verification_app.form_app import build_app  # noqa: E402
from verification_app.services import (  # noqa: E402
    AnnualMetrics,
    AnnualSummary,
    CalculationService,
    PeakValue,
)


def test_bulk_download_selection_export_and_recalculation(tmp_path: Path) -> None:
    import pandas as pd
    from jjjexperiment.csv_artifacts import capture_csv_exports, write_dataframe_csv

    def calculate(data):
        Path("bundlev1_input.json").write_text("{}", encoding="utf-8")
        write_dataframe_csv(pd.DataFrame({"value": [1]}), "bundlev1.csv")

    service = CalculationService(
        calculate, lambda: "v1", workdir=tmp_path,
        csv_export_session=capture_csv_exports,
    )
    demo = build_app(service=service)
    callbacks = {
        getattr(block.fn, "__name__", ""): block.fn for block in demo.fns.values()
        if block.fn is not None
    }
    result = service.run({"case_name__0": "bundle"}, include_graphs=False)
    assert result.succeeded
    assert callbacks["select_all_files"](result) == ["bundlev1_input.json"]
    exported = callbacks["export_csv_files"](result)
    result = exported[0]
    assert set(exported[5]["choices"]) == {"bundlev1.csv", "bundlev1_input.json"}
    selection = callbacks["select_all_files"](result)
    assert set(selection) == set(exported[5]["value"])
    message, archive = callbacks["build_download_archive"](result, ["bundlev1.csv"])
    assert "1件" in message
    with ZipFile(archive["value"]) as bundle:
        assert bundle.namelist() == ["bundlev1.csv"]
    cleared = callbacks["reset_archive"]([])
    assert cleared[0]["interactive"] is False
    assert cleared[2]["value"] is None and cleared[2]["visible"] is False
    started = form_app._calculation_started_outputs()
    assert started[-5]["choices"] == []
    assert started[-2]["value"] is None
    assert started[-1] is None  # previous calculation state is discarded
    message, archive = callbacks["build_download_archive"](None, selection)
    assert archive["visible"] is False
    assert "計算完了後" in message


def test_gradio_app_builds_all_schema_inputs_and_events() -> None:
    service = CalculationService(lambda input_data: None, lambda: "test")

    demo = build_app(service=service)
    config = demo.get_config_file()
    component_types = Counter(component["type"] for component in config["components"])
    markdown_values = tuple(
        component["props"].get("value", "")
        for component in config["components"]
        if component["type"] == "markdown"
    )
    group_headings = tuple(
        component
        for component in config["components"]
        if component["type"] == "markdown"
        and component["props"].get("value", "").startswith("## ")
    )
    html_values = tuple(
        component["props"].get("value", "")
        for component in config["components"]
        if component["type"] == "html"
    )
    origin_classes = Counter(
        elem_class
        for component in config["components"]
        for elem_class in component["props"].get("elem_classes", ())
        if elem_class.startswith("input-origin-")
    )
    accordions = {
        component["props"]["label"]: component
        for component in config["components"]
        if component["type"] == "accordion"
    }
    buttons = {
        component["props"].get("value", ""): component
        for component in config["components"]
        if component["type"] == "button"
    }
    components_by_key = {
        component["props"].get("key"): component
        for component in config["components"]
        if isinstance(component["props"].get("key"), str)
    }

    method = components_by_key["field:calculation_method__0"]["props"]
    assert method["choices"] == [("自立", "next"), ("TG", "tg")]
    assert method["value"] == "next"

    def descendants(node):
        yield node["id"]
        for child in node.get("children", ()):
            yield from descendants(child)

    def find_node(node, component_id):
        if node["id"] == component_id:
            return node
        for child in node.get("children", ()):
            found = find_node(child, component_id)
            if found is not None:
                return found
        return None

    expected_sections = {
        "calculation_method__0": "① 計算条件・外部データ",
        "tg_q_rtd_H__0": "⑤ 暖房設備",
        "tg_q_rtd_C__0": "⑥ 冷房設備",
        "tg_rac_class__0": "⑤ 暖房設備",
        "tg_fan_exponent__0": "⑤ 暖房設備",
        "tg_profile__0": "⑧ 詳細設定・比較検証",
    }
    for key, section in expected_sections.items():
        section_node = find_node(config["layout"], accordions[section]["id"])
        assert components_by_key[f"field:{key}"]["id"] in set(descendants(section_node))
    assert components_by_key["field:tg_profile__0"]["props"]["choices"][0] == (
        "標準計算（従来のTG総合・ダクト／RAC）", "standard",
    )

    assert gradio.__version__.startswith("6.")
    assert config["title"] == "Verification Platform Next ver.1.8.0"
    assert component_types["accordion"] == 9
    assert component_types["number"] == 158
    assert component_types["dropdown"] == 59
    assert component_types["checkbox"] == 11
    assert component_types["textbox"] == 4  # three text inputs and the log output
    assert component_types["plot"] == 5
    assert component_types["html"] == 2
    assert component_types["gallery"] == 0
    assert any(
        "床下関連設定の入力ガイド" in value
        and "docs/underfloor_ac_input_guide.md" in value
        for value in markdown_values
    )
    assert any(value.startswith("## 計算条件") for value in markdown_values)
    assert any(
        "建研Webプログラムの「基本情報」に対応" in value
        for value in markdown_values
    )
    assert not any(value.startswith("### ") for value in markdown_values)
    assert group_headings
    assert all(
        "input-group-heading" in component["props"].get("elem_classes", ())
        for component in group_headings
    )
    group_heading_ids = tuple(
        component["props"].get("elem_id") for component in group_headings
    )
    assert all(
        elem_id is not None and elem_id.startswith("input-group-heading-")
        for elem_id in group_heading_ids
    )
    assert len(group_heading_ids) == len(set(group_heading_ids))
    assert any(
        "建研Webにある入力" in value
        and "Verification Platformで追加・拡張した入力" in value
        and ".input-section {\n  overflow-x: clip !important;" in value
        and ".input-section > button > span:not(.icon)" in value
        and ".input-value-modified" in value
        and "デフォルトから変更した入力" in value
        for value in html_values
    )
    assert "変更した項目は濃い緑色で表示されます。" in markdown_values
    manual_constants = components_by_key["field:input_ufac_consts__0"]
    assert "不易層温度は外気温8760時間値の年間平均から自動算定" in (
        manual_constants["props"]["info"]
    )
    assert "床下から室への熱移動用を2.223" in manual_constants["props"]["info"]
    assert "field:Theta_g_avg__0" not in components_by_key
    assert "field:U_s_vert__0" not in components_by_key
    assert "↩ 入力をデフォルトに戻す" in buttons
    assert buttons["↩ 入力をデフォルトに戻す"]["props"]["variant"] == "secondary"
    assert "CSVファイルを出力" in buttons
    assert buttons["CSVファイルを出力"]["props"]["interactive"] is False
    assert "JSONファイルをアップロードして計算" in buttons
    assert component_types["file"] == 3
    assert component_types["checkboxgroup"] == 1
    assert "全選択" in buttons
    assert "全解除" in buttons
    assert buttons["選択したファイルをZIPにまとめる"]["props"]["interactive"] is False
    assert any(
        "旧Verification Platformまたは現在の画面で保存した入力JSON" in value
        and "現在のデフォルト値で補完" in value
        for value in markdown_values
    )
    assert origin_classes == {
        "input-origin-bri-web": 45,
        "input-origin-verification-platform": 186,
    }
    assert tuple(accordions) == (
        "JSONファイルの読込み",
        "① 計算条件・外部データ",
        "② 住宅基本情報",
        "③ 外皮性能",
        "④ 床下・空気搬送",
        "⑤ 暖房設備",
        "⑥ 冷房設備",
        "⑦ 熱交換型換気設備",
        "⑧ 詳細設定・比較検証",
    )
    input_accordions = tuple(
        component for label, component in accordions.items() if label[0].isdigit()
    )
    assert all(
        "input-section" in component["props"].get("elem_classes", ())
        for component in input_accordions
    )
    assert accordions["① 計算条件・外部データ"]["props"]["open"] is True
    assert all(
        component["props"]["open"] is False
        for label, component in accordions.items() if label != "① 計算条件・外部データ"
    )
    assert all(component["props"]["visible"] is True for component in accordions.values())

    dependencies = config["dependencies"]
    calculation_started, calculation, graph_generation, csv_export = dependencies[:4]
    reset_inputs = next(
        dependency
        for dependency in dependencies
        if len(dependency["outputs"]) == 231 and dependency.get("js")
    )
    install_default_highlights = next(
        dependency
        for dependency in dependencies
        if "defaultHighlightBound" in (dependency.get("js") or "")
    )
    visibility_dependencies = tuple(
        dependency
        for dependency in dependencies[4:]
        if dependency not in (reset_inputs, install_default_highlights)
    )
    assert calculation_started["queue"] is False
    assert len(calculation_started["inputs"]) == 0
    assert len(calculation_started["outputs"]) == 18
    assert len(calculation["inputs"]) == 231
    assert len(calculation["outputs"]) == 13
    assert len(graph_generation["inputs"]) == 1
    assert len(graph_generation["outputs"]) == 7
    assert len(csv_export["inputs"]) == 1
    assert len(csv_export["outputs"]) == 9
    assert len(visibility_dependencies) >= 14
    assert 2 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    assert 3 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    for season in ("H", "C"):
        control_id = components_by_key[f"field:{season}_A_type__0"]["id"]
        required_outputs = {
            components_by_key[f"field:tg_q_rtd_{season}__0"]["id"],
            components_by_key["field:tg_rac_class__0"]["id"],
        }
        assert any(
            (control_id, "change") in dependency["targets"]
            and required_outputs.issubset(dependency["outputs"])
            for dependency in visibility_dependencies
        )
    assert len(reset_inputs["inputs"]) == 0
    assert len(reset_inputs["outputs"]) == 231
    assert len(install_default_highlights["inputs"]) == 0
    assert len(install_default_highlights["outputs"]) == 0
    assert install_default_highlights["queue"] is False
    assert "input-value-modified" in install_default_highlights["js"]
    reset_function = next(
        block_fn.fn
        for block_fn in demo.fns.values()
        if getattr(block_fn.fn, "__name__", "") == "reset_inputs"
    )
    reset_outputs = reset_function()
    model = form_app.load_form_model()
    assert tuple(update["value"] for update in reset_outputs[:len(form_app.load_form_model().fields)]) == tuple(
        field.default for field in model.schema.fields
    )
    assert tuple(update["visible"] for update in reset_outputs[:len(form_app.load_form_model().fields)]) == tuple(
        field.visible for field in model.fields
    )
    assert "先行計算がある場合は、順番に実行します" in (
        form_app._calculation_started_outputs()[0]
    )
    assert form_app._calculation_started_outputs()[1]["visible"] is False


@pytest.mark.parametrize("method", ["next", "tg"])
def test_annual_summary_html_shows_heating_and_cooling_metrics(method: str) -> None:
    summary = AnnualSummary(
        heating=AnnualMetrics(100.0, 2.0, 30.0, 4.0, PeakValue(6.75, "01/20 06:00")),
        cooling=AnnualMetrics(200.0, 5.0, 60.0, 7.0),
        calculation_method=method,
        fan_ventilation_mj=40.0 if method == "tg" else None,
        chapter5_ventilation_mj=50.0 if method == "tg" else None,
        tg_total_mj=390.0 if method == "tg" else None,
    )

    html = form_app._annual_summary_html(summary)

    assert f"年間計算結果（{'自立' if method == 'next' else 'TG'}方式）" in html
    assert "一次エネルギー消費量には未処理負荷" in html
    assert "暖房" in html
    assert "冷房" in html
    assert "一次エネルギー消費量" in html
    assert "未処理負荷（一次エネルギー相当）" in html
    assert "消費電力量（エアコン）" in html
    assert "消費電力量（ファン）" in html
    assert "100.0" in html
    assert "200.0" in html
    total_html = html.split('annual-summary__season--total">', 1)[1].split("</section>", 1)[0]
    assert "暖冷房合計" in total_html
    assert "300.0" in total_html
    assert "7.0" in total_html
    assert "90.0" in total_html
    assert "11.0" in total_html
    assert "6.75" in html and "01/20 06:00" in html
    assert html.count("ピーク負荷（建物全体）") == 2
    assert "ピーク" not in total_html
    assert "データなし" in html
    assert html.index("<h3>冷房</h3>") < html.index("<h3>暖冷房合計</h3>")
    if method == "tg":
        assert "390.0" not in total_html
        assert html.index("<h3>暖冷房合計</h3>") < html.index("TG比較合計")


def test_highlight_javascript_uses_schema_defaults_and_field_dom_ids() -> None:
    model = form_app.load_form_model()
    fields = model.schema.fields
    field_dom_ids = {
        field.key: f"test-field-{index}" for index, field in enumerate(fields)
    }
    section_fields = {
        section.name: tuple(
            field.definition
            for group in section.groups
            for field in group.fields
        )
        for section in model.sections
    }
    section_dom_ids = {
        section.name: f"test-section-{index}"
        for index, section in enumerate(model.sections)
    }
    control_keys = tuple(dict.fromkeys(
        field.enabled_when.path[0]
        for field in fields
        if field.enabled_when is not None
    ))
    hidden_group = next(
        group
        for section in model.sections
        for group in section.groups
        if group.fields and not any(field.visible for field in group.fields)
    )
    group_targets = ((
        "test-hidden-group",
        tuple(field.definition for field in hidden_group.fields),
    ),)
    visibility = {field.definition.key: field.visible for field in model.fields}

    modified_js = form_app._install_default_highlight_js(
        fields,
        field_dom_ids,
        control_keys,
        (model.sections[6].name,),
        section_fields,
        section_dom_ids,
        group_targets,
    )
    reset_js = form_app._reset_highlight_js(
        fields,
        field_dom_ids,
        visibility,
        (model.sections[6].name,),
        section_fields,
        section_dom_ids,
        group_targets,
    )

    assert json.dumps([field.default for field in fields], ensure_ascii=True) in modified_js
    assert "test-field-0" in modified_js
    assert 'typeof defaultValue !== "number"' in modified_js
    assert "const numericValue = Number(value);" in modified_js
    assert "JSON.stringify(normalizedValue)" in modified_js
    assert 'classList.toggle("input-value-modified", changed)' in modified_js
    assert 'container.classList.remove("input-value-modified")' in modified_js
    assert "const reconcileAll" in modified_js
    assert "const reconcileVisibility" in modified_js
    assert 'style.setProperty("display", "none", "important")' in modified_js
    assert "H_A_q_hs_rtd_H1__0" in modified_js
    assert "H_A_q_hs_mid_H1__0" in modified_js
    assert "requestAnimationFrame(() => requestAnimationFrame" in modified_js
    assert "MutationObserver" in modified_js
    assert "const groupTargets" in modified_js
    assert "test-hidden-group" in modified_js
    assert "group.fieldKeys.some((key) => isVisible(key))" in modified_js
    assert "test-field-1" in reset_js
    assert 'classList.remove("input-value-modified")' in reset_js
    assert 'style.setProperty("display", "none", "important")' in reset_js
    assert "const groupVisibility" in reset_js
    assert '"domId": "test-hidden-group", "visible": false' in reset_js


def test_modified_input_highlight_uses_a_strong_green_treatment() -> None:
    assert "div.block.input-value-modified" in form_app._INPUT_ORIGIN_CSS
    assert "color-mix(in srgb, #16a34a 22%, transparent)" in form_app._INPUT_ORIGIN_CSS
    assert "box-shadow: inset 0 0 0 2px #16a34a" in form_app._INPUT_ORIGIN_CSS


def test_input_origin_colors_remain_distinct_on_gradio_components() -> None:
    assert "div.block.input-origin-bri-web" in form_app._INPUT_ORIGIN_CSS
    assert "div.block.input-origin-verification-platform" in form_app._INPUT_ORIGIN_CSS
    assert "box-shadow: inset 4px 0 0 #2563eb !important" in form_app._INPUT_ORIGIN_CSS
    assert "box-shadow: inset 4px 0 0 #f59e0b !important" in form_app._INPUT_ORIGIN_CSS
    assert (
        "background: color-mix(in srgb, #f59e0b 7%, transparent) !important"
        in form_app._INPUT_ORIGIN_CSS
    )


class _LaunchRecorder:
    def __init__(self) -> None:
        self.queue_options: dict[str, object] | None = None
        self.launch_options: dict[str, object] | None = None
        self.share_url = "https://healthy.gradio.live"
        self.blocked = False
        self.closed = False

    def queue(self, **options: object) -> "_LaunchRecorder":
        self.queue_options = options
        return self

    def launch(self, **options: object) -> None:
        self.launch_options = options

    def block_thread(self) -> None:
        self.blocked = True

    def close(self) -> None:
        self.closed = True


def test_colab_launch_uses_publicly_reachable_server_and_debugging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _LaunchRecorder()
    monkeypatch.setattr(form_app, "build_app", lambda: recorder)
    monkeypatch.setattr(form_app, "_share_url_is_healthy", lambda *_: True)
    monkeypatch.setenv("COLAB_RELEASE_TAG", "release")
    for name in (
        "GRADIO_SHARE",
        "GRADIO_SERVER_NAME",
        "GRADIO_SERVER_PORT",
        "GRADIO_DEBUG",
        "GRADIO_SHOW_ERROR",
        "GRADIO_STATUS_UPDATE_RATE",
        "GRADIO_QUEUE_MAX_SIZE",
    ):
        monkeypatch.delenv(name, raising=False)

    form_app.main()

    assert recorder.queue_options == {
        "status_update_rate": 1.0,
        "max_size": 5,
        "default_concurrency_limit": 1,
    }
    assert recorder.launch_options == {
        "share": True,
        "server_name": "0.0.0.0",
        "server_port": 7860,
        "debug": False,
        "show_error": True,
        "prevent_thread_lock": True,
    }
    assert recorder.blocked


def test_launch_environment_overrides_are_respected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _LaunchRecorder()
    monkeypatch.setattr(form_app, "build_app", lambda: recorder)
    monkeypatch.setattr(form_app, "_share_url_is_healthy", lambda *_: True)
    monkeypatch.delenv("COLAB_RELEASE_TAG", raising=False)
    monkeypatch.setenv("GRADIO_SHARE", "yes")
    monkeypatch.setenv("GRADIO_SERVER_NAME", "localhost")
    monkeypatch.setenv("GRADIO_SERVER_PORT", "7861")
    monkeypatch.setenv("GRADIO_DEBUG", "on")
    monkeypatch.setenv("GRADIO_SHOW_ERROR", "0")
    monkeypatch.setenv("GRADIO_STATUS_UPDATE_RATE", "2.5")
    monkeypatch.setenv("GRADIO_QUEUE_MAX_SIZE", "9")

    form_app.main()

    assert recorder.queue_options == {
        "status_update_rate": 2.5,
        "max_size": 9,
        "default_concurrency_limit": 1,
    }
    assert recorder.launch_options == {
        "share": True,
        "server_name": "localhost",
        "server_port": 7861,
        "debug": False,
        "show_error": False,
        "prevent_thread_lock": True,
    }
    assert recorder.blocked


def test_share_launch_retries_an_unhealthy_tunnel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorders = [_LaunchRecorder(), _LaunchRecorder()]
    health_results = iter((False, True))
    monkeypatch.setattr(form_app, "build_app", lambda: recorders.pop(0))
    monkeypatch.setattr(
        form_app,
        "_share_url_is_healthy",
        lambda *_: next(health_results),
    )
    monkeypatch.setattr(form_app.time, "sleep", lambda _: None)
    monkeypatch.setenv("GRADIO_SHARE", "1")
    monkeypatch.setenv("GRADIO_SHARE_MAX_ATTEMPTS", "2")

    first, second = recorders
    form_app.main()

    assert first.closed
    assert not first.blocked
    assert second.blocked
    assert not second.closed
