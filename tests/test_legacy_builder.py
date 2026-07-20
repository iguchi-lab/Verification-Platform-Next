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


def test_boolean_encoding_matches_existing_contract() -> None:
    values = default_ui_values()
    values["carry_over_heat__0"] = True

    data = build_legacy_input_data(values)

    assert data["carry_over_heat"] == 2
