# Verification Platform Next

[![CI](https://github.com/iguchi-lab/Verification-Platform-Next/actions/workflows/ci.yml/badge.svg)](https://github.com/iguchi-lab/Verification-Platform-Next/actions/workflows/ci.yml)

## 公開Web版

**[Verification Platform Next ver.1.1.1をブラウザで開く](https://verification-platform-next-dnoeszca4a-an.a.run.app/)**

公開Web版では、インストールせずに入力、計算、結果ファイルの取得を行えます。
計算は1件ずつ処理するため、混雑時は画面に表示される順番をお待ちください。
入力ファイルと計算成果物は一時的に保存されるため、機密情報や個人情報を含む
データはアップロードしないでください。

住宅の省エネルギー性能を検証するための計算エンジン、入力スキーマ、Gradio UIを
まとめたPythonモノレポです。正式版は **ver.1.1.1** です。

本リポジトリは、建築研究所が公開する住宅のエネルギー消費性能計算プログラム
`pyhees`を基礎とし、検証用の入力画面、床下空調などの拡張計算、数値回帰試験を
統合しています。建築研究所の公式配布物ではありません。

## 主な機能

- 223項目の正規入力スキーマと方式別の表示・検証条件
- JSON入力とGradio Web UI
- ダクト式セントラル空調、ルームエアコン、床下空調などの計算
- 暖冷房結果、8760時間系列、グラフ、計算ログの出力
- 製品版、ソースコミット、上流`pyhees`、入力SHA-256を記録するマニフェスト
- 旧版との代表ケース比較を行うPhase 5数値回帰
- Google Colabおよび任意のCloud Runデプロイ

## 動作環境

- Python 3.12.11以上、3.13未満
- Windows、macOS、Linux、またはGoogle Colab

## インストールと起動

```bash
git clone https://github.com/iguchi-lab/Verification-Platform-Next.git
cd Verification-Platform-Next
python -m pip install --upgrade pip
python -m pip install -e apps/gradio
verification-platform
```

Poetryを使用する場合は次のとおりです。

```bash
poetry install
poetry run verification-platform
```

Colabでは
[`notebooks/Verification_Platform_Next.ipynb`](notebooks/Verification_Platform_Next.ipynb)
を開いてください。

## 検証

リポジトリ全体の契約・回帰試験と静的検査を実行します。

```bash
python -m pytest -q
ruff check .
python scripts/run_phase5_regression.py
```

計算エンジン内部の履歴試験は次のコマンドで実行します。

```bash
cd packages/pyhees-jjj
python -m pytest src/tests -q -o addopts=""
```

数値基準は、差分の計算上・規格上の影響を確認せずに更新しないでください。

## ディレクトリ構成

```text
apps/gradio/                 Gradio Web UIと実行サービス
packages/verification-core/ 入力スキーマと共通契約
packages/pyhees-jjj/         建研由来コードと検証用拡張計算
notebooks/                   Google Colabランチャー
regression/phase5/           代表ケースの固定数値基準
tests/                       パッケージ横断の契約・回帰試験
docs/                        設計、入力、計算仕様、リリース資料
```

## 計算成果物と版管理

成果物名には製品版を付け、同じ接頭辞のマニフェストへソースコミット、上流
`pyhees`版、床下仕様、入力SHA-256を記録します。詳細は
[`docs/RELEASING.md`](docs/RELEASING.md)を参照してください。

生成したJSON、CSV、ログはGitへ追加せず、`outputs/`などの作業用ディレクトリに
保存してください。

## Cloud Runへの任意デプロイ

`.github/workflows/deploy-cloud-run.yml`は手動実行専用です。GitHub Actionsの
variablesとsecretsへGoogle Cloudのプロジェクト、リージョン、Artifact Registry、
Workload Identity Federationを設定して使用します。`main`へのpushでは自動
デプロイされません。

既定のCloud Run構成は最大1インスタンスです。複数の利用者から計算要求があった場合は
Gradioのキューで受け付け、1件ずつ順番に計算します。待機上限は5件、計算成果物の
保持期間は24時間で、次の環境変数から変更できます。

- `GRADIO_QUEUE_MAX_SIZE`: 待機可能件数。0以下は無制限
- `VERIFICATION_RESULT_TTL_SECONDS`: 成果物保持秒数。0以下は自動削除なし
- `VERIFICATION_OUTPUT_DIR`: 計算ID別ディレクトリを作る親ディレクトリ

ローカルでコンテナを確認する場合は次のとおりです。

```bash
docker build -t verification-platform-next .
docker run --rm -p 8080:8080 verification-platform-next
```

## ドキュメント

- [アーキテクチャ](docs/ARCHITECTURE.md)
- [リリースと成果物の版管理](docs/RELEASING.md)
- [変更履歴](CHANGELOG.md)
- [床下関連設定の入力ガイド](docs/underfloor_ac_input_guide.md)
- [床下空調計算の7つの変更点](docs/underfloor_ac_seven_changes.md)
- [Excelとの床下計算整合](docs/underfloor_ac_excel_alignment.md)
- [建研本家・旧Verification Platformとの計算差分](docs/calculation_differences.md)
- [計算エンジン](packages/pyhees-jjj/README.md)
- [上流`pyhees`の追跡方針](packages/pyhees-jjj/UPSTREAM.md)

## コントリビューション

不具合報告や改善提案はGitHub Issue、変更提案はPull Requestで受け付けます。
計算式または数値結果を変更する場合は、根拠資料、影響する系列・年間値、実行した
試験を明記してください。詳しくは[`CONTRIBUTING.md`](CONTRIBUTING.md)を参照して
ください。
