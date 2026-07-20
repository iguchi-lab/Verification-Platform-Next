from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class ValueTransform(Protocol):
    def evaluate(self, values: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True, slots=True)
class LiteralValue:
    value: Any

    def evaluate(self, values: Mapping[str, Any]) -> Any:
        return self.value


@dataclass(frozen=True, slots=True)
class SourceValue:
    source_id: str

    def evaluate(self, values: Mapping[str, Any]) -> Any:
        try:
            return values[self.source_id]
        except KeyError as error:
            raise ValueError(f"Missing input value: {self.source_id}") from error


@dataclass(frozen=True, slots=True)
class ListValue:
    items: tuple[ValueTransform, ...]

    def evaluate(self, values: Mapping[str, Any]) -> list[Any]:
        return [item.evaluate(values) for item in self.items]


@dataclass(frozen=True, slots=True)
class EmptyDictValue:
    def evaluate(self, values: Mapping[str, Any]) -> dict[str, Any]:
        return {}


@dataclass(frozen=True, slots=True)
class EqualsCondition:
    value: ValueTransform
    expected: ValueTransform

    def evaluate(self, values: Mapping[str, Any]) -> bool:
        return self.value.evaluate(values) == self.expected.evaluate(values)


@dataclass(frozen=True, slots=True)
class TruthyCondition:
    value: ValueTransform

    def evaluate(self, values: Mapping[str, Any]) -> bool:
        return bool(self.value.evaluate(values))


@dataclass(frozen=True, slots=True)
class ConditionalValue:
    condition: EqualsCondition | TruthyCondition
    when_true: ValueTransform
    when_false: ValueTransform

    def evaluate(self, values: Mapping[str, Any]) -> Any:
        branch = self.when_true if self.condition.evaluate(values) else self.when_false
        return branch.evaluate(values)


@dataclass(frozen=True, slots=True)
class DivideValue:
    numerator: ValueTransform
    denominator: ValueTransform

    def evaluate(self, values: Mapping[str, Any]) -> Any:
        return self.numerator.evaluate(values) / self.denominator.evaluate(values)


class _BindingExpressionParser:
    def __init__(self, source_ids: tuple[str, ...]) -> None:
        self._source_ids = source_ids

    def parse(self, expression: str) -> ValueTransform:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as error:
            raise ValueError(f"Invalid binding expression: {expression}") from error
        return self._parse_value(tree.body)

    def _parse_value(self, node: ast.expr) -> ValueTransform:
        if isinstance(node, ast.Constant):
            if node.value is None or isinstance(node.value, (str, int, float, bool)):
                return LiteralValue(node.value)
        elif isinstance(node, ast.Name):
            return SourceValue(self._next_source(node))
        elif isinstance(node, ast.Dict) and not node.keys and not node.values:
            return EmptyDictValue()
        elif isinstance(node, ast.List):
            return ListValue(tuple(self._parse_value(item) for item in node.elts))
        elif isinstance(node, ast.IfExp):
            return ConditionalValue(
                condition=self._parse_condition(node.test),
                when_true=self._parse_value(node.body),
                when_false=self._parse_value(node.orelse),
            )
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return DivideValue(
                numerator=self._parse_value(node.left),
                denominator=self._parse_value(node.right),
            )
        raise self._unsupported(node)

    def _parse_condition(self, node: ast.expr) -> EqualsCondition | TruthyCondition:
        if isinstance(node, ast.Name):
            return TruthyCondition(self._parse_value(node))
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and len(node.comparators) == 1
        ):
            return EqualsCondition(
                value=self._parse_value(node.left),
                expected=self._parse_value(node.comparators[0]),
            )
        raise self._unsupported(node)

    def _next_source(self, node: ast.Name) -> str:
        candidates = tuple(
            source_id
            for source_id in self._source_ids
            if source_id.rsplit("__", 1)[0] == node.id
        )
        if len(candidates) != 1:
            raise ValueError(
                f"Binding expression name {node.id!r} must have one source ID, "
                f"found {len(candidates)}"
            )
        return candidates[0]

    @staticmethod
    def _unsupported(node: ast.AST) -> ValueError:
        return ValueError(f"Unsupported binding expression syntax: {type(node).__name__}")


def parse_binding_expression(
    expression: str,
    source_ids: tuple[str, ...],
) -> ValueTransform:
    return _BindingExpressionParser(source_ids).parse(expression)
