"""Resolve Web CSV inputs from uploaded bytes, never from client-supplied paths."""
import csv
import io
import math
import re
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath

MAX_CSV_BYTES = 20 * 1024 * 1024
CSV_SLOTS = {'climateFile': ('気象', 'climate'), 'loadFile': ('暖冷房負荷', 'load')}


_CLIMATE_COLUMNS = (
    '外気温[℃]', '外気絶対湿度 [kg/kgDA]', '法線面直達日射量 [W/m2]',
    '水平面天空日射量 [W/m2]', '太陽高度角[度]', '太陽方位角[度]',
)


def _validate_csv(payload: bytes, key: str, label: str) -> None:
    climate = key == 'climateFile'
    encoding = 'shift_jis' if climate else 'utf-8-sig'
    try:
        with io.TextIOWrapper(io.BytesIO(payload), encoding=encoding, newline='') as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            if climate:
                columns = [header.index(name) for name in _CLIMATE_COLUMNS]
            else:
                if len(header) != 36:
                    raise ValueError('ヘッダーは36列必要です。')
                columns = range(36)
            count = 0
            for row in reader:
                if not row:
                    continue
                count += 1
                if count > 8760 or len(row) != len(header):
                    raise ValueError(f'{count}行目の行数または列数が不正です。')
                if not all(math.isfinite(float(row[i])) for i in columns):
                    raise ValueError(f'{count}行目に有限でない数値があります。')
            if count != 8760:
                raise ValueError(f'8760時間分が必要です（入力は{count}行）。')
    except (UnicodeError, csv.Error, ValueError) as error:
        raise ValueError(f'{label}CSVの形式を確認してください（{encoding}）。{error}') from error


def prepare_external_csv(data, uploads, *, from_json):
    """Return files for the new run directory and record portable names in its input."""
    files = {}
    for key, (label, stem) in CSV_SLOTS.items():
        reference = data.get(key, '-')
        payload = uploads.get(key)
        if reference == '-' and (from_json or payload is None):
            continue
        if reference != '-' and (
            not isinstance(reference, str)
            or PurePosixPath(reference).name != reference
            or PureWindowsPath(reference).name != reference
            or ':' in reference or '\x00' in reference
            or not reference.lower().endswith('.csv')
        ):
            raise ValueError(f'{label}データには①でCSVを添付してください。URLやパスは使用できません。')
        if payload is None:
            raise ValueError(f'{label}データのCSV（{reference}）を①で添付してください。')
        if not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_CSV_BYTES:
            raise ValueError(f'{label}データには空でない20 MiB以下のCSVを添付してください。')
        name = f'{stem}-{sha256(payload).hexdigest()}.csv'
        if from_json and re.fullmatch(rf'{stem}-[0-9a-f]{{64}}\.csv', reference) and reference != name:
            raise ValueError(f'{label}データが保存JSONのCSVと一致しません。')
        _validate_csv(payload, key, label)
        data[key] = name
        files[name] = payload
    return files
