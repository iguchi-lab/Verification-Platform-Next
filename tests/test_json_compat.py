import json
from pathlib import Path

import pytest

from verification_core import (
    build_input_data,
    load_compatible_input_json,
    load_legacy_inventory,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_current_json_is_loaded_without_supplementation() -> None:
    current = build_input_data({})

    loaded = load_compatible_input_json(json.dumps(current))

    assert loaded.input_data == current
    assert loaded.supplemented_paths == ()


def test_current_rac_json_uses_defaults_for_its_equipment_branch() -> None:
    inventory = load_legacy_inventory()
    fields = {field.id: field for field in inventory.fields}
    current = build_input_data({
        "H_A_type__0": fields["H_A_type__0"].choices[1],
        "C_A_type__0": fields["C_A_type__0"].choices[1],
    })

    loaded = load_compatible_input_json(json.dumps(current))

    assert loaded.input_data == current
    assert loaded.supplemented_paths == ()


def test_old_json_uses_current_defaults_only_for_missing_entries() -> None:
    old_input = {
        "case_name": "old-case",
        "region": 2,
        "H_A": {"type": 2},
        "legacy_extension": {"enabled": True},
    }

    loaded = load_compatible_input_json(json.dumps(old_input))

    assert loaded.input_data["case_name"] == "old-case"
    assert loaded.input_data["region"] == 2
    assert loaded.input_data["H_A"]["type"] == 2
    assert loaded.input_data["H_A"]["correct_no_general_ventilation_airflow"] == 1
    assert loaded.input_data["C_A"] == build_input_data({})["C_A"]
    assert loaded.input_data["legacy_extension"] == {"enabled": True}
    assert "C_A" in loaded.supplemented_paths
    assert "H_A.correct_no_general_ventilation_airflow" in loaded.supplemented_paths


def test_pre_next_regression_json_is_accepted() -> None:
    path = _ROOT / "packages/pyhees-jjj/src/test_utils/input_sample_type2.json"
    original = json.loads(path.read_text(encoding="utf-8"))

    loaded = load_compatible_input_json(path.read_bytes())

    assert loaded.input_data["case_name"] == original["case_name"]
    assert loaded.input_data["H_A"]["type"] == original["H_A"]["type"]
    assert loaded.input_data["H_A"]["q_rac_rtd_H"] == original["H_A"]["q_rac_rtd_H"]
    assert loaded.input_data["C_A"]["type"] == original["C_A"]["type"]
    assert loaded.input_data["H_A"]["correct_no_general_ventilation_airflow"] == 1
    assert loaded.supplemented_paths


@pytest.mark.parametrize("payload", ("[]", "null", '"input"'))
def test_input_json_requires_an_object_at_the_root(payload: str) -> None:
    with pytest.raises(ValueError, match="最上位はオブジェクト"):
        load_compatible_input_json(payload)


def test_input_json_reports_invalid_utf8_or_json() -> None:
    with pytest.raises(ValueError, match="2行1列"):
        load_compatible_input_json('{"case_name": "broken",\n}')

    with pytest.raises(ValueError, match="UTF-8"):
        load_compatible_input_json(b"\x81")
