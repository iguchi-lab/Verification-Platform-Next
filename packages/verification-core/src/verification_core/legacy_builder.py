from __future__ import annotations

import ast
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


class _LegacyFormEvaluator:
    """Evaluate only the small Python subset used by the packaged legacy form."""

    def __init__(self, values: Mapping[str, Any], overrides: Mapping[int, str]) -> None:
        self._values = values
        self._overrides = overrides
        self._namespace: dict[str, Any] = {}

    def evaluate(self, tree: ast.Module) -> dict[str, Any]:
        for statement in tree.body:
            self._validate_statement(statement)
        for statement in tree.body:
            self._execute(statement)

        input_data = self._namespace.get("input_data")
        if not isinstance(input_data, dict):
            raise ValueError("Legacy form did not create input_data")
        return input_data

    def _unsupported(self, node: ast.AST) -> ValueError:
        return ValueError(
            f"Unsupported legacy form syntax: {type(node).__name__} "
            f"at line {getattr(node, 'lineno', '?')}"
        )

    def _validate_statement(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Import):
            if (
                len(node.names) != 1
                or node.names[0].name != "jjjexperiment.main"
                or node.names[0].asname is not None
            ):
                raise self._unsupported(node)
            return
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise self._unsupported(node)
            target = node.targets[0]
            if isinstance(target, ast.Name):
                pass
            elif isinstance(target, ast.Subscript):
                self._validate_expr(target.value)
                self._validate_expr(target.slice)
            else:
                raise self._unsupported(target)
            self._validate_expr(node.value)
            return
        if isinstance(node, ast.If):
            self._validate_expr(node.test)
            for statement in (*node.body, *node.orelse):
                self._validate_statement(statement)
            return
        if isinstance(node, ast.Raise):
            if (
                node.cause is not None
                or not isinstance(node.exc, ast.Call)
                or not isinstance(node.exc.func, ast.Name)
                or node.exc.func.id != "Exception"
                or len(node.exc.args) != 1
                or node.exc.keywords
            ):
                raise self._unsupported(node)
            self._validate_expr(node.exc.args[0])
            return
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return
            if self._is_calc_call(node.value):
                return
        raise self._unsupported(node)

    def _validate_expr(self, node: ast.expr) -> None:
        if isinstance(node, ast.Constant):
            if node.value is None or isinstance(node.value, (str, int, float, bool)):
                return
        elif isinstance(node, ast.Name):
            return
        elif isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                raise self._unsupported(node)
            for key, value in zip(node.keys, node.values, strict=True):
                self._validate_expr(key)
                self._validate_expr(value)
            return
        elif isinstance(node, ast.List):
            for item in node.elts:
                self._validate_expr(item)
            return
        elif isinstance(node, ast.Subscript):
            self._validate_expr(node.value)
            self._validate_expr(node.slice)
            return
        elif isinstance(node, ast.IfExp):
            self._validate_expr(node.test)
            self._validate_expr(node.body)
            self._validate_expr(node.orelse)
            return
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            self._validate_expr(node.operand)
            return
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            self._validate_expr(node.left)
            self._validate_expr(node.right)
            return
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            for value in node.values:
                self._validate_expr(value)
            return
        elif isinstance(node, ast.Compare):
            if (
                len(node.ops) == 1
                and isinstance(node.ops[0], (ast.Eq, ast.In))
                and len(node.comparators) == 1
            ):
                self._validate_expr(node.left)
                self._validate_expr(node.comparators[0])
                return
        raise self._unsupported(node)

    def _execute(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Import):
            if len(node.names) != 1 or node.names[0].name != "jjjexperiment.main":
                raise self._unsupported(node)
            return

        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise self._unsupported(node)
            value = self._eval(node.value)
            field_id = self._overrides.get(node.lineno)
            if field_id is not None:
                value = self._values.get(field_id, value)
            self._assign(node.targets[0], value)
            return

        if isinstance(node, ast.If):
            branch = node.body if self._eval(node.test) else node.orelse
            for statement in branch:
                self._execute(statement)
            return

        if isinstance(node, ast.Raise):
            if (
                node.cause is not None
                or not isinstance(node.exc, ast.Call)
                or not isinstance(node.exc.func, ast.Name)
                or node.exc.func.id != "Exception"
                or len(node.exc.args) != 1
                or node.exc.keywords
            ):
                raise self._unsupported(node)
            message = self._eval(node.exc.args[0])
            if not isinstance(message, str):
                raise self._unsupported(node)
            raise Exception(message)

        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return
            if self._is_calc_call(node.value):
                return
            raise self._unsupported(node)

        raise self._unsupported(node)

    @staticmethod
    def _is_calc_call(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Call)
            and not node.keywords
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "input_data"
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "calc"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "main"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "jjjexperiment"
        )

    def _assign(self, target: ast.expr, value: Any) -> None:
        if isinstance(target, ast.Name):
            self._namespace[target.id] = value
            return
        if isinstance(target, ast.Subscript):
            container = self._eval(target.value)
            key = self._eval(target.slice)
            if not isinstance(container, dict) or not isinstance(key, str):
                raise self._unsupported(target)
            container[key] = value
            return
        raise self._unsupported(target)

    def _eval(self, node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            if node.value is None or isinstance(node.value, (str, int, float, bool)):
                return node.value
            raise self._unsupported(node)

        if isinstance(node, ast.Name):
            if node.id not in self._namespace:
                raise ValueError(
                    f"Unknown legacy form name {node.id!r} at line {node.lineno}"
                )
            return self._namespace[node.id]

        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                raise self._unsupported(node)
            return {
                self._eval(key): self._eval(value)
                for key, value in zip(node.keys, node.values, strict=True)
            }

        if isinstance(node, ast.List):
            return [self._eval(item) for item in node.elts]

        if isinstance(node, ast.Subscript):
            container = self._eval(node.value)
            key = self._eval(node.slice)
            if not isinstance(container, dict) or not isinstance(key, str):
                raise self._unsupported(node)
            return container[key]

        if isinstance(node, ast.IfExp):
            return self._eval(node.body if self._eval(node.test) else node.orelse)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            operand = self._eval(node.operand)
            if isinstance(operand, bool) or not isinstance(operand, (int, float)):
                raise self._unsupported(node)
            return -operand

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = self._eval(node.left)
            right = self._eval(node.right)
            if (
                isinstance(left, bool)
                or isinstance(right, bool)
                or not isinstance(left, (int, float))
                or not isinstance(right, (int, float))
            ):
                raise self._unsupported(node)
            return left / right

        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            result = self._eval(node.values[0])
            for value in node.values[1:]:
                if not result:
                    return result
                result = self._eval(value)
            return result

        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise self._unsupported(node)
            left = self._eval(node.left)
            right = self._eval(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.In):
                if not isinstance(left, str) or not isinstance(right, str):
                    raise self._unsupported(node)
                return left in right
            raise self._unsupported(node)

        raise self._unsupported(node)


def _parameter_overrides(source: str) -> dict[int, str]:
    occurrences: defaultdict[str, int] = defaultdict(int)
    overrides: dict[int, str] = {}
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = _ASSIGNMENT_RE.match(line)
        if match:
            _, name, _, _ = match.groups()
            occurrence = occurrences[name]
            occurrences[name] += 1
            overrides[line_number] = f"{name}__{occurrence}"
    return overrides


def build_legacy_input_data(
    values: Mapping[str, Any],
    version: str = "260715",
) -> dict[str, Any]:
    """Build input_data with a restricted evaluator for the 260715 form."""

    source = load_legacy_form_source(version)
    try:
        tree = ast.parse(source, filename=f"legacy_form_{version}.py")
    except SyntaxError as error:
        raise ValueError(f"Invalid legacy form syntax: {error}") from error
    evaluator = _LegacyFormEvaluator(values, _parameter_overrides(source))
    return evaluator.evaluate(tree)
