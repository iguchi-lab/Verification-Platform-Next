from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from .bindings import InputBinding, InputBindingCatalog, load_input_bindings
from .legacy import load_legacy_inventory
from .legacy_builder import default_ui_values
from .predicates import BranchPredicate, Predicate, parse_binding_predicate

_ConditionPart = tuple[str, int, str]
_ConditionKey = tuple[_ConditionPart, ...]


def build_input_data(
    values: Mapping[str, Any],
    version: str = "260724",
) -> dict[str, Any]:
    """Build input_data by applying the declarative binding catalog in source order."""

    inventory = load_legacy_inventory(version)
    resolved_values = default_ui_values(inventory)
    resolved_values.update(values)
    catalog = load_input_bindings(version)
    branches = _branch_predicates(catalog)
    input_data: dict[str, Any] = {}

    for binding in catalog.bindings:
        if _conditions_match(binding, branches, resolved_values, input_data):
            _write_path(input_data, binding.target_path, binding.evaluate(resolved_values))
    return input_data


def _branch_predicates(
    catalog: InputBindingCatalog,
) -> dict[_ConditionKey, BranchPredicate]:
    sources: defaultdict[_ConditionKey, set[str]] = defaultdict(set)
    by_parent: defaultdict[_ConditionKey, set[_ConditionKey]] = defaultdict(set)

    for binding in catalog.bindings:
        prefix: _ConditionKey = ()
        for condition in binding.conditions:
            current = (condition.kind, condition.line, condition.expression)
            key = (*prefix, current)
            sources[key].update(binding.source_ids)
            by_parent[prefix].add(key)
            prefix = key

    result: dict[_ConditionKey, BranchPredicate] = {}
    for siblings in by_parent.values():
        previous: list[Predicate] = []
        for key in sorted(siblings, key=lambda item: item[-1][1]):
            kind, _, expression = key[-1]
            if kind == "if":
                previous = []
            if kind not in {"if", "elif", "else"}:
                raise ValueError(f"Unsupported binding condition kind: {kind}")
            current = (
                None
                if kind == "else"
                else parse_binding_predicate(
                    expression,
                    tuple(sorted(sources[key])),
                )
            )
            result[key] = BranchPredicate(current=current, previous=tuple(previous))
            if current is not None:
                previous.append(current)
    return result


def _conditions_match(
    binding: InputBinding,
    branches: Mapping[_ConditionKey, BranchPredicate],
    values: Mapping[str, Any],
    input_data: Mapping[str, Any],
) -> bool:
    prefix: _ConditionKey = ()
    for condition in binding.conditions:
        prefix = (*prefix, (condition.kind, condition.line, condition.expression))
        if not branches[prefix].matches(values, input_data):
            return False
    return True


def _write_path(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    if not path:
        raise ValueError("Binding target path cannot be empty")
    current = data
    for part in path[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[path[-1]] = value
