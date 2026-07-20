from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable, Mapping


class FieldKind(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    SELECT = "select"


def _read_path(data: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


@dataclass(frozen=True, slots=True)
class Condition:
    path: tuple[str, ...]
    allowed_values: tuple[Any, ...]

    def matches(self, data: Mapping[str, Any]) -> bool:
        return _read_path(data, self.path) in self.allowed_values


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    path: tuple[str, ...]
    label: str
    kind: FieldKind
    default: Any
    section: str
    group: str = "基本項目"
    choices: tuple[Any, ...] = ()
    enabled_when: Condition | None = None
    description: str = ""

    @property
    def key(self) -> str:
        return ".".join(self.path)

    def is_enabled(self, data: Mapping[str, Any]) -> bool:
        return self.enabled_when is None or self.enabled_when.matches(data)


@dataclass(frozen=True)
class InputSchema:
    fields: tuple[FieldDefinition, ...] = field(default_factory=tuple)

    @classmethod
    def from_fields(cls, fields: Iterable[FieldDefinition]) -> "InputSchema":
        schema = cls(tuple(fields))
        schema.validate()
        return schema

    def validate(self) -> None:
        keys = [item.key for item in self.fields]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise ValueError(f"Duplicate schema paths: {duplicates}")
        for item in self.fields:
            if item.kind is FieldKind.SELECT and not item.choices:
                raise ValueError(f"Select field requires choices: {item.key}")
            if item.choices and item.default not in item.choices:
                raise ValueError(f"Default is not included in choices: {item.key}")

    def defaults(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for item in self.fields:
            current = result
            for part in item.path[:-1]:
                current = current.setdefault(part, {})
            current[item.path[-1]] = item.default
        return result

    def enabled_fields(self, data: Mapping[str, Any]) -> tuple[FieldDefinition, ...]:
        return tuple(item for item in self.fields if item.is_enabled(data))
