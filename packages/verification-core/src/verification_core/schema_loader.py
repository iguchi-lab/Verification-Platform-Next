from __future__ import annotations

from .legacy import LegacyFieldDefinition, LegacyInputInventory, load_legacy_inventory
from .schema import Condition, FieldDefinition, InputSchema

_TYPE_CONTROLS = {
    ("H_A", "type"): "H_A_type__0",
    ("C_A", "type"): "C_A_type__0",
}


def load_input_schema(version: str = "260724") -> InputSchema:
    inventory = load_legacy_inventory(version)
    return InputSchema.from_fields(
        _field_definition(field, inventory)
        for field in inventory.fields
    )


def _field_definition(
    field: LegacyFieldDefinition,
    inventory: LegacyInputInventory,
) -> FieldDefinition:
    return FieldDefinition(
        path=(field.id,),
        label=field.label,
        kind=field.kind,
        default=field.default,
        section=field.section,
        group=field.group,
        choices=field.choices,
        enabled_when=_enabled_condition(field.enabled_when, inventory),
    )


def _enabled_condition(
    condition: Condition | None,
    inventory: LegacyInputInventory,
) -> Condition | None:
    if condition is None:
        return None
    control_id = _TYPE_CONTROLS.get(condition.path)
    if control_id is None:
        raise ValueError(
            f"Unsupported legacy enabled condition path: {'.'.join(condition.path)}"
        )
    control = next(field for field in inventory.fields if field.id == control_id)
    try:
        allowed_values = tuple(
            control.choices[int(value) - 1]
            for value in condition.allowed_values
        )
    except (IndexError, TypeError, ValueError) as error:
        raise ValueError(
            f"Invalid enabled condition values for {control_id}: "
            f"{condition.allowed_values}"
        ) from error
    return Condition(path=(control_id,), allowed_values=allowed_values)
