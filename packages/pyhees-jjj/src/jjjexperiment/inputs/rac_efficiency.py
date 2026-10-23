"""Independent RAC efficiency selection, with the saved-JSON legacy contract."""

from jjjexperiment.v_min_input.validation import require_positive_finite


def resolve_efficiency(data, season, q_rtd_C, legacy_cooling_efficiency=None):
    from pyhees.section4_3_a import get_e_rtd_C, get_e_rtd_H

    label = '暖房' if season == 'H' else '冷房'
    mode = data.get('rac_efficiency_mode')
    if 'rac_efficiency_mode' not in data:
        # Old JSON coupled capacity and COP. Keep that precedence, including the
        # old heating fallback when no heating efficiency selector was saved.
        if int(data.get('input_rac_performance', 1)) == 2:
            return float(data[f'e_rac_rtd_{season}'])
        if season == 'H' and 'input_mode' not in data:
            return get_e_rtd_H(legacy_cooling_efficiency)
        mode = 'class' if int(data.get('input_mode', 1)) == 2 else 'default'
    elif mode not in ('default', 'class', 'direct'):
        raise ValueError(f'{label}の効率の設定方法が不正です。')

    if mode == 'direct':
        return require_positive_finite(data[f'e_rac_rtd_{season}'], f'定格{label}COP')
    e_class = None
    if mode == 'class':
        e_class = {1: 'い', 2: 'ろ', 3: 'は'}.get(int(data.get('mode', 1)))
        if e_class is None and 'rac_efficiency_mode' in data:
            raise ValueError(f'{label}の効率区分は い・ろ・は から選択してください。')
    efficiency = get_e_rtd_C(e_class, q_rtd_C)
    if season == 'H':
        efficiency = get_e_rtd_H(efficiency)
    if 'rac_efficiency_mode' in data:
        require_positive_finite(efficiency, f'算定した定格{label}COP')
    return efficiency


def validate_capacity(data, season, rated, maximum):
    """Validate the new input contract without changing historical input behavior."""
    if 'rac_efficiency_mode' not in data:
        return
    label = '暖房' if season == 'H' else '冷房'
    require_positive_finite(rated, f'定格{label}能力 [W]')
    require_positive_finite(maximum, f'最大{label}能力 [W]')
    if maximum < rated:
        raise ValueError(f'最大{label}能力は定格{label}能力以上にしてください。')
