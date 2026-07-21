# Verification Platform Next

検証用プラットフォームの計算エンジン、共通入力スキーマ、Gradio UIを同一リポジトリで管理するモノレポです。

## 現在の状態

移行 Phase 4（計算エンジン履歴移行）とクラウド実行基盤の整備が完了し、Phase 5（回帰確認と切替）の準備段階です。

- 共通入力スキーマの型を `verification-core` に追加
- 現行222項目をバージョン付きJSON台帳へ移行（基本45・暖房84・冷房91・換気2）
- UI入力から計算用 `input_data` への264代入を条件分岐・元行番号付きで台帳化
- 222項目すべてが計算用入力に利用されることを契約テストで検証
- JSON入力を実行できる最小Gradioアプリを追加
- 現行計算エンジンを固定コミットで参照
- スキーマ契約テストとGitHub Actionsを追加
- 現行Gradioノートブックを移行元スナップショットとして保存
- 制限付きAST互換ビルダーと型付き宣言的ビルダーを追加
- 222項目の正規 `InputSchema` と表示条件を追加
- デフォルト、全暖冷房方式、全boolean・select代替値で旧入力との完全一致を固定
- 正規 `InputSchema` から222項目のGradioフォームを生成
- 暖冷房方式に応じた表示切替を、入力値を維持したまま実装
- 計算ログ、グラフ、ダウンロード収集をUI非依存サービスへ分離
- Colab版をインストールと起動だけの薄いランチャーへ移行
- Cloud Run向けDockerfile、サービス定義、GitHub Actionsデプロイを追加
- 計算出力を実行環境ごとの作業ディレクトリへ隔離
- `pyhees-jjj` を固定コミットまでの履歴付きで `packages/pyhees-jjj` へ統合
- Gradioアプリの計算エンジン依存をモノレポ内のローカルパスへ切替

次は、代表入力による旧版との出力比較、ローカル・Colab・コンテナの回帰確認を行います。

## 複数PCとCodex Cloudでの作業

このリポジトリを作業状態の正本とし、PCを切り替える前に作業ブランチをcommit・pushします。Codex Cloudでは、このGitHubリポジトリを接続した環境から同じブランチをチェックアウトして作業します。

Codex Cloud環境のセットアップスクリプトには、次を指定してください。

```bash
bash scripts/setup-codex-cloud.sh
```

Pythonは `3.12.11` 以上、`3.13` 未満を使用します。リポジトリ共通の作業手順と検証コマンドは `AGENTS.md` に記載しています。

## ディレクトリ構成

```text
.
├── apps/
│   └── gradio/                 # Web UI
├── packages/
│   ├── verification-core/      # 入力スキーマ・共通契約
│   └── pyhees-jjj/             # 履歴付きで統合した計算エンジン
├── notebooks/
│   ├── Verification_Platform_Next.ipynb # Colabランチャー
│   └── legacy/                 # 現行動作版の移行元
├── tests/                      # 契約・回帰テスト
├── docs/
│   ├── ARCHITECTURE.md
│   └── MIGRATION.md
└── pyproject.toml
```

## ローカル起動

Python 3.12.11以上とPoetryを使用します。

```bash
poetry install
poetry run verification-platform
```

正規スキーマから生成した222項目のフォームが起動します。Colabでは `notebooks/Verification_Platform_Next.ipynb` を使用してください。

## Cloud Runへの任意デプロイ

Cloud RunはGradioアプリを公開する場合だけ使用する任意機能であり、複数PCやCodex Cloudで開発を継続するためには必要ありません。コンテナはCloud RunのHTTP契約に合わせて `0.0.0.0:8080` で起動し、計算出力を一時領域 `/tmp/verification-platform` に保存します。

GitHubリポジトリに次を設定したうえで、`.github/workflows/deploy-cloud-run.yml` を手動実行すると、ビルド、Artifact Registryへのpush、Cloud Runへのデプロイを行います。`main` へのpushでは自動デプロイされません。

GitHub Actions variables:

- `GCP_PROJECT_ID`: Google CloudプロジェクトID
- `GCP_REGION`: Cloud RunとArtifact Registryのリージョン（例: `asia-northeast1`）
- `GCP_ARTIFACT_REPOSITORY`: Artifact Registryリポジトリ名

GitHub Actions secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`: Workload Identity Providerの完全名
- `GCP_SERVICE_ACCOUNT`: デプロイ用サービスアカウントのメールアドレス

ローカルでコンテナを確認する場合:

```bash
docker build -t verification-platform-next .
docker run --rm -p 8080:8080 verification-platform-next
```

`deploy/cloudrun.service.yaml` は同等のCloud Run設定を手動適用する際の基準です。`IMAGE_URI` を実際のイメージURIへ置換して使用します。

## 設計資料

- [アーキテクチャ](docs/ARCHITECTURE.md)
- [段階的移行計画](docs/MIGRATION.md)
- [計算エンジン](packages/pyhees-jjj/README.md)

## 移行元

- [Verification-Platform](https://github.com/iguchi-lab/Verification-Platform)
- [pyhees-jjj](https://github.com/iguchi-lab/pyhees-jjj)

移行完了までは、旧リポジトリを削除・アーカイブしません。
