from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from verification_core import FieldDefinition, FieldKind, InputSchema, load_input_schema


@dataclass(frozen=True, slots=True)
class FormField:
    definition: FieldDefinition
    visible: bool

    @property
    def key(self) -> str:
        return self.definition.key


@dataclass(frozen=True, slots=True)
class FormGroup:
    name: str
    fields: tuple[FormField, ...]


@dataclass(frozen=True, slots=True)
class FormSection:
    name: str
    groups: tuple[FormGroup, ...]


@dataclass(frozen=True, slots=True)
class FormModel:
    schema: InputSchema
    sections: tuple[FormSection, ...]

    @property
    def fields(self) -> tuple[FormField, ...]:
        return tuple(
            field for section in self.sections for group in section.groups for field in group.fields
        )

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(field.key for field in self.fields)

    def values_from_sequence(self, values: Iterable[Any]) -> dict[str, Any]:
        resolved = tuple(values)
        if len(resolved) != len(self.schema.fields):
            raise ValueError(
                f"Expected {len(self.schema.fields)} form values, found {len(resolved)}"
            )
        return {
            field.key: _coerce_value(field, value)
            for field, value in zip(self.schema.fields, resolved, strict=True)
        }

    def visibility(self, values: Mapping[str, Any]) -> dict[str, bool]:
        fields_by_key = {field.key: field for field in self.schema.fields}
        resolved: dict[str, bool] = {}
        resolving: set[str] = set()

        def is_visible(field: FieldDefinition) -> bool:
            if field.key in resolved:
                return resolved[field.key]
            if field.key in resolving:
                raise ValueError(f"Circular visibility dependency: {field.key}")
            resolving.add(field.key)
            condition = field.enabled_when
            if condition is None:
                visible = True
            else:
                control = fields_by_key.get(".".join(condition.path))
                visible = (
                    control is not None
                    and is_visible(control)
                    and condition.matches(values)
                )
            resolving.remove(field.key)
            resolved[field.key] = visible
            return visible

        return {field.key: is_visible(field) for field in self.schema.fields}


def load_form_model(
    version: str = "260804",
    values: Mapping[str, Any] | None = None,
) -> FormModel:
    schema = load_input_schema(version)
    resolved_values = schema.defaults()
    if values is not None:
        resolved_values.update(values)

    sections: list[FormSection] = []
    for section_name in dict.fromkeys(field.section for field in schema.fields):
        section_fields = tuple(field for field in schema.fields if field.section == section_name)
        groups = tuple(
            FormGroup(
                name=group_name,
                fields=tuple(
                    FormField(
                        definition=field,
                        visible=field.is_enabled(resolved_values),
                    )
                    for field in section_fields
                    if field.group == group_name
                ),
            )
            for group_name in dict.fromkeys(field.group for field in section_fields)
        )
        sections.append(FormSection(name=section_name, groups=groups))
    return FormModel(schema=schema, sections=tuple(sections))


def _coerce_value(field: FieldDefinition, value: Any) -> Any:
    if field.kind is FieldKind.INTEGER:
        return int(value)
    if field.kind is FieldKind.NUMBER:
        return float(value)
    if field.kind is FieldKind.BOOLEAN:
        return bool(value)
    if field.kind is FieldKind.TEXT:
        return str(value)
    return value
