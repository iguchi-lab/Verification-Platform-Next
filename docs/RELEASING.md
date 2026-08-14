# リリース手順

## 版番号

Verification Platform Nextは、製品全体を1つの
[Semantic Versioning](https://semver.org/) で管理します。

- Pythonパッケージ版: `1.3.0`
- 表示名: `ver.1.3.0`
- Gitタグ: `v1.3.0`
- 成果物接尾辞: `_v1.3.0`

製品版の正本は
`packages/pyhees-jjj/src/jjjexperiment/release.py`です。ルート、
`verification-core`、Gradioアプリ、`pyhees-jjj`の各`pyproject.toml`は
同じ版にそろえ、契約テストで不一致を検出します。

日付は版番号として使いません。パッチ修正は`1.2.1`、後方互換な機能追加は
`1.3.0`、互換性を破る変更は`2.0.0`とします。

## 計算成果物の追跡

成果物名には安定した版接尾辞を付けます。

```text
<case_name>_v1.3.0_input.json
<case_name>_v1.3.0_output1.csv
<case_name>_v1.3.0_output2.csv
<case_name>_v1.3.0_manifest.json
```

計算が正常終了すると、マニフェストへ次を記録します。

- 製品版、表示名、リリース日
- 実行したソースのGitコミット
- 建築研究所公式`pyhees`の版と固定コミット
- 床下計算仕様
- 入力JSONをキー順に正規化したSHA-256
- 生成日時（UTC）

Git管理されたソースから実行するとコミットを自動取得します。コンテナや
配布物では、ビルドまたは実行時に`VERIFICATION_SOURCE_COMMIT`へ完全な
コミットSHAを設定します。これにより、ファイル名を毎回の日付で変更せず、
同じ製品版のどのソース・入力から生成されたかを追跡できます。

## リリース判定

リリースPRで次を実行します。

```bash
python -m pytest -q
ruff check .
python scripts/run_phase5_regression.py

cd packages/pyhees-jjj
python -m pytest src/tests -q -o addopts=""
```

計算エンジンまたは入力対応を変更した場合は、
[`regression/phase5/README.md`](../regression/phase5/README.md)に従い、
代表CSVも固定基準と比較します。`skip`、`xfail`、`xpass`、警告は件数だけで
成功扱いにせず、理由と意図をリリースPRへ記録します。

GitHub Actionsがすべて成功した後、PRをマージし、マージコミットへ注釈付き
タグを作成します。

```bash
git switch main
git pull --ff-only
git tag -a v1.3.0 -m "Verification Platform Next ver.1.3.0"
git push origin v1.3.0
gh release create v1.3.0 --title "Verification Platform Next ver.1.3.0"
```

GitHub Releaseには`CHANGELOG.md`の該当版、試験結果、既知の制約を記載します。
Cloud Runへのデプロイはリリースとは別の手動操作であり、明示的な依頼がある
場合だけ実施します。
