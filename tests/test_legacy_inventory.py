from collections import Counter

from verification_core import FieldKind, FieldOrigin, load_legacy_inventory


def test_260809_active_inventory_adds_opt_in_calculation_corrections() -> None:
    inventory = load_legacy_inventory()

    assert inventory.version == "260809"
    assert len(inventory.fields) == 225
    assert inventory.category_counts == {
        "基本設定": 46,
        "暖房": 86,
        "冷房": 91,
        "換気": 2,
    }
    assert len(inventory.section_names) == 16
    assert len({item.id for item in inventory.fields}) == 225
    assert "underfloor_air_conditioning_air_supply__0" not in {
        item.id for item in inventory.fields
    }
    new_underfloor = next(
        item
        for item in inventory.fields
        if item.id == "change_underfloor_temperature__0"
    )
    assert new_underfloor.label == "新床下空調を使用する"
    assert new_underfloor.group == "新床下空調（Verification Platform）"
    assert "床下利用面積は100%" in new_underfloor.description

    ventilation_area = next(
        item for item in inventory.fields if item.id == "r_A_ufvnt__0"
    )
    assert ventilation_area.group == "床下換気（建研方式）"
    assert ventilation_area.enabled_when is not None
    assert ventilation_area.enabled_when.path == ("underfloor_ventilation__0",)
    assert ventilation_area.enabled_when.allowed_values == (True,)

    ground_resistance = next(
        item for item in inventory.fields if item.id == "R_g__0"
    )
    assert ground_resistance.group == "手動設定する補助定数"
    assert ground_resistance.enabled_when is not None
    assert ground_resistance.enabled_when.path == ("input_ufac_consts__0",)
    assert "既定値0.15" in ground_resistance.description

    corrections = {
        item.id: item for item in inventory.fields
        if item.group == "建研本家との比較設定"
    }
    assert set(corrections) == {
        "correct_cooling_partition_heat_transfer__0",
        "correct_no_general_ventilation_airflow__0",
    }
    assert all(item.default is False for item in corrections.values())


def test_260809_consolidates_related_general_sections() -> None:
    inventory = load_legacy_inventory()
    fields = {item.id: item for item in inventory.fields}

    assert fields["case_name__0"].section == "①・② 計算条件・外部ファイル"
    assert fields["case_name__0"].group == "計算条件"
    for field_id in ("climateFile__0", "loadFile__0"):
        assert fields[field_id].section == "①・② 計算条件・外部ファイル"
        assert fields[field_id].group == "外部ファイル（任意）"

    carry_over_ids = (
        "carry_over_heat__0",
        "c1_BR_R_1__0",
        "c1_BR_R_2__0",
        "c1_BR_R_3__0",
        "c1_BR_R_4__0",
        "c1_BR_R_5__0",
        "c1_NR_R__0",
    )
    for field_id in carry_over_ids:
        assert fields[field_id].section == "⑥ その他"
        assert fields[field_id].group == "過剰熱量持越し"

    assert "① 計算条件名" not in inventory.section_names
    assert "② 外部ファイル名の入力（ある場合のみ）" not in inventory.section_names
    assert "⑥-1. 過剰熱量持越し" not in inventory.section_names
    assert "⑨ 熱交換型換気設備" in inventory.section_names
    assert "⑨ 熱交換型換気設備）" not in inventory.section_names


def test_260809_has_independent_heating_and_cooling_efficiency_classes() -> None:
    inventory = load_legacy_inventory()
    fields = {
        item.id: item
        for item in inventory.fields
        if item.id in {
            "H_A_input_mode__0",
            "H_A_mode__0",
            "C_A_input_mode__0",
            "C_A_mode__0",
        }
    }

    for field in (fields["H_A_input_mode__0"], fields["H_A_mode__0"]):
        assert field.section.startswith("⑦-2 暖房")
        assert field.group == "エネルギー消費効率の入力"
        assert field.category == "暖房"
        assert field.enabled_when is not None
        assert field.origin is FieldOrigin.BRI_WEB
    assert fields["H_A_input_mode__0"].enabled_when.path == ("H_A", "type")
    assert fields["H_A_input_mode__0"].enabled_when.allowed_values == (2,)
    assert fields["H_A_mode__0"].enabled_when.path == ("H_A_input_mode__0",)
    assert fields["H_A_mode__0"].enabled_when.allowed_values == ("入力する",)

    for field in (fields["C_A_input_mode__0"], fields["C_A_mode__0"]):
        assert field.section.startswith("⑧-2 冷房")
        assert field.group == "エネルギー消費効率の入力"
        assert field.category == "冷房"
        assert field.enabled_when is not None
        assert field.origin is FieldOrigin.BRI_WEB
    assert fields["C_A_input_mode__0"].enabled_when.path == ("C_A", "type")
    assert fields["C_A_input_mode__0"].enabled_when.allowed_values == (2,)
    assert fields["C_A_mode__0"].enabled_when.path == ("C_A_input_mode__0",)
    assert fields["C_A_mode__0"].enabled_when.allowed_values == ("入力する",)

    assert fields["H_A_input_mode__0"].source_name == "H_A_input_mode"
    assert fields["H_A_mode__0"].source_name == "H_A_mode"
    assert fields["C_A_input_mode__0"].source_name == "C_A_input_mode"
    assert fields["C_A_mode__0"].source_name == "C_A_mode"


