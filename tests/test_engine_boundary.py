import ast
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PYHEES_SOURCE = REPOSITORY_ROOT / "packages" / "pyhees-jjj" / "src" / "pyhees"
JJJEXPERIMENT_SOURCE = REPOSITORY_ROOT / "packages" / "pyhees-jjj" / "src" / "jjjexperiment"
JJJEXPERIMENT_MAIN = JJJEXPERIMENT_SOURCE / "main.py"
ENGINE_TEST_SOURCE = REPOSITORY_ROOT / "packages" / "pyhees-jjj" / "src" / "tests"
ENGINE_TEST_UTILS_SOURCE = (
    REPOSITORY_ROOT / "packages" / "pyhees-jjj" / "src" / "test_utils"
)
DENCHU_TEST_SOURCE = (
    ENGINE_TEST_SOURCE / "denchu"
)

# Temporary migration allowlist. Removing an entry is encouraged; adding one is not.
# Keep this exact so a dependency cannot be added or removed without an explicit review.
EXPECTED_REVERSE_DEPENDENCIES = {
    "section3_1_e.py": {
        "jjjexperiment.common",
        "jjjexperiment.constants",
        "jjjexperiment.inputs.options",
        "jjjexperiment.logger",
        "jjjexperiment.underfloor_ac.inputs.common",
        "jjjexperiment.underfloor_ac.section3_1_e",
    },
    "section4_2.py": {
        "jjjexperiment.common",
        "jjjexperiment.constants",
        "jjjexperiment.inputs.di_container",
        "jjjexperiment.inputs.options",
        "jjjexperiment.logger",
    },
    "section4_2_a.py": {
        "jjjexperiment.common",
        "jjjexperiment.constants",
        "jjjexperiment.inputs.options",
        "jjjexperiment.logger",
    },
    "section4_2_b.py": {"jjjexperiment.constants"},
    "section4_3.py": {
        "jjjexperiment.common",
        "jjjexperiment.constants",
    },
    "section4_3_a.py": {"jjjexperiment.constants"},
}

# Temporary migration allowlist. Remove modules as their wildcard imports are made explicit.
EXPECTED_MAIN_WILDCARD_IMPORTS: set[str] = set()

EXPECTED_OPTIONS_WILDCARD_IMPORTERS: set[str] = set()

# Package __init__.py files may deliberately re-export a public API. Implementation
# modules must make their dependencies explicit; shrink this migration allowlist as
# each remaining boundary is refactored.
EXPECTED_IMPLEMENTATION_WILDCARD_IMPORTS: set[tuple[str, str]] = set()

EXPECTED_DENCHU_TEST_WILDCARD_IMPORTS: set[tuple[str, str]] = set()

EXPECTED_OPTIONS_TEST_WILDCARD_IMPORTERS = {
    "latent_load/test_latent_load_integration.py",
    "underfloor_ac/test_4_2_f46_f48.py",
}

EXPECTED_ENGINE_TEST_WILDCARD_IMPORTS = {
    ("tests/latent_load/test_latent_load_integration.py", "jjjexperiment.inputs.options"),
    ("tests/origin/test_4_2_formula_45.py", "pyhees.section4_2"),
    ("tests/underfloor_ac/test_4_2_f46_f48.py", "jjjexperiment.common"),
    (
        "tests/underfloor_ac/test_4_2_f46_f48.py",
        "jjjexperiment.inputs.options",
    ),
}


def _jjjexperiment_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name
                for alias in node.names
                if alias.name == "jjjexperiment" or alias.name.startswith("jjjexperiment.")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "jjjexperiment" or node.module.startswith("jjjexperiment."):
                imports.add(node.module)

    return imports


def _find_reverse_dependencies() -> dict[str, set[str]]:
    result = {}
    for path in sorted(PYHEES_SOURCE.rglob("*.py")):
        imports = _jjjexperiment_imports(path)
        if imports:
            result[path.relative_to(PYHEES_SOURCE).as_posix()] = imports
    return result


def test_pyhees_reverse_dependencies_match_migration_allowlist():
    actual = _find_reverse_dependencies()

    assert actual == EXPECTED_REVERSE_DEPENDENCIES, (
        "The pyhees -> jjjexperiment dependency boundary changed. "
        "Do not add a reverse dependency. If an existing dependency was removed, "
        "reduce EXPECTED_REVERSE_DEPENDENCIES in the same refactoring PR.\n"
        f"expected={EXPECTED_REVERSE_DEPENDENCIES}\nactual={actual}"
    )


def test_main_wildcard_imports_match_migration_allowlist():
    tree = ast.parse(
        JJJEXPERIMENT_MAIN.read_text(encoding="utf-8"),
        filename=str(JJJEXPERIMENT_MAIN),
    )
    actual = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module
        and any(alias.name == "*" for alias in node.names)
    }

    assert actual == EXPECTED_MAIN_WILDCARD_IMPORTS, (
        "The jjjexperiment.main wildcard import boundary changed. "
        "Do not add a wildcard import. If an existing wildcard import was removed, "
        "reduce EXPECTED_MAIN_WILDCARD_IMPORTS in the same refactoring PR.\n"
        f"expected={EXPECTED_MAIN_WILDCARD_IMPORTS}\nactual={actual}"
    )


