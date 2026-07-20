import pytest

from verification_core import (
    default_ui_values,
    load_input_bindings,
    load_legacy_inventory,
)
from verification_core.transforms import parse_binding_expression


def test_260715_catalog_covers_every_ui_field() -> None:
    inventory = load_legacy_inventory()
    catalog = load_input_bindings()

    assert len(catalog.bindings) == 264
    assert catalog.source_ids == frozenset(field.id for field in inventory.fields)


def test_heating_and_cooling_types_keep_all_conditional_mappings() -> None:
    catalog = load_input_bindings()

    heating = catalog.for_target("H_A", "type")
    cooling = catalog.for_target("C_A", "type")

    assert len(heating) == 4
    assert len(cooling) == 4
    assert {binding.expression for binding in heating} == {"1", "2", "3", "4"}
    assert {binding.expression for binding in cooling} == {"1", "2", "3", "4"}
    assert all(binding.source_ids == ("H_A_type__0",) for binding in heating)
    assert all(binding.source_ids == ("C_A_type__0",) for binding in cooling)
    assert all(binding.conditions for binding in heating + cooling)


def test_room_ratio_binding_references_all_five_rooms() -> None:
    catalog = load_input_bindings()
    (binding,) = catalog.for_target("C1_BR_R_i")

    assert binding.source_ids == (
        "c1_BR_R_1__0",
        "c1_BR_R_2__0",
        "c1_BR_R_3__0",
        "c1_BR_R_4__0",
        "c1_BR_R_5__0",
    )


def test_catalog_has_no_unknown_source_ids() -> None:
    inventory = load_legacy_inventory()
    catalog = load_input_bindings()
    known_ids = {field.id for field in inventory.fields}

    assert catalog.source_ids <= known_ids


def test_all_binding_expressions_have_typed_transforms() -> None:
    values = default_ui_values()

    for binding in load_input_bindings().bindings:
        binding.evaluate(values)


def test_typed_transforms_cover_representative_operations() -> None:
    catalog = load_input_bindings()
    values = default_ui_values()

    (boolean_binding,) = catalog.for_target("carry_over_heat")
    (array_binding,) = catalog.for_target("C1_BR_R_i")
    (division_binding,) = catalog.for_target("HEX", "etr_t")
    empty_dict_binding = catalog.for_target("H_A")[0]

    values["carry_over_heat__0"] = True
    values["c1_BR_R_3__0"] = 123
    values["etr_t__0"] = 25

    assert boolean_binding.evaluate(values) == 2
    assert array_binding.evaluate(values) == [893676, 500835, 123, 325488, 325598]
    assert division_binding.evaluate(values) == 0.25
    assert empty_dict_binding.evaluate(values) == {}
    assert empty_dict_binding.evaluate(values) is not empty_dict_binding.evaluate(values)


def test_unsupported_binding_expression_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported binding expression syntax: Call",
    ):
        parse_binding_expression("open('secret')", ())
