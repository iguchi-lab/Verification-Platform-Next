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


def parse_airflow_correction(data: dict, season: str) -> dict:
    """Parse type-specific airflow correction fields for one season."""
    coefficient_name = f'C_af_{season}'
    input_C_af = {
        'input_mode': 2,
        'dedicated_chamber': False,
        'fixed_fin_direction': False,
        coefficient_name: 1.0,
    }
    if data.get('type') in [2, 3, 4]:
        suffix = str(data['type'])

        input_C_af['input_mode'] = int(data.get(f'input_C_af_{season}{suffix}', 2))
        if input_C_af['input_mode'] == 2:
            input_C_af[coefficient_name] = float(data.get(f'{coefficient_name}{suffix}', 1.0))

        input_C_af['dedicated_chamber'] = int(data.get(f'dedicated_chamber{suffix}', 1)) == 2
        input_C_af['fixed_fin_direction'] = int(data.get(f'fixed_fin_direction{suffix}', 1)) == 2

    return input_C_af