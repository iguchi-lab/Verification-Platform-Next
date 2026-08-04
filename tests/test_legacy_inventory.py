from collections import Counter

from verification_core import FieldKind, load_legacy_inventory


def test_260804_active_inventory_organizes_underfloor_fields() -> None:
    inventory = load_legacy_inventory()

    assert inventory.version == "260804"
    assert len(inventory.fields) == 221
    assert inventory.category_counts == {
        "基本設定": 44,
        "暖房": 84,
        "冷房": 91,
        "換気": 2,
    }
    assert len(inventory.section_names) == 18
    assert len({item.id for item in inventory.fields}) == 221
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
    assert ground_resistance.enabled_when is not None
    assert ground_resistance.enabled_when.path == (
        "change_underfloor_temperature__0",
    )


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
