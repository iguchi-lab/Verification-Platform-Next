# Repository guidance

## Purpose

This repository is the shared source of truth for work performed from local
computers and Codex Cloud. Keep work portable: use branches, commit meaningful
changes, and push them before switching computers.

Cloud Run is optional application hosting. It is not required for Codex Cloud
development and must only be deployed through the manual GitHub Actions
workflow when application hosting is explicitly requested.

## Environment setup

Codex Cloud and clean Linux environments should run:

```bash
bash scripts/setup-codex-cloud.sh
```

Use Python 3.12.11 or newer, but stay below Python 3.13.

## Verification

Run the repository checks from its root:

```bash
python -m pytest -q
ruff check .
```

When changing calculation code or its boundaries, also run the engine's
historical test suite:

```bash
cd packages/pyhees-jjj
python -m pytest src/tests -q -o addopts=""
```

The Phase 5 numerical gate is included in the full test suite. It can also be
run directly with `python scripts/run_phase5_regression.py`. Do not replace its
baselines without reviewing the numerical changes and updating the pinned
engine commit in `regression/phase5/manifest.json`.

When changing the calculation engine or input mapping, also compare representative
CSV outputs with the legacy baseline as described in `docs/MIGRATION.md`.

## Change scope

- Preserve the imported history under `packages/pyhees-jjj`.
- Do not archive or delete the legacy repositories until Phase 5 is complete.
- Keep generated outputs out of Git; use `outputs/` or a temporary directory.

## Refactoring workflow

Before refactoring calculation code, read `docs/REFACTORING.md` and the linked
GitHub issue. Keep behavior-preserving refactoring separate from feature work,
formula changes, upstream synchronization, and regression-baseline updates.

Treat one user instruction as one design outcome tracked by one issue. For
low-risk work, target 30-50 boundaries or roughly 800-1,500 changed lines per
pull request, and group 8-15 boundaries with the same responsibility,
invariants, and targeted tests into one commit. Keep numerical, stateful, and
order-sensitive work smaller.

Run targeted tests and Ruff for every commit. Run the full repository, Phase 5,
engine, and CI checks once per pull request, not after every commit.

Each refactoring pull request must state its scope, non-goals, preserved
behavior, verification evidence, and relationship to the work package. Update
the issue before handing the branch to another computer or Codex task and after
each PR merge.
