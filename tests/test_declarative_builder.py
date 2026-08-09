from itertools import product

from verification_core import (
    build_input_data,
    build_legacy_input_data,
    default_ui_values,
    load_legacy_inventory,
)


def test_default_output_matches_legacy_builder() -> None:
    inventory = load_legacy_inventory("260804")
    values = default_ui_values(inventory)

    assert build_input_data(values, version="260804") == build_legacy_input_data(values)


def test_representative_outputs_match_legacy_builder() -> None:
    inventory = load_legacy_inventory("260804")
    fields = {field.id: field for field in inventory.fields}

    for heating, cooling, boolean_value in product(range(4), range(4), (False, True)):
        values = default_ui_values(inventory)
        values["H_A_type__0"] = fields["H_A_type__0"].choices[heating]
        values["C_A_type__0"] = fields["C_A_type__0"].choices[cooling]
        values["carry_over_heat__0"] = boolean_value
        values["c1_BR_R_3__0"] = 123

        assert build_input_data(values, version="260804") == build_legacy_input_data(values)


def test_removed_legacy_underfloor_input_is_always_disabled() -> None:
    data = build_input_data({"change_underfloor_temperature__0": True})

    assert data["underfloor_air_conditioning_air_supply"] == "1"
    assert data["change_underfloor_temperature"] == "2"


def test_partial_values_use_inventory_defaults() -> None:
    data = build_input_data({"case_name__0": "partial"})

    assert data["case_name"] == "partial"
    assert data["H_A"]["type"] == 1
    assert data["C_A"]["type"] == 1


def test_correction_options_default_off_and_enable_together_for_both_seasons() -> None:
    default = build_input_data({})

    for key in ("H_A", "C_A"):
        assert default[key]["correct_cooling_partition_heat_transfer"] == 1
        assert default[key]["correct_no_general_ventilation_airflow"] == 1

    corrected = build_input_data({
        "correct_cooling_partition_heat_transfer__0": True,
        "correct_no_general_ventilation_airflow__0": True,
    })
    for key in ("H_A", "C_A"):
        assert corrected[key]["correct_cooling_partition_heat_transfer"] == 2
        assert corrected[key]["correct_no_general_ventilation_airflow"] == 2
