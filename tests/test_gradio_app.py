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

    assert gradio.__version__.startswith("6.")
    assert config["title"] == "Verification Platform Next ver.1.0.0"
    assert component_types["accordion"] == 18
    assert component_types["number"] == 158
    assert component_types["dropdown"] == 52
    assert component_types["checkbox"] == 8
    assert component_types["textbox"] == 4  # three text inputs and the log output
    assert component_types["plot"] == 5
    assert component_types["gallery"] == 0

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
    assert len(calculation["inputs"]) == 221
    assert len(calculation["outputs"]) == 6
    assert len(graph_generation["inputs"]) == 1
    assert len(graph_generation["outputs"]) == 7
    assert len(ventilation_visibility["outputs"]) == 2
    assert len(new_underfloor_visibility["outputs"]) == 5
    assert len(underfloor_constants_visibility["outputs"]) == 3
    assert len(heating_visibility["outputs"]) == 72
    assert len(cooling_visibility["outputs"]) == 79


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
