import pytest

from verification_core import Condition, FieldDefinition, FieldKind, InputSchema


def test_schema_builds_nested_defaults() -> None:
    schema = InputSchema.from_fields(
        [
            FieldDefinition(
                path=("case_name",),
                label="計算条件名",
                kind=FieldKind.TEXT,
                default="default",
                section="基本設定",
            ),
            FieldDefinition(
                path=("H_A", "type"),
                label="暖房設備の種類",
                kind=FieldKind.SELECT,
                default=1,
                choices=(1, 2, 3, 4),
                section="暖房全般",
            ),
        ]
    )

    assert schema.defaults() == {"case_name": "default", "H_A": {"type": 1}}


def test_condition_controls_model_specific_field() -> None:
    field = FieldDefinition(
        path=("H_A", "V_hs_dsgn"),
        label="設計風量",
        kind=FieldKind.NUMBER,
        default=1500.0,
        section="暖房ダクト式",
        enabled_when=Condition(path=("H_A", "type"), allowed_values=(1,)),
    )

    assert field.is_enabled({"H_A": {"type": 1}})
    assert not field.is_enabled({"H_A": {"type": 2}})


def test_duplicate_paths_are_rejected() -> None:
    item = FieldDefinition(
        path=("case_name",),
        label="計算条件名",
        kind=FieldKind.TEXT,
        default="default",
        section="基本設定",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        InputSchema.from_fields([item, item])
