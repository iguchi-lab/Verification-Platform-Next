import pytest

from verification_core import FieldOrigin
from verification_app.form_model import load_form_model


def test_form_model_preserves_schema_order_and_groups() -> None:
    model = load_form_model()

    assert len(model.fields) == 225
    assert len(model.sections) == 16
    assert model.keys == tuple(field.key for field in model.schema.fields)
    assert all(section.groups for section in model.sections)
    assert all(group.fields for section in model.sections for group in section.groups)


def test_form_model_preserves_input_origin() -> None:
    model = load_form_model()
    fields = {field.key: field for field in model.fields}

    assert fields["A_A__0"].definition.origin is FieldOrigin.BRI_WEB
    assert (
        fields["change_underfloor_temperature__0"].definition.origin
        is FieldOrigin.VERIFICATION_PLATFORM
    )


def test_rac_efficiency_classes_are_grouped_by_season_like_bri_web() -> None:
    model = load_form_model()
    heating = next(section for section in model.sections if section.name.startswith("⑦-2"))
    heating_group = next(
        group
        for group in heating.groups
        if group.name == "エネルギー消費効率の入力"
    )

    assert tuple(field.key for field in heating_group.fields) == (
        "H_A_input_mode__0",
        "H_A_mode__0",
    )
    assert not any(field.visible for field in heating_group.fields)

    cooling = next(section for section in model.sections if section.name.startswith("⑧-2"))
    cooling_group = next(
        group
        for group in cooling.groups
        if group.name == "エネルギー消費効率の入力"
    )
    assert tuple(field.key for field in cooling_group.fields) == (
        "C_A_input_mode__0",
        "C_A_mode__0",
    )
    assert not any(field.visible for field in cooling_group.fields)

    values = model.schema.defaults()
    heating_type = next(field for field in model.fields if field.key == "H_A_type__0")
    cooling_type = next(field for field in model.fields if field.key == "C_A_type__0")
    values["H_A_type__0"] = heating_type.definition.choices[1]
    values["C_A_type__0"] = cooling_type.definition.choices[1]
    visibility = model.visibility(values)
    assert visibility["H_A_input_mode__0"]
    assert not visibility["H_A_mode__0"]
    assert visibility["C_A_input_mode__0"]
    assert not visibility["C_A_mode__0"]
    assert not visibility["H_A_input__0"]
    assert not visibility["C_A_input__0"]

    values["H_A_input_mode__0"] = "入力する"
    values["C_A_input_mode__0"] = "入力する"
    selected_efficiency = model.visibility(values)
    assert selected_efficiency["H_A_mode__0"]
    assert selected_efficiency["C_A_mode__0"]


def test_rac_dual_compressor_is_grouped_separately_from_capacity_inputs() -> None:
    model = load_form_model()

    for section_prefix, compressor_key, capacity_group_name in (
        ("⑦-2", "H_A_dualcompressor__0", "暖房能力の入力"),
        ("⑧-2", "C_A_dualcompressor__0", "冷房能力の入力"),
    ):
        section = next(
            section for section in model.sections if section.name.startswith(section_prefix)
        )
        capacity_group = next(
            group for group in section.groups if group.name == capacity_group_name
        )
        compressor_group = next(
            group
            for group in section.groups
            if group.name == "小能力時高効率型コンプレッサー"
        )

        assert compressor_key not in tuple(
            field.key for field in capacity_group.fields
        )
        assert tuple(field.key for field in compressor_group.fields) == (
            compressor_key,
        )


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


