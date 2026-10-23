"""Restore editable values using the same declarative bindings as form submission."""
from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .bindings import load_input_bindings
from .declarative_builder import _branch_predicates, _conditions_match, _write_path
from .schema import FieldKind
from .schema_loader import load_input_schema
from .transforms import DivideValue, ListValue, SourceValue


@dataclass(frozen=True)
class RestoredForm:
    values: dict[str, Any]
    unrepresented_paths: tuple[str, ...]


def _read(data, path):
    for part in path:
        if not isinstance(data, Mapping) or part not in data:
            return None
        data = data[part]
    return data


def _equal(left, right):
    if isinstance(left, (dict, list)) or isinstance(right, (dict, list)):
        return left == right
    if left == right:
        return True
    # Historical selectors were saved as either integer or numeric string.
    try:
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    except (TypeError, ValueError):
        return False


def restore_form_values(data: Mapping[str, Any], version: str = "261023") -> RestoredForm:
    """Invert current bindings; report input that cannot be represented faithfully.

    Callers first supplement missing keys and migrate legacy efficiency semantics.
    No executable expressions from uploaded JSON are evaluated.
    """
    schema = load_input_schema(version)
    fields = {field.key: field for field in schema.fields}
    values = schema.defaults()
    catalog = load_input_bindings(version)
    branches = _branch_predicates(catalog)

    def build(selected):
        output = {}
        active = {}
        for binding in catalog.bindings:
            if _conditions_match(binding, branches, selected, output):
                _write_path(output, binding.target_path, binding.evaluate(selected))
                active[binding.target_path] = binding
        return output, active

    # Resolve selectors before numbers so the correct equipment branch is used.
    # Two passes also support selectors whose controlling field occurs later.
    for _ in range(2):
        for field in schema.fields:
            choices = field.choices or ((False, True) if field.kind is FieldKind.BOOLEAN else ())
            if not choices:
                continue
            paths = {b.target_path for b in catalog.bindings if field.key in b.source_ids}
            candidates = [(choice, build({**values, field.key: choice})[0]) for choice in choices]
            affected = {path for path in paths if any(
                not _equal(_read(candidates[0][1], path), _read(output, path))
                for _, output in candidates[1:]
            )}
            if not affected:
                continue  # inactive model-specific selector
            matches = [choice for choice, output in candidates if all(
                _equal(_read(output, path), _read(data, path)) for path in affected
            )]
            if not matches:
                raise ValueError(f"{field.label}の値を入力画面へ反映できません。")
            values[field.key] = values[field.key] if values[field.key] in matches else matches[0]

    def restore(transform, value, path):
        if isinstance(transform, SourceValue):
            field = fields[transform.source_id]
            if field.kind in (FieldKind.NUMBER, FieldKind.INTEGER):
                if isinstance(value, bool):
                    raise ValueError(f"{'.'.join(path)}には数値を指定してください。")
                number = float(value)
                if not math.isfinite(number):
                    raise ValueError(f"{'.'.join(path)}には有限の数値を指定してください。")
                if field.kind is FieldKind.INTEGER and not number.is_integer():
                    raise ValueError(f"{'.'.join(path)}には整数を指定してください。")
                values[field.key] = int(number) if field.kind is FieldKind.INTEGER else number
            elif field.kind is FieldKind.TEXT:
                if not isinstance(value, str):
                    raise ValueError(f"{'.'.join(path)}には文字列を指定してください。")
                values[field.key] = value
        elif isinstance(transform, DivideValue):
            restore(transform.numerator, float(value) * transform.denominator.evaluate(values), path)
        elif isinstance(transform, ListValue):
            if not isinstance(value, list) or len(value) != len(transform.items):
                raise ValueError(f"{'.'.join(path)}の配列の要素数が正しくありません。")
            for item, item_value in zip(transform.items, value, strict=True):
                restore(item, item_value, path)

    _, active = build(values)
    for path, binding in active.items():
        restore(binding.transform, _read(data, path), path)
    rebuilt, _ = build(values)

    def differences(source, target, prefix=()):
        for key, value in source.items():
            path = (*prefix, key)
            other = target.get(key)
            if isinstance(value, Mapping) and isinstance(other, Mapping):
                yield from differences(value, other, path)
            elif not _equal(value, other):
                yield '.'.join(path)

    return RestoredForm(values, tuple(differences(data, rebuilt)))
