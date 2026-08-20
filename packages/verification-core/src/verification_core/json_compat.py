from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Mapping

from .declarative_builder import build_input_data
from .legacy import load_legacy_inventory


@dataclass(frozen=True, slots=True)
class CompatibleInputData:
    """Engine input restored from a saved JSON document."""

    input_data: dict[str, Any]
    supplemented_paths: tuple[str, ...]


def load_compatible_input_json(
    payload: str | bytes,
    version: str = "260812",
) -> CompatibleInputData:
    """Load old or current input JSON and fill fields added in newer versions.

    Values explicitly present in the uploaded document always win. Missing mapping
    entries are copied from the current declarative defaults. Lists and scalar values
    are treated atomically so that an uploaded value is never silently rewritten.
    """

    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8-sig")
        imported = json.loads(payload)
    except (JSONDecodeError, UnicodeDecodeError) as error:
        if isinstance(error, JSONDecodeError):
            location = f"（{error.lineno}行{error.colno}列）"
        else:
            location = ""
        raise ValueError(
            f"JSONファイルをUTF-8として読み取れませんでした{location}。"
        ) from error

    if not isinstance(imported, Mapping):
        raise ValueError("入力JSONの最上位はオブジェクト（{ ... }）である必要があります。")

    defaults = build_input_data(
        _equipment_type_defaults(imported, version),
        version=version,
    )
    supplemented: list[str] = []
    merged = _merge_mapping(defaults, imported, (), supplemented)
    return CompatibleInputData(merged, tuple(supplemented))


def _equipment_type_defaults(
    imported: Mapping[str, Any],
    version: str,
) -> dict[str, Any]:
    """Select defaults for the same heating/cooling branch as the saved JSON."""

    inventory = load_legacy_inventory(version)
    fields = {field.id: field for field in inventory.fields}
    values: dict[str, Any] = {}
    for equipment_key in ("H_A", "C_A"):
        equipment = imported.get(equipment_key)
        if not isinstance(equipment, Mapping):
            continue
        equipment_type = equipment.get("type")
        if isinstance(equipment_type, bool):
            continue
        try:
            choice_index = int(equipment_type) - 1
        except (TypeError, ValueError):
            continue
        field_id = f"{equipment_key}_type__0"
        field = fields[field_id]
        if 0 <= choice_index < len(field.choices):
            values[field_id] = field.choices[choice_index]
    return values


def _merge_mapping(
    defaults: Mapping[str, Any],
    imported: Mapping[str, Any],
    prefix: tuple[str, ...],
    supplemented: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, default_value in defaults.items():
        path = (*prefix, key)
        if key not in imported:
            result[key] = deepcopy(default_value)
            supplemented.append(".".join(path))
            continue

        imported_value = imported[key]
        if isinstance(default_value, Mapping) and isinstance(imported_value, Mapping):
            result[key] = _merge_mapping(
                default_value,
                imported_value,
                path,
                supplemented,
            )
        else:
            result[key] = deepcopy(imported_value)

    for key, imported_value in imported.items():
        if key not in defaults:
            result[key] = deepcopy(imported_value)
    return result