def test_jjjexperiment_common_imports_are_explicit():
    wildcard_importers = set()
    for path in sorted(JJJEXPERIMENT_SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jjjexperiment.common"
            and any(alias.name == "*" for alias in node.names)
            for node in ast.walk(tree)
        ):
            wildcard_importers.add(path.relative_to(JJJEXPERIMENT_SOURCE).as_posix())

    assert not wildcard_importers, (
        "Import names explicitly from jjjexperiment.common; wildcard imports obscure "
        f"the dependency boundary: {sorted(wildcard_importers)}"
    )


def test_options_wildcard_imports_match_migration_allowlist():
    wildcard_importers = set()
    for path in sorted(JJJEXPERIMENT_SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jjjexperiment.inputs.options"
            and any(alias.name == "*" for alias in node.names)
            for node in ast.walk(tree)
        ):
            wildcard_importers.add(path.relative_to(JJJEXPERIMENT_SOURCE).as_posix())

    assert wildcard_importers == EXPECTED_OPTIONS_WILDCARD_IMPORTERS, (
        "The jjjexperiment.inputs.options wildcard import boundary changed. "
        "Do not add a wildcard import. If an existing wildcard import was removed, "
        "reduce EXPECTED_OPTIONS_WILDCARD_IMPORTERS in the same refactoring commit.\n"
        f"expected={EXPECTED_OPTIONS_WILDCARD_IMPORTERS}\nactual={wildcard_importers}"
    )


def test_implementation_wildcard_imports_match_migration_allowlist():
    wildcard_imports = set()
    for path in sorted(JJJEXPERIMENT_SOURCE.rglob("*.py")):
        if path.name == "__init__.py":
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        wildcard_imports.update(
            (path.relative_to(JJJEXPERIMENT_SOURCE).as_posix(), node.module)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and any(alias.name == "*" for alias in node.names)
        )

    assert wildcard_imports == EXPECTED_IMPLEMENTATION_WILDCARD_IMPORTS, (
        "Implementation modules must use explicit imports. Do not add a wildcard "
        "import. If an existing wildcard import was removed, reduce "
        "EXPECTED_IMPLEMENTATION_WILDCARD_IMPORTS in the same refactoring commit.\n"
        f"expected={EXPECTED_IMPLEMENTATION_WILDCARD_IMPORTS}\n"
        f"actual={wildcard_imports}"
    )


def test_denchu_test_wildcard_imports_match_migration_allowlist():
    wildcard_imports = set()
    for path in sorted(DENCHU_TEST_SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        wildcard_imports.update(
            (path.relative_to(DENCHU_TEST_SOURCE).as_posix(), node.module)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and any(alias.name == "*" for alias in node.names)
        )

    assert wildcard_imports == EXPECTED_DENCHU_TEST_WILDCARD_IMPORTS, (
        "Denchu tests must import their dependencies explicitly. Do not add a "
        "wildcard import. If an existing wildcard import was removed, reduce "
        "EXPECTED_DENCHU_TEST_WILDCARD_IMPORTS in the same refactoring commit.\n"
        f"expected={EXPECTED_DENCHU_TEST_WILDCARD_IMPORTS}\n"
        f"actual={wildcard_imports}"
    )


def test_options_test_wildcard_imports_match_migration_allowlist():
    wildcard_importers = set()
    for path in sorted(ENGINE_TEST_SOURCE.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if any(
            isinstance(node, ast.ImportFrom)
            and node.module == "jjjexperiment.inputs.options"
            and any(alias.name == "*" for alias in node.names)
            for node in ast.walk(tree)
        ):
            wildcard_importers.add(path.relative_to(ENGINE_TEST_SOURCE).as_posix())

    assert wildcard_importers == EXPECTED_OPTIONS_TEST_WILDCARD_IMPORTERS, (
        "Engine tests must import option Enums explicitly. Do not add a wildcard "
        "import. If an existing wildcard import was removed, reduce "
        "EXPECTED_OPTIONS_TEST_WILDCARD_IMPORTERS in the same refactoring commit.\n"
        f"expected={EXPECTED_OPTIONS_TEST_WILDCARD_IMPORTERS}\n"
        f"actual={wildcard_importers}"
    )


def test_engine_test_wildcard_imports_match_migration_allowlist():
    wildcard_imports = set()
    source_root = ENGINE_TEST_SOURCE.parent

    for directory in (ENGINE_TEST_SOURCE, ENGINE_TEST_UTILS_SOURCE):
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            wildcard_imports.update(
                (path.relative_to(source_root).as_posix(), node.module)
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                and node.module
                and any(alias.name == "*" for alias in node.names)
            )

    assert wildcard_imports == EXPECTED_ENGINE_TEST_WILDCARD_IMPORTS, (
        "Engine tests and their support modules must use explicit imports. Do not "
        "add a wildcard import. If an existing wildcard import was removed, reduce "
        "EXPECTED_ENGINE_TEST_WILDCARD_IMPORTS in the same refactoring commit.\n"
        f"expected={EXPECTED_ENGINE_TEST_WILDCARD_IMPORTS}\n"
        f"actual={wildcard_imports}"
    )
