# Contributing

Verification Platform Nextへの不具合報告、仕様の確認、文書改善、コード変更を
歓迎します。IssueとPull Requestは日本語または英語で作成できます。

## 開発環境

Python 3.12.11以上、3.13未満を使用します。

```bash
git clone https://github.com/iguchi-lab/Verification-Platform-Next.git
cd Verification-Platform-Next
python -m pip install --upgrade pip
python -m pip install -e apps/gradio
python -m pip install pytest "ruff==0.15.22"
```

## 変更時の原則

- 1つのPull Requestでは、目的が同じ変更だけを扱ってください。
- 挙動を維持する整理と、計算式・入力契約・数値基準の変更を分けてください。
- `packages/pyhees-jjj/src/pyhees`の建築研究所由来コードと、
  `jjjexperiment`の独自拡張を区別してください。
- 建研由来の関数名、変数名、式番号、評価順を変更する場合は理由を記録してください。
- 生成したCSV、JSON、ログをコミットしないでください。
- APIキー、個人情報、非公開の入力データをIssueやPull Requestへ添付しないでください。

## 検証

すべての変更で、対象テストとRuffを実行してください。

```bash
python -m pytest -q
ruff check .
```

計算コードまたは入力対応を変更した場合は、Phase 5と計算エンジン内部試験も
実行します。

```bash
python scripts/run_phase5_regression.py

cd packages/pyhees-jjj
python -m pytest src/tests -q -o addopts=""
```

数値基準は、差分の原因と影響を確認した変更に限って更新してください。更新時は
`regression/phase5/manifest.json`の計算エンジンコミットも見直します。

## Pull Request

Pull Requestには次を記載してください。

- 変更の目的と背景
- 変更した範囲と変更しない範囲
- 利用者および計算結果への影響
- 計算式変更の場合は根拠資料と式番号
- 実行した試験と結果
- 関連するIssue

GitHub Actionsの全チェックが成功してからマージします。
