from typing import Any

from verification_core import (
    FieldKind,
    build_input_data,
    default_ui_values,
    load_legacy_inventory,
)
from verification_core._legacy_form_evaluator import build_legacy_input_data

_TYPE_FIELDS = {
    ("H_A", "type"): "H_A_type__0",
    ("C_A", "type"): "C_A_type__0",
}


def test_every_boolean_and_select_alternative_matches_legacy() -> None:
    inventory = load_legacy_inventory("260804")
    fields = {field.id: field for field in inventory.fields}

    for field in inventory.fields:
        for candidate in _alternatives(field.kind, field.default, field.choices):
            values = default_ui_values(inventory)
            if field.enabled_when is not None:
                control_id = _TYPE_FIELDS.get(field.enabled_when.path)
                if control_id is None:
                    (control_id,) = field.enabled_when.path
                    values[control_id] = field.enabled_when.allowed_values[0]
                else:
                    control = fields[control_id]
                    selected_type = int(field.enabled_when.allowed_values[0])
                    values[control_id] = control.choices[selected_type - 1]
            values[field.id] = candidate

            assert build_input_data(values, version="260804") == build_legacy_input_data(values), (
                field.id,
                candidate,
            )


def _alternatives(
    kind: FieldKind,
    default: Any,
    choices: tuple[Any, ...],
) -> tuple[Any, ...]:
    if kind is FieldKind.BOOLEAN:
        return (not default,)
    if kind is FieldKind.SELECT:
        return tuple(choice for choice in choices if choice != default)
    if kind in {FieldKind.NUMBER, FieldKind.INTEGER}:
        return (default + 1,)
    if kind is FieldKind.TEXT:
        return (f"{default}-changed",)
    raise AssertionError(f"Unhandled field kind: {kind}")
