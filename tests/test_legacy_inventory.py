from collections import Counter

from verification_core import FieldKind, load_legacy_inventory


def test_260715_inventory_has_all_fields() -> None:
    inventory = load_legacy_inventory()

    assert len(inventory.fields) == 222
    assert inventory.category_counts == {
        "基本設定": 45,
        "暖房": 84,
        "冷房": 91,
        "換気": 2,
    }
    assert len(inventory.section_names) == 18
    assert len({item.id for item in inventory.fields}) == 222


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
