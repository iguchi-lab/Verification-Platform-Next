from itertools import product

from verification_core import (
    build_input_data,
    build_legacy_input_data,
    default_ui_values,
    load_legacy_inventory,
)


def test_default_output_matches_legacy_builder() -> None:
    values = default_ui_values()

    assert build_input_data(values) == build_legacy_input_data(values)


def test_representative_outputs_match_legacy_builder() -> None:
    inventory = load_legacy_inventory()
    fields = {field.id: field for field in inventory.fields}

    for heating, cooling, boolean_value in product(range(4), range(4), (False, True)):
        values = default_ui_values(inventory)
        values["H_A_type__0"] = fields["H_A_type__0"].choices[heating]
        values["C_A_type__0"] = fields["C_A_type__0"].choices[cooling]
        values["carry_over_heat__0"] = boolean_value
        values["c1_BR_R_3__0"] = 123

        assert build_input_data(values) == build_legacy_input_data(values)


def test_partial_values_use_inventory_defaults() -> None:
    data = build_input_data({"case_name__0": "partial"})

    assert data["case_name"] == "partial"
    assert data["H_A"]["type"] == 1
    assert data["C_A"]["type"] == 1
