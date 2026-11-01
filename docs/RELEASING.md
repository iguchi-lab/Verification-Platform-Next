# リリース手順

## 版番号

Verification Platform Nextは、製品全体を1つの
[Semantic Versioning](https://semver.org/) で管理します。

- Pythonパッケージ版: `1.8.1`
- 表示名: `ver.1.8.1`
- Gitタグ: `v1.8.1`
- 成果物接尾辞: `_v1.8.1`

製品版の正本は
`packages/pyhees-jjj/src/jjjexperiment/release.py`です。ルート、
`verification-core`、Gradioアプリ、`pyhees-jjj`の各`pyproject.toml`は
同じ版にそろえ、契約テストで不一致を検出します。

正式タグ以降のmainには追加更新が入る場合があります。同じ製品版でもソースコミットは異なるため、
[更新履歴](update_history.md)と成果物の `source_commit` を併せて確認します。
入力仕様番号（2026-10-29時点では `261029`）は製品版とは別に管理します。

製品版には日付を使いません。パッチ修正は`1.2.1`、後方互換な機能追加は
`1.3.0`、互換性を破る変更は`2.0.0`とします。

## 計算成果物の追跡

成果物名には安定した版接尾辞を付けます。

```text
<case_name>_v1.8.1_input.json
<case_name>_v1.8.1_output1.csv
<case_name>_v1.8.1_output2.csv
<case_name>_v1.8.1_manifest.json
```

計算が正常終了すると、マニフェストへ次を記録します。

- 製品版、表示名、リリース日
- 実行したソースのGitコミット
- 建築研究所公式`pyhees`の版と固定コミット
- 計算方式、TG仕様識別子・比較モード（TGの場合）
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
タグを作成します。以下の `v1.8.1` は書式例です。実行時は新しいリリース対象版へ
置き換え、既存の正式タグは再作成しません。

```bash
git switch main
git pull --ff-only
git tag -a v1.8.1 -m "Verification Platform Next ver.1.8.1"
git push origin v1.8.1
gh release create v1.8.1 --title "Verification Platform Next ver.1.8.1"
```

GitHub Releaseには`CHANGELOG.md`の該当版、試験結果、既知の制約を記載します。
Cloud Runへのデプロイはリリースとは別の手動操作であり、明示的な依頼がある
場合だけ実施します。

## Cloud Runへの本番反映と完了判定

対象はサービス `verification-platform-next` です。`GCP_PROJECT_ID` と `GCP_REGION` には、
デプロイワークフローのGitHub変数と同じ本番プロジェクトID・リージョンを設定してから以下を使用します。

1. **現在の配信先を控える。** 次の読取りコマンドで `status.traffic` のリビジョン名と割合を確認します。更新前に正常動作を確認した配信先を、切り戻し先としてリリースPRに記録します。

   ```bash
   gcloud run services describe verification-platform-next \
     --project="${GCP_PROJECT_ID:?}" --region="${GCP_REGION:?}" \
     --format='yaml(status.url,status.traffic)'
   ```

2. **リリースタグからデプロイする。** `RELEASE_TAG` に対象の正式タグを設定し、`git rev-parse "${RELEASE_TAG:?}^{commit}"` の出力がリリースPRのマージコミットと一致することを確認します。続いて `gh workflow run deploy-cloud-run.yml --ref "${RELEASE_TAG:?}"` で手動実行します。[Deploy to Cloud Run](https://github.com/iguchi-lab/Verification-Platform-Next/actions/workflows/deploy-cloud-run.yml)
3. **配信先を確認する。** ワークフローの成功後、手順1のコマンドを再実行します。今回作成したリビジョンがトラフィックの100%を受けていることを確認します。
4. **公開画面で計算する。** サービスURLを開き、画面の版番号を確認します。確認用の既知の入力で計算し、暖房・冷房それぞれの年間値を同じ条件の参照値と照合します。出力ファイルから入力JSONとマニフェストを取得し、`version` が対象版、`source_commit` が手順2の完全なSHAであることを確認します。入力の照合には、保存JSONを読み込んで [`input_sha256`](../packages/pyhees-jjj/src/jjjexperiment/release.py) を計算し、マニフェストの `input_sha256` と比較します。
5. **結果を記録する。** デプロイ実行のリンク、配信リビジョン、計算ID、参照値との照合結果をリリースPRに残して本番反映を完了とします。v1.8.1の例では、同じ画面で地盤抵抗を変更し、手動設定をOFFに戻した後の年間値まで確認しました。[v1.8.1の本番確認記録](https://github.com/iguchi-lab/Verification-Platform-Next/pull/219)

## 直前の正常版への切り戻し

新しい配信先で計算エラーや説明できない数値差が再現し、旧版へ戻すと判断した場合は、
`PREVIOUS_REVISION` に手順1で記録した**正常稼働時のリビジョン名**を設定し、旧版に100%のトラフィックを戻します。

```bash
gcloud run services update-traffic verification-platform-next \
  --project="${GCP_PROJECT_ID:?}" --region="${GCP_REGION:?}" \
  --to-revisions="${PREVIOUS_REVISION:?}=100"
```

手順1の読取りコマンドで旧リビジョンが100%であることを確認し、同じ確認用入力で旧版の年間値とマニフェストを照合します。
切り戻した時刻、配信先、原因となった計算IDまたはエラーをリリースPRに記録してください。
リビジョン名を指定した配信設定は次のデプロイにも引き継がれます。修正版の公開時には配信先を確認し、
修正版が最新の正常なリビジョンであることを確かめてから、最新リビジョンへの自動配信を再開する場合に `--to-latest` を使います。[Cloud Run公式のトラフィック切替手順](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
