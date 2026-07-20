from verification_core import load_input_bindings, load_legacy_inventory


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
