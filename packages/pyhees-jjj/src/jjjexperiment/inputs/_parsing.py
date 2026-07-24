from collections.abc import Callable
from typing import Any

FieldSpec = tuple[str, str, Callable[[Any], Any]]


def parse_present_fields(data: dict, fields: tuple[FieldSpec, ...]) -> dict:
    """入力に存在するフィールドを定義順に変換する。"""
    kwargs = {}
    for source_name, target_name, converter in fields:
        if source_name in data:
            kwargs[target_name] = converter(data[source_name])
    return kwargs