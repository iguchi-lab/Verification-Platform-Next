from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


class Operand(Protocol):
    def evaluate(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> Any: ...


class Predicate(Protocol):
    def matches(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class LiteralOperand:
    value: Any

    def evaluate(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> Any:
        return self.value


@dataclass(frozen=True, slots=True)
class SourceOperand:
    source_id: str

    def evaluate(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> Any:
        try:
            return values[self.source_id]
        except KeyError as error:
            raise ValueError(f"Missing input value: {self.source_id}") from error


@dataclass(frozen=True, slots=True)
class OutputOperand:
    path: tuple[str, ...]

    def evaluate(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> Any:
        current: Any = input_data
        for part in self.path:
            if not isinstance(current, Mapping) or part not in current:
                raise ValueError(f"Missing output value: {'.'.join(self.path)}")
            current = current[part]
        return current


@dataclass(frozen=True, slots=True)
class EqualsPredicate:
    left: Operand
    right: Operand

    def matches(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> bool:
        return self.left.evaluate(values, input_data) == self.right.evaluate(
            values,
            input_data,
        )


@dataclass(frozen=True, slots=True)
class ContainsPredicate:
    member: Operand
    container: Operand

    def matches(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> bool:
        member = self.member.evaluate(values, input_data)
        container = self.container.evaluate(values, input_data)
        if not isinstance(member, str) or not isinstance(container, str):
            raise ValueError("Binding containment conditions require strings")
        return member in container


@dataclass(frozen=True, slots=True)
class AndPredicate:
    items: tuple[Predicate, ...]

    def matches(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> bool:
        return all(item.matches(values, input_data) for item in self.items)


@dataclass(frozen=True, slots=True)
class BranchPredicate:
    current: Predicate | None
    previous: tuple[Predicate, ...] = ()

    def matches(
        self,
        values: Mapping[str, Any],
        input_data: Mapping[str, Any],
    ) -> bool:
        if any(item.matches(values, input_data) for item in self.previous):
            return False
        return self.current is None or self.current.matches(values, input_data)


class _PredicateParser:
    def __init__(self, source_ids: tuple[str, ...]) -> None:
        self._source_ids = source_ids

    def parse(self, expression: str) -> Predicate:
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as error:
            raise ValueError(f"Invalid binding condition: {expression}") from error
        return self._parse_predicate(tree.body)

    def _parse_predicate(self, node: ast.expr) -> Predicate:
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
            return AndPredicate(tuple(self._parse_predicate(item) for item in node.values))
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and len(node.comparators) == 1
        ):
            left = self._parse_operand(node.left)
            right = self._parse_operand(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq):
                return EqualsPredicate(left, right)
            if isinstance(node.ops[0], ast.In):
                return ContainsPredicate(left, right)
        raise self._unsupported(node)

    def _parse_operand(self, node: ast.expr) -> Operand:
        if isinstance(node, ast.Constant) and isinstance(
            node.value,
            (str, int, float, bool),
        ):
            return LiteralOperand(node.value)
        if isinstance(node, ast.Name):
            candidates = tuple(
                source_id
                for source_id in self._source_ids
                if source_id.rsplit("__", 1)[0] == node.id
            )
            if len(candidates) != 1:
                raise ValueError(
                    f"Binding condition name {node.id!r} must have one source ID, "
                    f"found {len(candidates)}"
                )
            return SourceOperand(candidates[0])
        path = self._output_path(node)
        if path is not None:
            return OutputOperand(path)
        raise self._unsupported(node)

    def _output_path(self, node: ast.expr) -> tuple[str, ...] | None:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Subscript):
            if not isinstance(current.slice, ast.Constant) or not isinstance(
                current.slice.value,
                str,
            ):
                return None
            parts.append(current.slice.value)
            current = current.value
        if not isinstance(current, ast.Name) or current.id != "input_data":
            return None
        return tuple(reversed(parts))

    @staticmethod
    def _unsupported(node: ast.AST) -> ValueError:
        return ValueError(f"Unsupported binding condition syntax: {type(node).__name__}")


def parse_binding_predicate(
    expression: str,
    source_ids: tuple[str, ...],
) -> Predicate:
    return _PredicateParser(source_ids).parse(expression)
