from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, replace
from importlib import resources
from typing import Any

from .schema import Condition, FieldKind, FieldOrigin


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
    description: str = ""
    origin: FieldOrigin = FieldOrigin.BRI_WEB


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


def _field_override_from_dict(value: dict[str, Any]) -> dict[str, Any]:
    override = dict(value)
    if "enabled_when" in override:
        override["enabled_when"] = _condition_from_dict(override["enabled_when"])
    return override


def _field_from_dict(item: dict[str, Any]) -> LegacyFieldDefinition:
    return LegacyFieldDefinition(
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
        description=item.get("description", ""),
        origin=FieldOrigin(item.get("origin", FieldOrigin.BRI_WEB)),
    )


def load_legacy_inventory(version: str = "260812") -> LegacyInputInventory:
    file_name = f"input_fields_{version}.json"
    data_file = resources.files("verification_core.data").joinpath(file_name)
    with data_file.open(encoding="utf-8") as stream:
        payload = json.load(stream)

    if "base_version" in payload:
        base = load_legacy_inventory(payload["base_version"])
        removed_ids = frozenset(payload.get("remove_field_ids", ()))
        overrides = {
            field_id: _field_override_from_dict(value)
            for field_id, value in payload.get("field_overrides", {}).items()
        }
        platform_sections = frozenset(
            payload.get("verification_platform_sections", ())
        )
        platform_field_ids = frozenset(
            payload.get("verification_platform_field_ids", ())
        )
        bri_web_field_ids = frozenset(payload.get("bri_web_field_ids", ()))
        known_sections = frozenset(field.section for field in base.fields)
        unknown_sections = platform_sections - known_sections
        if unknown_sections:
            raise ValueError(
                "Unknown verification_platform_sections: "
                f"{sorted(unknown_sections)}"
            )
        known_ids = frozenset(field.id for field in base.fields)
        unknown_ids = (platform_field_ids | bri_web_field_ids) - known_ids
        if unknown_ids:
            raise ValueError(
                "Unknown field origin IDs: "
                f"{sorted(unknown_ids)}"
            )
        fields = tuple(
            replace(
                field,
                origin=(
                    FieldOrigin.BRI_WEB
                    if field.id in bri_web_field_ids
                    else FieldOrigin.VERIFICATION_PLATFORM
                    if (
                        overrides.get(field.id, {}).get("section", field.section)
                        in platform_sections
                        or field.id in platform_field_ids
                    )
                    else field.origin
                ),
                **overrides.get(field.id, {}),
            )
            for field in base.fields
            if field.id not in removed_ids
        )
        mutable_fields = list(fields)
        for item in payload.get("append_fields", ()):
            field = _field_from_dict(item)
            insert_after = item.get("insert_after_field_id")
            if insert_after is None:
                mutable_fields.append(field)
                continue
            try:
                index = next(
                    index
                    for index, existing in enumerate(mutable_fields)
                    if existing.id == insert_after
                )
            except StopIteration as error:
                raise ValueError(
                    f"Unknown insert_after_field_id: {insert_after}"
                ) from error
            mutable_fields.insert(index + 1, field)
        fields = tuple(mutable_fields)
    else:
        fields = tuple(_field_from_dict(item) for item in payload["fields"])
    inventory = LegacyInputInventory(version=payload["version"], fields=fields)
    inventory.validate(expected_count=int(payload["field_count"]))
    return inventory
