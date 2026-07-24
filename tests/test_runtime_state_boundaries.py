import ast
import os
from pathlib import Path

import verification_app.services as services


class _RecordingLock:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        self.events.append("lock-enter")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.events.append("lock-exit")


def test_calculation_services_share_process_cwd_lock(monkeypatch, tmp_path):
    events = []
    lock = _RecordingLock(events)
    monkeypatch.setattr(services, "_CALCULATION_CWD_LOCK", lock)

    def calculate(input_data):
        events.append(("calculate", Path.cwd()))

    first = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path / "first",
    )
    second = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path / "second",
    )

    assert first.run({}).succeeded
    assert second.run({}).succeeded
    assert events == [
        "lock-enter",
        ("calculate", (tmp_path / "first").resolve()),
        "lock-exit",
        "lock-enter",
        ("calculate", (tmp_path / "second").resolve()),
        "lock-exit",
    ]


def test_calculation_service_restores_cwd_after_failure(tmp_path):
    previous_cwd = Path.cwd()

    def calculate(input_data):
        assert Path.cwd() == tmp_path.resolve()
        raise RuntimeError("calculation failed")

    service = services.CalculationService(
        calculate,
        lambda: "v1",
        workdir=tmp_path,
    )

    result = service.run({})

    assert not result.succeeded
    assert "RuntimeError: calculation failed" in result.log
    assert Path.cwd() == previous_cwd
    assert Path(os.getcwd()) == previous_cwd


_EXPECTED_GLOBAL_SETTERS = {
    "_set_C1_BR_R_i",
    "_set_C1_NR_R",
    "_set_C_A_A_e_hex_large",
    "_set_C_A_A_e_hex_small",
    "_set_C_A_A_f_hex_large",
    "_set_C_A_A_f_hex_small",
    "_set_C_A_airvolume_coeff",
    "_set_C_A_airvolume_maximum",
    "_set_C_A_airvolume_minimum",
    "_set_C_A_compressor_coeff",
    "_set_C_A_fan_coeff",
    "_set_C_A_heat_transfer_coeff",
    "_set_C_V_fan_dsgn_C",
    "_set_C_V_fan_dsgn_H",
    "_set_C_df_H_d_t_defrost_ductcentral",
    "_set_C_df_H_d_t_defrost_rac",
    "_set_C_hm_C",
    "_set_H_A_A_e_hex_large",
    "_set_H_A_A_e_hex_small",
    "_set_H_A_A_f_hex_large",
    "_set_H_A_A_f_hex_small",
    "_set_H_A_airvolume_coeff",
    "_set_H_A_airvolume_maximum",
    "_set_H_A_airvolume_minimum",
    "_set_H_A_compressor_coeff",
    "_set_H_A_fan_coeff",
    "_set_R_g",
    "_set_Theta_hs_out_max_H_d_t_limit",
    "_set_Theta_hs_out_min_C_d_t_limit",
    "_set_change_heat_source_outlet_required_temperature",
    "_set_change_supply_volume_before_vav_adjust",
    "_set_defrost_humid_ductcentral",
    "_set_defrost_humid_rac",
    "_set_defrost_temp_ductcentral",
    "_set_defrost_temp_rac",
    "_set_phi_i",
    "_set_q_rtd_C_limit",
}


class _BoundaryVisitor(ast.NodeVisitor):
    def __init__(self):
        self.function_names = []
        self.global_sites = []
        self.chdir_sites = []

    def visit_FunctionDef(self, node):
        self.function_names.append(node.name)
        self.generic_visit(node)
        self.function_names.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Global(self, node):
        function_name = self.function_names[-1] if self.function_names else None
        self.global_sites.append((function_name, tuple(node.names)))

    def visit_Call(self, node):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "chdir"
        ):
            function_name = self.function_names[-1] if self.function_names else None
            self.chdir_sites.append(function_name)
        self.generic_visit(node)


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_function(tree, name):
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_global_updates_remain_in_audited_constant_setters():
    repository_root = Path(__file__).parents[1]
    source_root = repository_root / "packages" / "pyhees-jjj" / "src" / "jjjexperiment"
    findings = []

    for path in source_root.rglob("*.py"):
        visitor = _BoundaryVisitor()
        visitor.visit(_parse(path))
        findings.extend(
            (path.relative_to(source_root).as_posix(), function_name, names)
            for function_name, names in visitor.global_sites
        )

    assert findings
    assert {relative_path for relative_path, _, _ in findings} == {"constants.py"}
    assert {function_name for _, function_name, _ in findings} == _EXPECTED_GLOBAL_SETTERS


def test_product_chdir_calls_remain_in_calculation_service_boundary():
    repository_root = Path(__file__).parents[1]
    roots = (
        repository_root / "apps" / "gradio" / "src",
        repository_root / "packages" / "verification-core" / "src",
        repository_root / "packages" / "pyhees-jjj" / "src" / "jjjexperiment",
    )
    findings = []

    for source_root in roots:
        for path in source_root.rglob("*.py"):
            visitor = _BoundaryVisitor()
            visitor.visit(_parse(path))
            findings.extend(
                (
                    path.relative_to(repository_root).as_posix(),
                    function_name,
                )
                for function_name in visitor.chdir_sites
            )

    assert findings == [
        ("apps/gradio/src/verification_app/services.py", "run"),
        ("apps/gradio/src/verification_app/services.py", "run"),
    ]


def test_public_calculation_coordinators_remain_mutation_free():
    repository_root = Path(__file__).parents[1]
    coordinators = (
        (
            repository_root / "packages" / "pyhees-jjj" / "src"
            / "jjjexperiment" / "main.py",
            "calc_main",
        ),
        (
            repository_root / "packages" / "pyhees-jjj" / "src"
            / "jjjexperiment" / "section4_2_jjj.py",
            "calc_Q_UT_A",
        ),
    )

    for path, function_name in coordinators:
        function = _find_function(_parse(path), function_name)
        assert not any(
            isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.AugAssign))
            for node in ast.walk(function)
        )
        assignment_targets = (
            target
            for node in ast.walk(function)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        )
        assert not any(
            isinstance(descendant, ast.Subscript)
            for target in assignment_targets
            for descendant in ast.walk(target)
        )


def test_hourly_carryover_loop_remains_isolated_in_dedicated_phase():
    repository_root = Path(__file__).parents[1]
    path = (
        repository_root / "packages" / "pyhees-jjj" / "src"
        / "jjjexperiment" / "section4_2_jjj.py"
    )
    function = _find_function(_parse(path), "_run_carryover_calculation")

    loops = [node for node in ast.walk(function) if isinstance(node, ast.For)]

    assert len(loops) == 1
    assert isinstance(loops[0].target, ast.Name)
    assert loops[0].target.id == "t"