#!/usr/bin/env sh

# pip の更新
pip install -U pip

# Poetry をインストール
pip install poetry

# プロジェクトのルートに仮想環境を作成
# 重要: この設定により .venv が /workspaces/pyhees-jjj/.venv に生成されます
# VS Code の Python インタプリタ選択で "poetry ./.venv/bin/python" を選択してください
poetry config virtualenvs.in-project true

# NOTE: poetry lock を実行しないで下さい
# バージョン固定ファイルが再生成され、開発者間でのバージョンの不一致が発生するため

# 開発用の依存関係をインストール
poetry install --with dev
