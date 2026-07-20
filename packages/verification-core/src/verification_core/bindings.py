from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

from .legacy import LegacyInputInventory, load_legacy_inventory


@dataclass(frozen=True, slots=True)
class BindingCondition:
    """One source-level branch guarding a legacy input_data assignment."""

    kind: str
    expression: str
    line: int


@dataclass(frozen=True, slots=True)
class InputBinding:
    """Traceable mapping from UI fields to one legacy input_data assignment."""

    line: int
    target_path: tuple[str, ...]
    expression: str
    conditions: tuple[BindingCondition, ...]
    source_ids: tuple[str, ...]

    @property
    def dotted_target(self) -> str:
        return ".".join(self.target_path)


@dataclass(frozen=True)
class InputBindingCatalog:
    version: str
    bindings: tuple[InputBinding, ...]

    @property
    def source_ids(self) -> frozenset[str]:
        return frozenset(
            source_id
            for binding in self.bindings
            for source_id in binding.source_ids
        )

    def for_target(self, *path: str) -> tuple[InputBinding, ...]:
        target = tuple(path)
        return tuple(binding for binding in self.bindings if binding.target_path == target)

    def validate(
        self,
        *,
        expected_count: int | None = None,
        inventory: LegacyInputInventory | None = None,
    ) -> None:
        if expected_count is not None and len(self.bindings) != expected_count:
            raise ValueError(
                f"Expected {expected_count} bindings, found {len(self.bindings)}"
            )

        for binding in self.bindings:
            if not binding.target_path:
                raise ValueError(f"Binding at line {binding.line} has an empty target")
            if not binding.expression.strip():
                raise ValueError(
                    f"Binding for {binding.dotted_target} has an empty expression"
                )
            if binding.line < 1:
                raise ValueError(
                    f"Binding for {binding.dotted_target} has an invalid line number"
                )

        if inventory is None:
            return

        inventory_ids = {field.id for field in inventory.fields}
        unknown = self.source_ids - inventory_ids
        missing = inventory_ids - self.source_ids
        if unknown:
            raise ValueError(f"Bindings contain unknown source IDs: {sorted(unknown)}")
        if missing:
            raise ValueError(f"Inventory fields have no binding: {sorted(missing)}")


def load_input_bindings(version: str = "260715") -> InputBindingCatalog:
    file_name = f"input_bindings_{version}.json"
    data_file = resources.files("verification_core.data").joinpath(file_name)
    with data_file.open(encoding="utf-8") as stream:
        payload = json.load(stream)

    bindings = tuple(
        InputBinding(
            line=int(item["line"]),
            target_path=tuple(item["target_path"]),
            expression=item["expression"],
            conditions=tuple(
                BindingCondition(
                    kind=condition["kind"],
                    expression=condition["expression"],
                    line=int(condition["line"]),
                )
                for condition in item["conditions"]
            ),
            source_ids=tuple(item["source_ids"]),
        )
        for item in payload["bindings"]
    )
    catalog = InputBindingCatalog(version=payload["version"], bindings=bindings)
    catalog.validate(
        expected_count=int(payload["binding_count"]),
        inventory=load_legacy_inventory(version),
    )
    return catalog
