import pytest

import verification_core.legacy_builder as legacy_builder
from verification_core import (
    build_legacy_input_data,
    default_ui_values,
    load_legacy_inventory,
)


def test_default_inventory_builds_input_data() -> None:
    inventory = load_legacy_inventory()
    data = build_legacy_input_data(default_ui_values(inventory))

    assert data["case_name"] == "default"
    assert data["H_A"]["type"] == 1
    assert data["C_A"]["type"] == 1
    assert data["carry_over_heat"] == 1
    assert data["C1_BR_R_i"] == [893676, 500835, 400667, 325488, 325598]


def test_heating_model_selection_is_transformed() -> None:
    inventory = load_legacy_inventory()
    values = default_ui_values(inventory)
    heating_type = next(
        item for item in inventory.fields if item.id == "H_A_type__0"
    )
    values[heating_type.id] = heating_type.choices[1]

    data = build_legacy_input_data(values)

    assert data["H_A"]["type"] == 2


def test_cooling_model_selection_is_transformed() -> None:
    inventory = load_legacy_inventory()
    values = default_ui_values(inventory)
    cooling_type = next(
        item for item in inventory.fields if item.id == "C_A_type__0"
    )
    values[cooling_type.id] = cooling_type.choices[2]

    data = build_legacy_input_data(values)

    assert data["C_A"]["type"] == 3


def test_array_values_are_built_from_individual_fields() -> None:
    values = default_ui_values()
    values["c1_BR_R_3__0"] = 123

    assert build_legacy_input_data(values)["C1_BR_R_i"] == [
        893676,
        500835,
        123,
        325488,
        325598,
    ]


def test_boolean_encoding_matches_existing_contract() -> None:
    values = default_ui_values()
    values["carry_over_heat__0"] = True

    data = build_legacy_input_data(values)

    assert data["carry_over_heat"] == 2


def test_unsupported_syntax_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        legacy_builder,
        "load_legacy_form_source",
        lambda version: "import os\ninput_data = {}\n",
    )

    with pytest.raises(ValueError, match="Unsupported legacy form syntax: Import"):
        build_legacy_input_data({})
