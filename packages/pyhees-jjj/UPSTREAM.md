# 建築研究所由来コードの管理

## 対象

- 上流リポジトリ: `BRI-EES-House/pyhees`
- 建築研究所由来コード: `src/pyhees`
- 検証用プラットフォーム独自コード: `src/jjjexperiment`
- 独自変更マーカー: `src/pyhees/jjj_markers.py`（上流由来ではありません）
- 上流接続アダプター: src/pyhees/jjj_runtime.py（上流由来ではありません）

## 現在の基準

このモノレポへ取り込んだ `pyhees-jjj` の固定コミットは次のとおりです。

- fork commit: `0f91ba8381df1b4960557b92b39339385cc9009f`
- engine version: `_20260323`
- legacy form version: `260715`

この値は `regression/phase5/manifest.json` と一致させます。

固定コミットは独自変更を含むforkのコミットです。対応する `BRI-EES-House/pyhees` の正確な基準コミットは、現在の履歴と文書だけでは確定できていません。次回の上流更新前に上流リポジトリとの比較で特定し、この文書へコミットIDを追記します。推測したバージョン名で更新しません。

## 変更方針

1. 新しい独自機能は `src/jjjexperiment` に実装します。
2. `src/pyhees` から `jjjexperiment` への新しい依存は追加しません。
3. `src/pyhees` から `jjjexperiment` への逆依存は0件を維持し、`tests/test_engine_boundary.py` の契約テストで再導入を防止します。
4. リファクタリングと計算機能の追加・数式変更は別のPRにします。
5. 挙動を維持するリファクタリングではPhase 5の基準CSVを更新しません。

## 上流更新の手順

1. 上流の対象コミットを明記した専用ブランチとPRを作成します。
2. 現在の `src/pyhees` と上流コードの差分を、上流変更と独自変更に分類します。
3. 上流変更を取り込み、独自変更は可能な限り `jjjexperiment` 側のアダプターへ移します。
4. エンジン内部テスト、ルートの契約テスト、Phase 5数値回帰を実行します。
5. 数値差がある場合は原因と妥当性をレビューし、承認後にだけ基準値とmanifestを更新します。
6. この文書の基準コミットと `regression/phase5/manifest.json` を更新します。
