"""JSON-to-form migration without running a simulation."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jjjexperiment.calculation_method import prepare_input
from jjjexperiment.inputs.cooling import CRACSpecification as CoolingRAC
from jjjexperiment.inputs.heating import CRACSpecification as HeatingRAC
from verification_core import load_compatible_input_json
from verification_core.form_import import restore_form_values


@dataclass(frozen=True)
class ImportedForm:
    values: dict[str, Any]
    notes: tuple[str, ...]


def load_json_into_form(path: str | Path | None) -> ImportedForm:
    if path is None:
        raise ValueError("読み込むJSONファイルを選択してください。")
    file = Path(path)
    if not file.is_file():
        raise ValueError("選択したJSONファイルを読み取れません。")
    if file.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("入力JSONは5 MB以下にしてください。")
    compatible = load_compatible_input_json(file.read_bytes())
    data = deepcopy(compatible.input_data)
    notes = []
    if compatible.supplemented_paths:
        notes.append(f"不足していた{len(compatible.supplemented_paths)}項目は初期値で補完しました。")
    # Normalize numeric equipment selectors before resolving legacy RAC semantics.
    for key in ('H_A', 'C_A'):
        kind = data[key]['type']
        if isinstance(kind, bool) or float(kind) not in (1, 2, 3, 4):
            raise ValueError(f'{key}.typeの設備方式が正しくありません。')
        data[key]['type'] = int(kind)
    if data.get('calculation_method') == 'tg':
        data = prepare_input(data)
        for key in ('H_A', 'C_A'):
            if data[key]['type'] == 2:
                data[key]['rac_efficiency_mode'] = 'default'
                data[key]['input_mode'] = 1
        data.pop('tg_specification', None)  # generated provenance, not a form input
    else:
        cold = CoolingRAC.from_dict(data['C_A'], float(data['A_A']))
        hot = HeatingRAC.from_dict(data['H_A'], cold.q_rtd, cold.q_max, cold.e_rtd)
        for season, spec in (('C', cold), ('H', hot)):
            equipment = data[f'{season}_A']
            if equipment['type'] != 2 or 'rac_efficiency_mode' in equipment:
                continue
            mode = 'class' if int(equipment.get('input_mode', 1)) == 2 else 'default'
            if int(equipment.get('input_rac_performance', 1)) == 2:
                mode = 'direct'
            elif season == 'H' and 'input_mode' not in equipment:
                cooling = data['C_A']
                mode = cooling.get('rac_efficiency_mode', 'default') if cooling['type'] == 2 else 'default'
                if mode == 'direct':
                    notes.append('旧JSONの暖房COPは読込み時の冷房COPから換算した値で固定しました。冷房COPを変更する場合は暖房COPも確認してください。')
                if mode == 'class':
                    equipment['mode'] = cooling.get('mode', 1)
            equipment['rac_efficiency_mode'] = mode
            equipment['input_mode'] = 2 if mode == 'class' else 1
            equipment.setdefault('mode', 1)
            if mode == 'direct':
                equipment[f'e_rac_rtd_{season}'] = spec.e_rtd
            notes.append(f"旧JSONの{'暖房' if season == 'H' else '冷房'}効率を、同じCOPになる設定に変換しました。")
        # Reject legacy values that cannot satisfy the editable current contract.
        checked_cold = CoolingRAC.from_dict(data['C_A'], float(data['A_A']))
        HeatingRAC.from_dict(data['H_A'], checked_cold.q_rtd, checked_cold.q_max, checked_cold.e_rtd)
    if any(data.get(key, '-') != '-' for key in ('climateFile', 'loadFile')):
        notes.append("外部の気象・負荷ファイル本体はJSONに含まれません。①のファイル指定を確認してください。")
    restored = restore_form_values(data)
    if restored.unrepresented_paths:
        paths = '、'.join(restored.unrepresented_paths[:8])
        raise ValueError(
            f"画面で再現できない設定があります：{paths}。入力欄は変更していません。"
            "元のJSONをそのまま実行する場合は「JSONファイルをアップロードして計算」を使用してください。"
        )
    return ImportedForm(restored.values, tuple(notes))
