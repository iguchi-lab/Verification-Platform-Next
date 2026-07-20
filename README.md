# Verification Platform Next

検証用プラットフォームの計算エンジン、共通入力スキーマ、Gradio UIを同一リポジトリで管理するモノレポです。

## 現在の状態

移行 Phase 2（入力スキーマ移行）が完了し、Phase 3（Gradio移行）の準備段階です。

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

次は、正規 `InputSchema` から222項目のGradioフォームを生成し、宣言的ビルダーを実行経路へ接続します。

## ディレクトリ構成

```text
.
├── apps/
│   └── gradio/                 # Web UI
├── packages/
│   ├── verification-core/      # 入力スキーマ・共通契約
│   └── pyhees-jjj/             # 計算エンジン移行先
├── notebooks/
│   └── legacy/                 # 現行動作版の移行元
├── tests/                      # 契約・回帰テスト
├── docs/
│   ├── ARCHITECTURE.md
│   └── MIGRATION.md
└── pyproject.toml
```

## ローカル起動（移行用JSON画面）

Python 3.12.11以上とPoetryを使用します。

```bash
poetry install
poetry run verification-platform
```

現在の最小アプリはJSON入力用です。222項目のフォームは、共通スキーマへの移行が完了するまでは `notebooks/legacy` のGradio版を利用してください。

## 設計資料

- [アーキテクチャ](docs/ARCHITECTURE.md)
- [段階的移行計画](docs/MIGRATION.md)
- [計算エンジン移行境界](packages/pyhees-jjj/README.md)

## 移行元

- [Verification-Platform](https://github.com/iguchi-lab/Verification-Platform)
- [pyhees-jjj](https://github.com/iguchi-lab/pyhees-jjj)

移行完了までは、旧リポジトリを削除・アーカイブしません。
