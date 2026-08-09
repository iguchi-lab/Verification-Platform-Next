import pytest

from verification_app.form_model import load_form_model


def test_form_model_preserves_schema_order_and_groups() -> None:
    model = load_form_model()

    assert len(model.fields) == 223
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


def test_form_model_updates_nested_underfloor_visibility() -> None:
    model = load_form_model()
    values = model.schema.defaults()

    initial = model.visibility(values)
    assert not initial["r_A_ufvnt__0"]
    assert not initial["R_g__0"]
    assert not initial["input_ufac_consts__0"]
    assert not initial["Theta_g_avg__0"]
    assert not initial["U_s_vert__0"]
    assert not initial["phi__0"]

    values["underfloor_ventilation__0"] = True
    ventilation = model.visibility(values)
    assert ventilation["r_A_ufvnt__0"]
    assert ventilation["underfloor_insulation__0"]

    values["change_underfloor_temperature__0"] = True
    new_underfloor = model.visibility(values)
    assert new_underfloor["R_g__0"]
    assert new_underfloor["input_ufac_consts__0"]
    assert not new_underfloor["Theta_g_avg__0"]

    values["input_ufac_consts__0"] = True
    constants = model.visibility(values)
    assert constants["Theta_g_avg__0"]
    assert constants["U_s_vert__0"]
    assert constants["phi__0"]

    values["change_underfloor_temperature__0"] = False
    hidden_parent = model.visibility(values)
    assert not hidden_parent["input_ufac_consts__0"]
    assert not hidden_parent["Theta_g_avg__0"]
    assert not hidden_parent["U_s_vert__0"]
    assert not hidden_parent["phi__0"]


def test_form_values_are_mapped_by_schema_order() -> None:
    model = load_form_model()
    values = tuple(field.definition.default for field in model.fields)

    mapped = model.values_from_sequence(values)

    assert mapped == model.schema.defaults()


def test_form_value_count_is_validated() -> None:
    model = load_form_model()

    with pytest.raises(ValueError, match="Expected 223 form values, found 1"):
        model.values_from_sequence(("only-one",))
