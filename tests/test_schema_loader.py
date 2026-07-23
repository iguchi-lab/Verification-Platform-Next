from verification_core import (
    default_ui_values,
    load_input_schema,
    load_legacy_inventory,
)


def test_input_schema_contains_all_inventory_fields() -> None:
    inventory = load_legacy_inventory()
    schema = load_input_schema()

    assert len(schema.fields) == 221
    assert schema.defaults() == default_ui_values(inventory)
    assert {field.key for field in schema.fields} == {
        field.id for field in inventory.fields
    }


def test_model_conditions_reference_the_source_selector() -> None:
    schema = load_input_schema()
    values = schema.defaults()
    model_three_field = next(field for field in schema.fields if field.key == "a4__0")
    heating_type = next(
        field for field in schema.fields if field.key == "H_A_type__0"
    )

    assert not model_three_field.is_enabled(values)

    values["H_A_type__0"] = heating_type.choices[2]

    assert model_three_field.is_enabled(values)


def test_schema_preserves_inventory_presentation_metadata() -> None:
    inventory = load_legacy_inventory()
    schema = load_input_schema()
    legacy = inventory.fields[0]
    field = schema.fields[0]

    assert field.label == legacy.label
    assert field.section == legacy.section
    assert field.group == legacy.group
    assert field.kind == legacy.kind
    assert field.choices == legacy.choices