@pytest.mark.parametrize(
    ("control_key", "enabled_value", "dependent_keys"),
    (
        (
            "carry_over_heat__0",
            True,
            (
                "c1_BR_R_1__0",
                "c1_BR_R_2__0",
                "c1_BR_R_3__0",
                "c1_BR_R_4__0",
                "c1_BR_R_5__0",
                "c1_NR_R__0",
            ),
        ),
        ("H_A_input_V_hs_dsgn_H__0", "入力する", ("H_A_V_hs_dsgn_H__0",)),
        ("H_A_input_V_hs_min__0", "入力する", ("H_A_V_hs_min__0",)),
        (
            "H_A_input_E_E_fan_min__0",
            "入力する",
            ("H_A_E_E_fan_logic__0", "H_A_E_E_fan_min__0"),
        ),
        ("C_A_input_V_hs_dsgn_C__0", "入力する", ("C_A_V_hs_dsgn_C__0",)),
        ("C_A_input_V_hs_min__0", "入力する", ("C_A_V_hs_min__0",)),
        (
            "C_A_input_E_E_fan_min__0",
            "入力する",
            ("C_A_E_E_fan_logic__0", "C_A_E_E_fan_min__0"),
        ),
        ("HEX_install__0", "設置する", ("etr_t__0",)),
    ),
)
def test_form_model_hides_optional_values_until_their_input_is_enabled(
    control_key: str,
    enabled_value: object,
    dependent_keys: tuple[str, ...],
) -> None:
    model = load_form_model()
    values = model.schema.defaults()

    initial = model.visibility(values)
    assert all(not initial[key] for key in dependent_keys)

    values[control_key] = enabled_value
    enabled = model.visibility(values)
    assert all(enabled[key] for key in dependent_keys)


def test_form_model_applies_nested_equipment_input_visibility() -> None:
    model = load_form_model()
    values = model.schema.defaults()

    initial = model.visibility(values)
    assert initial["H_A_input__0"]
    assert not initial["H_A_q_hs_rtd_H1__0"]
    assert not initial["H_A_q_hs_mid_H1__0"]

    values["H_A_input__0"] = "定格能力試験の値を入力する"
    rated = model.visibility(values)
    assert rated["H_A_q_hs_rtd_H1__0"]
    assert not rated["H_A_q_hs_mid_H1__0"]

    values["H_A_input__0"] = "定格能力試験と中間能力試験の値を入力する"
    rated_and_mid = model.visibility(values)
    assert rated_and_mid["H_A_q_hs_rtd_H1__0"]
    assert rated_and_mid["H_A_q_hs_mid_H1__0"]

    values["H_A_input__0"] = "入力しない"
    hidden_again = model.visibility(values)
    assert not hidden_again["H_A_q_hs_rtd_H1__0"]
    assert not hidden_again["H_A_q_hs_mid_H1__0"]

    heating_type = next(field for field in model.fields if field.key == "H_A_type__0")
    values["H_A_type__0"] = heating_type.definition.choices[1]
    rac = model.visibility(values)
    assert rac["H_A_input_C_af_H2__0"]
    assert rac["H_A_dedicated_chamber2__0"]
    assert not rac["H_A_C_af_H2__0"]
    assert not rac["H_A_q_rac_rtd_H__0"]
    assert not rac["f_SFP_H__0"]

    values["H_A_input_C_af_H2__0"] = "補正係数を直接入力する"
    values["H_A_input_rac_performance__0"] = "性能を直接入力"
    values["H_A_input_f_SFP_H__0"] = "入力する"
    direct = model.visibility(values)
    assert not direct["H_A_dedicated_chamber2__0"]
    assert direct["H_A_C_af_H2__0"]
    assert direct["H_A_q_rac_rtd_H__0"]
    assert direct["f_SFP_H__0"]

    values["H_A_input_rac_performance__0"] = "面積から能力を算出"
    capacity_hidden_again = model.visibility(values)
    assert not capacity_hidden_again["H_A_q_rac_rtd_H__0"]
    assert capacity_hidden_again["H_A_dualcompressor__0"]


def test_form_values_are_mapped_by_schema_order() -> None:
    model = load_form_model()
    values = tuple(field.definition.default for field in model.fields)

    mapped = model.values_from_sequence(values)

    assert mapped == model.schema.defaults()


def test_form_value_count_is_validated() -> None:
    model = load_form_model()

    with pytest.raises(ValueError, match="Expected 225 form values, found 1"):
        model.values_from_sequence(("only-one",))
