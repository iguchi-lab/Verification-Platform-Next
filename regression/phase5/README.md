# Phase 5 regression baselines

Phase 5は完了しています。このディレクトリは旧版からモノレポへ切り替えた時点の数値契約です。

These fixtures freeze the legacy form-to-engine contract at form version
`260715`. The current calculation-engine validation target is the
BRI-EES-House/pyhees Ver.3.10 upstream commit
`d5224c4a01def00a8421bcd2fcc0d4b4a5b88644`, integrated with the JJJ adapters.
The unchanged fixtures also preserve compatibility with the original imported
fork commit `0f91ba8381df1b4960557b92b39339385cc9009f`.

Each case starts from every legacy form default, applies the small set of UI
overrides recorded in `manifest.json`, and compares three artifacts:

- the complete calculation input JSON;
- the annual `output1.csv` summary; and
- every value in the 8,760-hour `output2.csv` time series.

CSV labels and timestamps must match exactly. Numeric values use the explicit
relative and absolute tolerances in `manifest.json`. Baselines are gzip
compressed only to keep the repository small; comparison is against their
full uncompressed content.

Run the verification from the repository root:

```bash
python scripts/run_phase5_regression.py
```

Baseline replacement is intentionally explicit. Only update it after a
reviewed calculation-engine change and record the new engine commit in the
manifest first:

```bash
python scripts/run_phase5_regression.py \
  --update-baselines \
  --engine-commit <exact-engine-commit>
```

Never update baselines merely to make a failing pull request pass. Review the
numerical differences and their standards impact first.
