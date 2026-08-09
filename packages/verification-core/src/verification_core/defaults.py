from __future__ import annotations

from typing import Any

from .legacy import LegacyInputInventory, load_legacy_inventory


def default_ui_values(
    inventory: LegacyInputInventory | None = None,
) -> dict[str, Any]:
    """Return canonical UI defaults without evaluating the historical form."""

    inventory = inventory or load_legacy_inventory()
    return {item.id: item.default for item in inventory.fields}
