"""Production regressions: run multiple cases in the same application process."""
import asyncio
from hashlib import sha256
import json
from pathlib import Path

import pytest

from jjjexperiment import release
from verification_app.form_app import _default_service, build_app
from verification_app.services import CalculationService
from verification_core import build_input_data, load_compatible_input_json


def test_sequential_floor_cases_use_their_own_ground_resistance(tmp_path, monkeypatch):
    monkeypatch.setenv('VERIFICATION_OUTPUT_DIR', str(tmp_path))
    service = _default_service()
    settings = {
        'change_underfloor_temperature_C__0': True, 'underfloor_ventilation__0': True,
        'r_A_ufvnt__0': 100, 'input_ufac_consts__0': True,
    }

    def annual(values):
        result = service.run(settings | values, include_graphs=False)
        assert result.succeeded, result.log
        return (result.annual_summary.heating.primary_energy_mj,
                result.annual_summary.cooling.primary_energy_mj)

    before = annual({'R_g__0': 0.15})
    after = annual({'R_g__0': 0.30})
    assert after == pytest.approx((33499.540208035134, 16487.757479377957))
    assert after[0] != pytest.approx(before[0])
    assert annual({'R_g__0': 0.30}) == after
    assert annual({'R_g__0': 0.30, 'input_ufac_consts__0': False}) == annual({
        'R_g__0': 0.15, 'input_ufac_consts__0': False,
    })


def test_repeat_heating_export_and_saved_json_are_reproducible(tmp_path, monkeypatch):
    monkeypatch.setenv('VERIFICATION_OUTPUT_DIR', str(tmp_path))
    service = _default_service()
    settings = {'case_name__0': 'ケース[1]', 'change_underfloor_temperature_H__0': True}
    hashes = []
    for _ in range(2):
        result = service.run(settings, include_graphs=False)
        assert result.succeeded, result.log
        files = [Path(name) for name in result.files]
        saved = json.loads(next(p for p in files if p.name.endswith('_input.json')).read_text())
        manifest = json.loads(next(p for p in files if p.name.endswith('_manifest.json')).read_text())
        assert manifest['input_sha256'] == release.input_sha256(saved)
        assert saved == result.input_data
        exported = service.export_csv(result)
        diagnostics = next(Path(p) for p in exported.files if p.endswith('_H_output_uf.csv'))
        hashes.append(sha256(diagnostics.read_bytes()).digest())
    assert hashes[0] == hashes[1]


def test_capacity_arrays_and_individual_keys_are_isolated_at_engine_entry(tmp_path, monkeypatch):
    import jjjexperiment.main as engine
    from jjjexperiment import constants

    monkeypatch.chdir(tmp_path)
    observed = []

    class Injector:
        def call_with_injection(self, _fn):
            observed.append(tuple(constants.C1_BR_R_i))
            if fail:
                raise ValueError('interrupted')

    monkeypatch.setattr(engine.jjj_ipt_di, 'create_injector_from_json', lambda *_: Injector())
    fail = False
    defaults = build_input_data({})
    edited = build_input_data({'c1_BR_R_1__0': 1787352})
    engine.calc(edited)
    assert observed[-1] == tuple(edited['C1_BR_R_i'])
    # A pre-array JSON may specify only one room. Form restoration and direct
    # execution must see the same converted five-room vector.
    old = {'C1_BR_R_2': 712345}
    migrated = load_compatible_input_json(json.dumps(old)).input_data
    assert migrated['C1_BR_R_i'][1] == 712345
    assert 'C1_BR_R_2' not in migrated
    fail = True
    with pytest.raises(ValueError, match='interrupted'):
        engine.calc(old)
    assert observed[-1][1] == 712345
    fail = False
    engine.calc(defaults)
    assert observed[-1] == tuple(defaults['C1_BR_R_i'])
    assert load_compatible_input_json(json.dumps(edited | old)).input_data['C1_BR_R_i'] == edited['C1_BR_R_i']


@pytest.mark.parametrize('key', ['climateFile', 'loadFile'])
@pytest.mark.parametrize('reference', ['http://127.0.0.1/x.csv', 'file:///tmp/x.csv', '/tmp/x.csv',
                                       '../x.csv', r'C:\temp\x.csv', 'missing.csv'])
def test_web_form_and_uploaded_json_reject_unattached_external_data(tmp_path, key, reference):
    service = CalculationService(lambda _: pytest.fail('engine was reached'), lambda: 'test', workdir=tmp_path)
    path = tmp_path / 'saved.json'
    path.write_text(json.dumps({key: reference}))
    runs = (service.run({key + '__0': reference}), service.run_uploaded_json(path))
    for result in runs:
        assert not result.succeeded and result.run_id is None
        assert '①' in result.log


def test_csv_uploads_are_local_to_one_case_and_bound_to_the_saved_json(tmp_path):
    climate = (Path(__file__).resolve().parents[1] / 'packages/pyhees-jjj/src/pyhees/data/climate/climateData_6.csv').read_bytes()
    load = (','.join(str(i) for i in range(36)) + '\n' + ('0,' * 35 + '1\n') * 8760).encode()
    calls = []

    def calculate(data):
        calls.append(dict(data))
        assert Path(data['climateFile']).read_bytes() == climate
        assert Path(data['loadFile']).read_bytes() == load

    service = CalculationService(calculate, lambda: 'test', workdir=tmp_path)
    initial = service.run({}, climate_csv=climate, load_csv=load)
    assert initial.succeeded, initial.log
    saved = tmp_path / 'saved.json'
    saved.write_text(json.dumps(initial.input_data))
    repeated = service.run_uploaded_json(saved, climate_csv=climate, load_csv=load)
    assert repeated.succeeded and calls[1] == calls[0]
    assert repeated.artifact_dir != initial.artifact_dir
    swapped = service.run_uploaded_json(saved, climate_csv=climate, load_csv=load.replace(b'1\n', b'2\n'))
    assert not swapped.succeeded and '一致しません' in swapped.log
    assert not service.run_uploaded_json(saved).succeeded
    assert not service.run({}, load_csv=b'header\n0\n').succeeded
    assert len(calls) == 2


def test_gradio_rejects_remote_file_metadata_before_caching():
    app = build_app()
    remote = {'path': 'http://127.0.0.1/test.csv', 'meta': {'_type': 'gradio.FileData'}}
    with pytest.raises(ValueError, match='アップロード済み'):
        asyncio.run(app.preprocess_data(None, [remote], None))
