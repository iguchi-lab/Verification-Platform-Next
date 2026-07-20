from collections import Counter

import pytest

gradio = pytest.importorskip("gradio")

from verification_app.form_app import build_app  # noqa: E402
from verification_app.services import CalculationService  # noqa: E402


def test_gradio_app_builds_all_schema_inputs_and_events() -> None:
    service = CalculationService(lambda input_data: None, lambda: "test")

    demo = build_app(service=service)
    config = demo.get_config_file()
    component_types = Counter(component["type"] for component in config["components"])

    assert gradio.__version__.startswith("6.")
    assert component_types["accordion"] == 18
    assert component_types["number"] == 158
    assert component_types["dropdown"] == 52
    assert component_types["checkbox"] == 9
    assert component_types["textbox"] == 4  # three text inputs and the log output

    calculation, heating_visibility, cooling_visibility = config["dependencies"]
    assert len(calculation["inputs"]) == 222
    assert len(calculation["outputs"]) == 5
    assert len(heating_visibility["outputs"]) == 72
    assert len(cooling_visibility["outputs"]) == 79
