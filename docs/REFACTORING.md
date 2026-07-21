# リファクタリング方針と引き継ぎ

## 目的

この文書は、複数のPCやCodexタスクから計算コードの整理を継続するための正本です。安定した方針と作業手順はこの文書に置き、個別作業の進捗、判断、残課題はGitHub IssueとPull Requestに記録します。

リファクタリングの目的は、計算結果を変えずに責任範囲、依存方向、状態管理、テスト容易性を改善し、その後の機能追加と計算ロジック確認を安全にすることです。

## 変更してよい範囲

| 領域 | 所有・役割 | リファクタリング時の扱い |
| --- | --- | --- |
| `packages/pyhees-jjj/src/pyhees` | 建築研究所由来コード | 原則として直接変更しない。上流更新は専用PRで扱う |
| `packages/pyhees-jjj/src/jjjexperiment` | 検証用プラットフォーム独自コード | 主な整理対象。新しい独自機能も原則ここに置く |
| `packages/verification-core` | 入力スキーマと共通契約 | 入力契約の正本。UI都合の処理を持ち込まない |
| `apps/gradio` | UIと実行オーケストレーション | 計算式を持たず、公開APIと結果モデルだけを利用する |
| `regression/phase5` | 旧版との数値契約 | 挙動維持のリファクタリングでは基準値を変更しない |

詳しい依存方向は [`ARCHITECTURE.md`](ARCHITECTURE.md)、建築研究所由来コードの管理方法は [`packages/pyhees-jjj/UPSTREAM.md`](../packages/pyhees-jjj/UPSTREAM.md) を参照してください。

## 必須方針

1. 機能追加、計算式変更、上流更新、リファクタリングを同じPRに混在させません。
2. 1つのPRでは、1つの責任範囲または依存境界だけを扱います。
3. 変更前の挙動をテストで固定してから内部構造を変更します。
4. `pyhees -> jjjexperiment` の新しい逆依存を追加しません。
5. 挙動維持のPRではPhase 5の基準CSVと許容誤差を変更しません。
6. 公開API、入力辞書、出力CSV、例外、ログなど、利用側から観測できる挙動の変更を非対象とします。
7. PCを切り替える前に、作業をcommit・pushし、Issueへ現在地と次の操作を記録します。

## 完了済み

- [PR #5](https://github.com/iguchi-lab/Verification-Platform-Next/pull/5): 建築研究所由来コードと独自コードの境界を文書化し、逆依存の許可リストと計算エンジンCIを追加しました。
- [PR #6](https://github.com/iguchi-lab/Verification-Platform-Next/pull/6): 計算時のInjector状態を実行コンテキスト内へ限定し、例外、入れ子、スレッド、非同期タスクの分離をテストしました。
- [PR #8](https://github.com/iguchi-lab/Verification-Platform-Next/pull/8): `constants.py` のオプションEnum依存を明示importに置き換え、従来の再公開名とVAV既定値を契約テストで固定しました。
- [PR #10](https://github.com/iguchi-lab/Verification-Platform-Next/pull/10): `main.py` のDIコンテナ由来のワイルドカードimportを廃止し、実際に使用する型とEnumを定義元から明示importしました。

この一覧は完了した設計判断を把握するためのものです。次の作業は必ず最新の`main`とGitHub上のIssue・PRを確認して決めます。

## 次の候補

以下は候補であり、着手順ではありません。調査結果をIssueに記録し、独立して検証できる最小単位を1件だけ選びます。

1. `jjjexperiment`のモジュールと公開APIを棚卸しし、利用箇所のないコードと外部利用される境界を区別する。
2. `jjjexperiment/main.py`のワイルドカードimportと暗黙の依存を、明示的なimportへ段階的に置き換える。
3. 入力準備、負荷計算、暖冷房計算、結果組み立て、ファイル出力の責任を分離する。
4. 既存の`pyhees -> jjjexperiment`逆依存を1ファイルずつ削減する。
5. カレントディレクトリ、グローバル状態、暗黙のファイル名などの副作用を境界へ集約する。
6. 辞書と長い引数列を、既存契約を保ったまま内部DTOや型付き結果へ段階的に整理する。

## 1件の進め方

1. 最新の`main`へ同期します。
2. `.github/ISSUE_TEMPLATE/refactoring.yml`からIssueを作成します。
3. 対象、非対象、保持する挙動、検証方法をIssueに記入します。
4. 専用ブランチを作り、変更前の回帰テストを追加または確認します。
5. 内部構造だけを変更します。
6. 必須テストを実行し、結果をPRへ記録します。
7. Draft PRで差分を確認し、CI成功後にレビュー可能へ変更します。
8. マージ後、Issueの完了項目と次候補を更新します。

## 検証

計算コードまたはその境界を変更した場合、リポジトリルートで次を実行します。

```bash
python -m pytest -q
ruff check .
python scripts/run_phase5_regression.py
```

続いて計算エンジンの履歴テストを実行します。

```bash
cd packages/pyhees-jjj
python -m pytest src/tests -q -o addopts=""
```

必要な依存関係と実行環境はルートの [`AGENTS.md`](../AGENTS.md) に従います。失敗を通すためだけにPhase 5基準値を更新してはいけません。

## PCを切り替えるとき

作業中のPCで次を確認します。

```bash
git status
git push -u origin <作業ブランチ>
```

Issueへ次の内容を追記します。

- 作業ブランチと関連PR
- 完了した内容
- 未完了の内容と次の1操作
- 実行済みテストと結果
- 判断が必要な点

別のPCではリポジトリをcloneするか、既存cloneを最新化し、Issueに記録されたブランチをcheckoutします。未commitの変更がある場合は先に退避またはcommitし、上書きしません。

## Codexへの開始指示

新しいPCまたは新しいCodexタスクでは、Issue番号を指定して次のように依頼します。

```text
このリポジトリの計算コードのリファクタリングを続けます。

最初にAGENTS.md、docs/ARCHITECTURE.md、docs/REFACTORING.md、
packages/pyhees-jjj/UPSTREAM.mdとGitHub Issue #<番号>を読んでください。
最新のmain、関連PR、作業ブランチの状態も確認してください。

機能追加、計算式変更、上流更新、Phase 5基準値の変更は行わず、
Issueに記載された挙動維持のリファクタリングだけを進めてください。
着手前に対象、非対象、保持する挙動、実行するテストを説明してください。
作業終了時はcommit・pushし、Draft PRとIssueに検証結果と次の操作を記録してください。
```

Issueがまだない場合は、実装を始めず、コードを調査して最小の作業候補をIssueとして提案します。
