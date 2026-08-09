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
    html_values = tuple(
        component["props"].get("value", "")
        for component in config["components"]
        if component["type"] == "html"
    )
    origin_classes = Counter(
        elem_class
        for component in config["components"]
        if component["type"] == "column"
        for elem_class in component["props"].get("elem_classes", ())
    )
    accordions = {
        component["props"]["label"]: component
        for component in config["components"]
        if component["type"] == "accordion"
    }

    def equipment_section(prefix: str) -> dict[str, object]:
        return next(
            component
            for label, component in accordions.items()
            if label.startswith(prefix)
        )

    assert gradio.__version__.startswith("6.")
    assert config["title"] == "Verification Platform Next ver.1.0.2"
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
    assert any(
        "建研Webにある入力" in value
        and "Verification Platformで追加・拡張した入力" in value
        for value in html_values
    )
    assert origin_classes == {
        "input-origin-bri-web": 47,
        "input-origin-verification-platform": 178,
    }
    assert equipment_section("⑦-1")["props"]["visible"] is True
    assert equipment_section("⑧-1")["props"]["visible"] is True
    assert "⑨ 熱交換型換気設備" in accordions
    assert "⑨ 熱交換型換気設備）" not in accordions
    for prefix in ("⑦-2", "⑦-3", "⑦-4", "⑧-2", "⑧-3", "⑧-4"):
        assert equipment_section(prefix)["props"]["visible"] is False

    (
        calculation_started,
        calculation,
        graph_generation,
        ventilation_visibility,
        new_underfloor_visibility,
        underfloor_constants_visibility,
        heating_visibility,
        cooling_visibility,
    ) = config["dependencies"]
    assert calculation_started["queue"] is False
    assert len(calculation_started["inputs"]) == 0
    assert len(calculation_started["outputs"]) == 10
    assert len(calculation["inputs"]) == 225
    assert len(calculation["outputs"]) == 6
    assert len(graph_generation["inputs"]) == 1
    assert len(graph_generation["outputs"]) == 7
    assert len(ventilation_visibility["outputs"]) == 2
    assert len(new_underfloor_visibility["outputs"]) == 5
    assert len(underfloor_constants_visibility["outputs"]) == 3
    assert len(heating_visibility["outputs"]) == 78
    assert len(cooling_visibility["outputs"]) == 83
    heating_section_ids = {
        equipment_section(prefix)["id"] for prefix in ("⑦-1", "⑦-2", "⑦-3", "⑦-4")
    }
    cooling_section_ids = {
        equipment_section(prefix)["id"] for prefix in ("⑧-1", "⑧-2", "⑧-3", "⑧-4")
    }
    assert heating_section_ids <= set(heating_visibility["outputs"])
    assert cooling_section_ids <= set(cooling_visibility["outputs"])


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
    ):
        monkeypatch.delenv(name, raising=False)

    form_app.main()

    assert recorder.queue_options == {"status_update_rate": 1.0}
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

    form_app.main()

    assert recorder.queue_options == {"status_update_rate": 2.5}
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
