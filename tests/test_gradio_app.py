import json
from collections import Counter

import pytest

gradio = pytest.importorskip("gradio")

from verification_app import form_app  # noqa: E402
from verification_app.form_app import build_app  # noqa: E402
from verification_app.services import CalculationService  # noqa: E402


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

    def equipment_section(prefix: str) -> dict[str, object]:
        return next(
            component
            for label, component in accordions.items()
            if label.startswith(prefix)
        )

    assert gradio.__version__.startswith("6.")
    assert config["title"] == "Verification Platform Next ver.1.1.0"
    assert component_types["accordion"] == 16
    assert component_types["number"] == 158
    assert component_types["dropdown"] == 54
    assert component_types["checkbox"] == 10
    assert component_types["textbox"] == 4  # three text inputs and the log output
    assert component_types["plot"] == 5
    assert component_types["gallery"] == 0
    assert any(
        "床下関連設定の入力ガイド" in value
        and "docs/underfloor_ac_input_guide.md" in value
        for value in markdown_values
    )
    assert "## 計算条件" in markdown_values
    assert not any(value.startswith("### ") for value in markdown_values)
    assert group_headings
    assert all(
        "input-group-heading" in component["props"].get("elem_classes", ())
        for component in group_headings
    )
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
    assert "↩ 入力をデフォルトに戻す" in buttons
    assert buttons["↩ 入力をデフォルトに戻す"]["props"]["variant"] == "secondary"
    assert origin_classes == {
        "input-origin-bri-web": 47,
        "input-origin-verification-platform": 178,
    }
    assert equipment_section("⑦-1")["props"]["visible"] is True
    assert equipment_section("⑧-1")["props"]["visible"] is True
    assert "⑨ 熱交換型換気設備" in accordions
    assert "⑨ 熱交換型換気設備）" not in accordions
    assert all(
        "input-section" in component["props"].get("elem_classes", ())
        for component in accordions.values()
    )
    for prefix in ("⑦-2", "⑦-3", "⑦-4", "⑧-2", "⑧-3", "⑧-4"):
        assert equipment_section(prefix)["props"]["visible"] is False

    dependencies = config["dependencies"]
    calculation_started, calculation, graph_generation = dependencies[:3]
    reset_inputs = next(
        dependency for dependency in dependencies if len(dependency["outputs"]) == 233
    )
    install_default_highlights = next(
        dependency
        for dependency in dependencies
        if "defaultHighlightBound" in (dependency.get("js") or "")
    )
    visibility_dependencies = tuple(
        dependency
        for dependency in dependencies[3:]
        if dependency not in (reset_inputs, install_default_highlights)
    )
    assert calculation_started["queue"] is False
    assert len(calculation_started["inputs"]) == 0
    assert len(calculation_started["outputs"]) == 10
    assert len(calculation["inputs"]) == 225
    assert len(calculation["outputs"]) == 6
    assert len(graph_generation["inputs"]) == 1
    assert len(graph_generation["outputs"]) == 7
    assert len(visibility_dependencies) >= 14
    assert 2 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    assert 5 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    assert 78 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    assert 83 in {len(dependency["outputs"]) for dependency in visibility_dependencies}
    assert len(reset_inputs["inputs"]) == 0
    assert len(reset_inputs["outputs"]) == 233
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
    assert tuple(update["value"] for update in reset_outputs[:225]) == tuple(
        field.default for field in model.schema.fields
    )
    assert tuple(update["visible"] for update in reset_outputs[:225]) == tuple(
        field.visible for field in model.fields
    )
    assert [update["visible"] for update in reset_outputs[-8:]] == [
        True,
        False,
        False,
        False,
        True,
        False,
        False,
        False,
    ]
    heating_section_ids = {
        equipment_section(prefix)["id"] for prefix in ("⑦-1", "⑦-2", "⑦-3", "⑦-4")
    }
    cooling_section_ids = {
        equipment_section(prefix)["id"] for prefix in ("⑧-1", "⑧-2", "⑧-3", "⑧-4")
    }
    assert any(
        heating_section_ids <= set(dependency["outputs"])
        for dependency in visibility_dependencies
    )
    assert any(
        cooling_section_ids <= set(dependency["outputs"])
        for dependency in visibility_dependencies
    )
    assert "先行計算がある場合は、順番に実行します" in (
        form_app._calculation_started_outputs()[0]
    )


def test_highlight_javascript_uses_schema_defaults_and_field_dom_ids() -> None:
    fields = form_app.load_form_model().schema.fields[:2]
    field_dom_ids = {
        field.key: f"test-field-{index}" for index, field in enumerate(fields)
    }

    modified_js = form_app._install_default_highlight_js(fields, field_dom_ids)
    reset_js = form_app._reset_highlight_js(fields, field_dom_ids)

    assert json.dumps([field.default for field in fields], ensure_ascii=True) in modified_js
    assert "test-field-0" in modified_js
    assert 'typeof defaultValue !== "number"' in modified_js
    assert "const numericValue = Number(value);" in modified_js
    assert "JSON.stringify(normalizedValue)" in modified_js
    assert 'classList.toggle("input-value-modified", changed)' in modified_js
    assert 'container.classList.remove("input-value-modified")' in modified_js
    assert "MutationObserver" in modified_js
    assert "test-field-1" in reset_js
    assert 'classList.remove("input-value-modified")' in reset_js


def test_modified_input_highlight_uses_a_strong_green_treatment() -> None:
    assert "color-mix(in srgb, #16a34a 22%, transparent)" in form_app._INPUT_ORIGIN_CSS
    assert "box-shadow: inset 0 0 0 2px #16a34a" in form_app._INPUT_ORIGIN_CSS


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