def test_260809_classifies_bri_web_and_verification_platform_inputs() -> None:
    inventory = load_legacy_inventory()
    fields = {item.id: item for item in inventory.fields}

    assert Counter(item.origin for item in inventory.fields) == {
        FieldOrigin.BRI_WEB: 47,
        FieldOrigin.VERIFICATION_PLATFORM: 178,
    }
    assert fields["A_A__0"].origin is FieldOrigin.BRI_WEB
    assert fields["H_A_input_V_hs_dsgn_H__0"].origin is FieldOrigin.BRI_WEB
    assert fields["C_A_input_mode__0"].origin is FieldOrigin.BRI_WEB
    assert fields["climateFile__0"].origin is FieldOrigin.VERIFICATION_PLATFORM
    assert fields["H_A_input_V_hs_min__0"].origin is FieldOrigin.VERIFICATION_PLATFORM
    assert (
        fields["correct_cooling_partition_heat_transfer__0"].origin
        is FieldOrigin.VERIFICATION_PLATFORM
    )


def test_260804_historical_inventory_remains_frozen() -> None:
    inventory = load_legacy_inventory("260804")

    assert inventory.version == "260804"
    assert len(inventory.fields) == 221


def test_260724_historical_inventory_remains_frozen() -> None:
    inventory = load_legacy_inventory("260724")

    assert inventory.version == "260724"
    assert len(inventory.fields) == 221
    assert all(item.description == "" for item in inventory.fields)


def test_260715_historical_inventory_remains_frozen() -> None:
    inventory = load_legacy_inventory("260715")

    assert len(inventory.fields) == 222
    assert inventory.category_counts["基本設定"] == 45
    assert "underfloor_air_conditioning_air_supply__0" in {
        item.id for item in inventory.fields
    }


def test_model_sections_have_activation_conditions() -> None:
    inventory = load_legacy_inventory()

    heating = next(item for item in inventory.fields if item.section.startswith("⑦-2"))
    cooling = next(item for item in inventory.fields if item.section.startswith("⑧-4"))

    assert heating.enabled_when is not None
    assert heating.enabled_when.path == ("H_A", "type")
    assert heating.enabled_when.allowed_values == (2,)

    assert cooling.enabled_when is not None
    assert cooling.enabled_when.path == ("C_A", "type")
    assert cooling.enabled_when.allowed_values == (4,)


def test_optional_input_values_have_their_own_activation_conditions() -> None:
    inventory = load_legacy_inventory()
    optional_values = [
        item
        for item in inventory.fields
        if "入力する場合のみ" in item.label or "設置する場合のみ" in item.label
    ]

    assert len(optional_values) == 55
    assert all(item.enabled_when is not None for item in optional_values)
    assert all(
        item.enabled_when.path not in {("H_A", "type"), ("C_A", "type")}
        for item in optional_values
        if item.enabled_when is not None
    )


def test_select_defaults_are_valid() -> None:
    inventory = load_legacy_inventory()
    selects = [item for item in inventory.fields if item.kind is FieldKind.SELECT]

    assert selects
    assert all(item.default in item.choices for item in selects)


def test_duplicate_source_variables_have_unique_ids() -> None:
    inventory = load_legacy_inventory()
    counts = Counter(item.source_name for item in inventory.fields)

    assert counts["a0"] == 7
    assert counts["H_A_input"] == 2
    assert len({item.id for item in inventory.fields}) == len(inventory.fields)
