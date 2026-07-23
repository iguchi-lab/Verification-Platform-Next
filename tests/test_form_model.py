import pytest

from verification_app.form_model import load_form_model


def test_form_model_preserves_schema_order_and_groups() -> None:
    model = load_form_model()

    assert len(model.fields) == 221
    assert len(model.sections) == 18
    assert model.keys == tuple(field.key for field in model.schema.fields)
    assert all(section.groups for section in model.sections)
    assert all(group.fields for section in model.sections for group in section.groups)


def test_form_model_updates_model_specific_visibility() -> None:
    model = load_form_model()
    values = model.schema.defaults()
    heating_type = next(field for field in model.fields if field.key == "H_A_type__0")

    assert not model.visibility(values)["a4__0"]

    values["H_A_type__0"] = heating_type.definition.choices[2]

    assert model.visibility(values)["a4__0"]


def test_form_values_are_mapped_by_schema_order() -> None:
    model = load_form_model()
    values = tuple(field.definition.default for field in model.fields)

    mapped = model.values_from_sequence(values)

    assert mapped == model.schema.defaults()


def test_form_value_count_is_validated() -> None:
    model = load_form_model()

    with pytest.raises(ValueError, match="Expected 221 form values, found 1"):
        model.values_from_sequence(("only-one",))
