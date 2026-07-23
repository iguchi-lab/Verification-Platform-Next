from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, replace
from importlib import resources
from typing import Any

from .schema import Condition, FieldKind


@dataclass(frozen=True, slots=True)
class LegacyFieldDefinition:
    id: str
    source_name: str
    source_occurrence: int
    label: str
    section: str
    group: str
    category: str
    kind: FieldKind
    default: Any
    choices: tuple[Any, ...]
    enabled_when: Condition | None = None


@dataclass(frozen=True)
class LegacyInputInventory:
    version: str
    fields: tuple[LegacyFieldDefinition, ...]

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(Counter(item.category for item in self.fields))

    @property
    def section_names(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.section for item in self.fields))

    def validate(self, expected_count: int | None = None) -> None:
        if expected_count is not None and len(self.fields) != expected_count:
            raise ValueError(
                f"Expected {expected_count} fields, found {len(self.fields)}"
            )
        ids = [item.id for item in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("Inventory contains duplicate field IDs")
        for item in self.fields:
            if item.kind is FieldKind.SELECT:
                if not item.choices:
                    raise ValueError(f"Select field requires choices: {item.id}")
                if item.default not in item.choices:
                    raise ValueError(
                        f"Default is not included in choices: {item.id}"
                    )


def _condition_from_dict(value: dict[str, Any] | None) -> Condition | None:
    if value is None:
        return None
    return Condition(
        path=tuple(value["path"]),
        allowed_values=tuple(value["allowed_values"]),
    )


def load_legacy_inventory(version: str = "260724") -> LegacyInputInventory:
    file_name = f"input_fields_{version}.json"
    data_file = resources.files("verification_core.data").joinpath(file_name)
    with data_file.open(encoding="utf-8") as stream:
        payload = json.load(stream)

    if "base_version" in payload:
        base = load_legacy_inventory(payload["base_version"])
        removed_ids = frozenset(payload.get("remove_field_ids", ()))
        overrides = payload.get("field_overrides", {})
        fields = tuple(
            replace(field, **overrides.get(field.id, {}))
            for field in base.fields
            if field.id not in removed_ids
        )
    else:
        fields = tuple(
            LegacyFieldDefinition(
                id=item["id"],
                source_name=item["source_name"],
                source_occurrence=int(item["source_occurrence"]),
                label=item["label"],
                section=item["section"],
                group=item["group"],
                category=item["category"],
                kind=FieldKind(item["kind"]),
                default=item["default"],
                choices=tuple(item["choices"] or ()),
                enabled_when=_condition_from_dict(item.get("enabled_when")),
            )
            for item in payload["fields"]
        )
    inventory = LegacyInputInventory(version=payload["version"], fields=fields)
    inventory.validate(expected_count=int(payload["field_count"]))
    return inventory