from __future__ import annotations

import re
from collections import defaultdict
from importlib import resources
from typing import Any, Mapping

from .legacy import LegacyInputInventory, load_legacy_inventory

_ASSIGNMENT_RE = re.compile(
    r"^(\s*)([A-Za-z_]\w*)\s*=\s*(.*?)\s+#@param\s*(.*)$"
)


def load_legacy_form_source(version: str = "260715") -> str:
    file_name = f"form_{version}.py"
    source_file = resources.files("verification_core.data").joinpath(file_name)
    return source_file.read_text(encoding="utf-8")


def default_ui_values(
    inventory: LegacyInputInventory | None = None,
) -> dict[str, Any]:
    inventory = inventory or load_legacy_inventory()
    return {item.id: item.default for item in inventory.fields}


def build_legacy_input_data(
    values: Mapping[str, Any],
    version: str = "260715",
) -> dict[str, Any]:
    """Build input_data with the trusted 260715 compatibility program.

    This bridge preserves the existing transformations while the declarative
    target-path bindings are migrated. The packaged source is trusted project
    data and must never be replaced with user-provided Python code.
    """

    source = load_legacy_form_source(version)
    transformed: list[str] = []
    occurrences: defaultdict[str, int] = defaultdict(int)

    for line in source.splitlines():
        stripped = line.strip()
        if stripped == "import jjjexperiment.main":
            continue
        if "jjjexperiment.main.calc(input_data)" in line:
            continue

        match = _ASSIGNMENT_RE.match(line)
        if match:
            indent, name, expression, _ = match.groups()
            occurrence = occurrences[name]
            occurrences[name] += 1
            field_id = f"{name}__{occurrence}"
            line = (
                f"{indent}{name} = "
                f"_values.get({field_id!r}, {expression})"
            )
        transformed.append(line)

    namespace: dict[str, Any] = {"_values": dict(values)}
    exec(
        compile("\n".join(transformed), f"legacy_form_{version}.py", "exec"),
        namespace,
    )
    input_data = namespace.get("input_data")
    if not isinstance(input_data, dict):
        raise ValueError("Legacy form did not create input_data")
    return input_data
