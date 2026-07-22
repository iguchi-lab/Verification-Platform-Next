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
2. 1つのPRでは、同じ目的とリスク特性を持つ独立した責任範囲または依存境界を、原則3〜5件、最大5件まで1バッチとして扱えます。
3. 変更前の挙動をテストで固定してから内部構造を変更します。
4. `pyhees -> jjjexperiment` の新しい逆依存を追加しません。
5. 挙動維持のPRではPhase 5の基準CSVと許容誤差を変更しません。
6. 公開API、入力辞書、出力CSV、例外、ログなど、利用側から観測できる挙動の変更を非対象とします。
7. PCを切り替える前に、作業をcommit・pushし、Issueへ現在地と次の操作を記録します。
8. 建築研究所由来コードと対応する実装では、一般的な抽象化よりも上流との差分追跡のしやすさを優先します。

## 建研コードとの対応と命名

建築研究所（建研）のプログラムに対応するコードは、節、関数、変数、式番号、処理順の対応を追えることを重視します。挙動を変えない整理であっても、上流との差分を読みにくくする大規模な抽象化、改名、並べ替えは避けます。

- `pyhees/section4_2.py`のような建研由来モジュールは、上流と同じ名前を保ちます。
- 建研の特定モジュールを基にJJJ側で追加・変更した実装は、`<建研モジュール名>_jjj.py`とします。例えば`section4_2_jjj.py`、`section4_2_a_jjj.py`、`section3_1_e_jjj.py`です。
- 建研の特定モジュールに対応しないJJJ独自機能は、節番号を流用せず、責務を表す名前にします。
- 建研コードに対応する関数・変数・式番号・処理順は可能な限り維持し、JJJ固有の処理は明確に区別して、必要に応じて独自機能モジュールへ委譲します。
- ファイル名の変更と計算ロジックの再構成を同じ境界に含めません。

既存モジュールをこの規則へ移行する前に、import元、再公開される名前、外部利用、テストを棚卸しし、現在のimport/API契約をテストで固定します。呼び出し側の更新は1つのバッチで行い、互換importが必要な場合だけ旧モジュールを一時的なshimとして残します。shimの削除は、利用がないことを確認した別の整理として扱います。

## バッチ化の条件

大量の挙動維持リファクタリングは、1回の指示で1つのバッチIssue、1つの作業ブランチ、1つの統合PRとして進めます。既定のバッチサイズは3〜5境界、上限は5境界です。候補が少ない場合や安全に分離できない場合は、無理に件数を満たしません。

次の条件をすべて満たす変更だけを同じバッチへ含めます。

- 目的、対象レイヤー、依存方向、検証方法が共通している
- 各境界を単独でレビュー、テスト、取り消しできる
- 各境界の変更後もブランチが実行可能な状態を保つ
- 公開API、入力・出力契約、計算式、Phase 5基準値を変更しない
- バッチ全体の差分を1つのPRで説明し、レビューできる

各境界は、原則として1つの意味のあるcommitにします。境界ごとに対象を絞ったテストを実行し、バッチ完成後にリポジトリ必須テスト、Phase 5回帰、計算エンジン履歴テスト、CIを1回ずつ実行します。これにより、独立した履歴と切り戻し単位を維持しながら、全テストとPR運用の待ち時間をまとめます。

調査中に次のいずれかが判明した境界は、そのバッチから外して単独Issueまたは次のバッチへ移します。

- 挙動変更、計算式変更、上流同期、基準値変更が必要になった
- 公開契約や複数レイヤーへ影響が広がった
- 他の境界へ依存し、単独でcommitまたは取り消しできない
- 対象テストが失敗し、原因をその境界内に限定できない
- 差分が大きくなり、残りの境界と一緒にレビューしにくい

## 完了済み

- [PR #5](https://github.com/iguchi-lab/Verification-Platform-Next/pull/5): 建築研究所由来コードと独自コードの境界を文書化し、逆依存の許可リストと計算エンジンCIを追加しました。
- [PR #6](https://github.com/iguchi-lab/Verification-Platform-Next/pull/6): 計算時のInjector状態を実行コンテキスト内へ限定し、例外、入れ子、スレッド、非同期タスクの分離をテストしました。
- [PR #8](https://github.com/iguchi-lab/Verification-Platform-Next/pull/8): `constants.py` のオプションEnum依存を明示importに置き換え、従来の再公開名とVAV既定値を契約テストで固定しました。
- [PR #10](https://github.com/iguchi-lab/Verification-Platform-Next/pull/10): `main.py` のDIコンテナ由来のワイルドカードimportを廃止し、実際に使用する型とEnumを定義元から明示importしました。
- [PR #12](https://github.com/iguchi-lab/Verification-Platform-Next/pull/12): `main.py` の結果モデル依存を `ResultSummary` と `SutValues` の明示importへ置き換え、残存ワイルドカード許可リストを縮小しました。
- [PR #14](https://github.com/iguchi-lab/Verification-Platform-Next/pull/14): jjjexperiment.common のワイルドカードimportを14モジュールから一括廃止し、AST境界テストで再導入を防止しました。
- [PR #16](https://github.com/iguchi-lab/Verification-Platform-Next/pull/16): 独立した3〜5境界を1つのIssue・ブランチ・PRで扱うバッチ運用と、履歴を残すマージ方式を文書化しました。
- [PR #18](https://github.com/iguchi-lab/Verification-Platform-Next/pull/18): options由来のワイルドカードimportを5境界で廃止し、境界ごとのcommitとAST契約テストを追加しました。
- [PR #20](https://github.com/iguchi-lab/Verification-Platform-Next/pull/20): 建研コードとの対応を追跡できるよう、JJJ変更版を `<建研モジュール名>_jjj.py` とする命名規則と段階的な移行手順を文書化しました。
- [PR #22](https://github.com/iguchi-lab/Verification-Platform-Next/pull/22): `jjjexperiment.inputs.options` の残存ワイルドカードimportを4つの実装境界で廃止し、実装側の許可集合を空にしました。
- [PR #24](https://github.com/iguchi-lab/Verification-Platform-Next/pull/24): 電中研と床下空調の2つの実装境界を明示importへ整理し、実装モジュール全体の残存ワイルドカードimportをAST契約で固定しました。
- [PR #26](https://github.com/iguchi-lab/Verification-Platform-Next/pull/26): `denchu_2` の公開37名と `denchu_1` 由来27名の再公開契約を固定したうえで、実装モジュールのワイルドカードimport許可集合を空にしました。
- [PR #28](https://github.com/iguchi-lab/Verification-Platform-Next/pull/28): 電中研モデルのテスト3境界を明示importへ置き換え、電中研テストのワイルドカードimport許可集合を空にしました。
- [PR #30](https://github.com/iguchi-lab/Verification-Platform-Next/pull/30): ルート・統合テスト5境界のoptionsワイルドカードimportを廃止し、残存する潜熱評価と床下空調の2境界まで許可リストを縮小しました。
- [PR #32](https://github.com/iguchi-lab/Verification-Platform-Next/pull/32): テスト・テスト支援層の残存ワイルドカードimportを4境界で廃止し、建研由来APIを直接検証するoriginテストだけを明示的な例外として固定しました。
- [PR #34](https://github.com/iguchi-lab/Verification-Platform-Next/pull/34): `section4_2.py` と `section4_2_a.py` の利用APIを固定し、旧import互換性を維持しながらJJJ変更版を `_jjj` 命名へ移行しました。
- [PR #36](https://github.com/iguchi-lab/Verification-Platform-Next/pull/36): 床下空調の建研節・式に対応する5モジュールを、旧import互換性と計算結果を維持しながら `_jjj` 命名へ移行しました。
- [PR #38](https://github.com/iguchi-lab/Verification-Platform-Next/pull/38): `calc_Q_UT_A` の公開契約、計算順序、建研由来コード、Phase 5結果を維持しながら、判定・事前計算の5責務を独立した内部関数へ分離しました。
- [PR #40](https://github.com/iguchi-lab/Verification-Platform-Next/pull/40): `calc_Q_UT_A` の式番号、負荷計算順序、CSV仕様を維持しながら、実負荷・未処理負荷・一次エネルギー・CSV出力の5責務を独立した内部関数へ分離しました。
- [PR #42](https://github.com/iguchi-lab/Verification-Platform-Next/pull/42): `calc_Q_UT_A` の列順、直接代入、`assign`の世代を維持しながら、終端のDataFrame列組み立て5責務を分離し、関数本体を77行縮小しました。
- [PR #44](https://github.com/iguchi-lab/Verification-Platform-Next/pull/44): `calc_Q_UT_A` の式番号、分岐優先順位、配列形状、評価回数、インプレース更新を維持しながら、熱源風量、VAV配分、床下への3種類の熱移動補正を5境界へ分離し、関数本体を66行縮小しました。
- [PR #46](https://github.com/iguchi-lab/Verification-Platform-Next/pull/46): `calc_Q_UT_A` の繰越あり・なし両経路で、出口要求状態、出口湿度、出口温度、供給風量上限、吹出温度の5境界を共通化し、式間の状態更新順と診断フラグを維持したまま関数本体を35行縮小しました。
- [PR #48](https://github.com/iguchi-lab/Verification-Platform-Next/pull/48): `calc_Q_UT_A` の繰越あり・なし両経路で、標準/潜熱方式の負荷・能力上限とRAC/電中研方式の暖冷房能力を4境界へ共通化し、評価順、ログ、中間出力を維持したまま関数本体を82行縮小しました。
- [PR #50](https://github.com/iguchi-lab/Verification-Platform-Next/pull/50): `calc_Q_UT_A` の過剰熱量繰越8760時刻ループから、繰越判定、式(8)/(9)、式(46)、式(48)の4境界を1時刻単位へ分離し、初期値、前時刻スライス、評価順を維持したまま関数本体を53行縮小しました。

この一覧は完了した設計判断を把握するためのものです。次の作業は必ず最新の`main`とGitHub上のIssue・PRを確認して決めます。

## 次の候補

以下は候補であり、着手順ではありません。調査結果をIssueに記録し、同じ目的と検証方法を持ち、独立してcommitできる境界を原則3〜5件選んで1バッチにします。

1. `jjjexperiment`のモジュールと公開APIを棚卸しし、利用箇所のないコード、建研モジュールに対応する変更版、独自機能の境界を区別する。
2. `carryover_heat/section4_2.py`など節番号を持つ残存独自モジュールが、建研対応版か純粋な独自機能かを判定し、前者は`_jjj`命名、後者は責務を表す名前へ段階的に移行する。
3. `jjjexperiment`に残るワイルドカードimportを棚卸しし、同じ依存元を持つ3〜5境界ずつ明示的なimportへ置き換える。
4. `calc_Q_UT_A` の次段階として、床下空調の要求温度・吹出温度補正を、旧ロジック、新ロジック、繰越経路の差異と処理順、建研由来の変数名を維持した内部フェーズへ段階的に分離する。
5. 既存の`pyhees -> jjjexperiment`逆依存を独立して検証できる境界へ分け、同種の3〜5境界ずつ削減する。
6. カレントディレクトリ、グローバル状態、暗黙のファイル名などの副作用を境界へ集約する。
7. 辞書と長い引数列を、既存契約と建研コードとの対応を保ったまま内部DTOや型付き結果へ段階的に整理する。

## 1バッチの進め方

1. 最新の`main`へ同期します。
2. `.github/ISSUE_TEMPLATE/refactoring.yml`からIssueを作成します。
3. バッチ共通の目的、非対象、保持する挙動、検証方法と、3〜5件の境界チェックリストをIssueに記入します。
4. 専用ブランチを作り、バッチ全体と各境界の変更前テストを追加または確認します。
5. 境界を1件ずつ変更し、対象テストの成功を確認して独立commitにします。
6. 境界が停止条件に該当した場合はバッチから外し、残りの境界を続行します。
7. バッチ完成後に必須テストをすべて実行し、境界別commitと検証結果をPRへ記録します。
8. Draft PRで統合差分を確認し、CI成功後にレビュー可能へ変更します。
9. マージ後、Issueの全境界、完了条件、次候補を更新します。

## マージ方式

- 複数の独立した境界commitを含むバッチPRは、履歴と個別の切り戻し単位を残すため、merge commitを既定とします。
- 単一境界のPR、または途中commitに独立したレビュー価値がないPRは、squash mergeを選べます。
- 各commitが自己完結し、線形履歴を優先する場合はrebase mergeも選べます。ただしcommit SHAが変わり、バッチを示すmerge commitが残らない点をPRで明示します。
- マージ方式にかかわらず、Draft PR、必須CI、Issue更新は省略しません。

## 検証

各境界の変更後は、その境界に対応する最小のテストを実行します。バッチ内の全境界が完成した後、計算コードまたはその境界を変更した場合は、リポジトリルートで次を1回実行します。

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

## バッチ完了通知

別のPCで作業中でも完了を把握できるように、Issueで希望されたバッチは、CI成功、マージ、Issue更新まで完了した直後にメールまたはSlackで通知します。通知にはIssue、PR、マージ結果、テスト結果、次候補へのリンクを含めます。

通知先のアドレスやチャンネルは公開Issueへ記載せず、Codexタスク側で指定します。メールは接続済みアカウント本人宛てに送信できます。Slackはプラグインの導入とワークスペース接続が済んでいる場合に送信します。通知に失敗してもマージ結果は変更せず、失敗理由をCodexタスクへ報告します。

## PCを切り替えるとき

作業中のPCで次を確認します。

```bash
git status
git push -u origin <作業ブランチ>
```

Issueへ次の内容を追記します。

- 作業ブランチと関連PR
- 完了した境界と各commit
- 未完了またはバッチから外した境界と次の1操作
- 実行済みテストと結果
- 判断が必要な点

別のPCではリポジトリをcloneするか、既存cloneを最新化し、Issueに記録されたブランチをcheckoutします。未commitの変更がある場合は先に退避またはcommitし、上書きしません。

## Codexへの開始指示

新しいPCまたは新しいCodexタスクでは、バッチIssue番号を指定して次のように依頼します。

```text
このリポジトリの計算コードのリファクタリングを続けます。

最初にAGENTS.md、docs/ARCHITECTURE.md、docs/REFACTORING.md、
packages/pyhees-jjj/UPSTREAM.mdとGitHub Issue #<番号>を読んでください。
最新のmain、関連PR、作業ブランチの状態も確認してください。

機能追加、計算式変更、上流更新、Phase 5基準値の変更は行わず、
建研コードに対応する節、関数、変数、式番号、処理順を可能な限り維持してください。
建研モジュールのJJJ変更版には<建研モジュール名>_jjj.pyの命名規則を適用し、
Issueに記載された挙動維持のリファクタリングを、最大5境界まで進めてください。
着手前にバッチ共通の対象、非対象、保持する挙動、境界一覧、実行するテストを説明してください。
各境界を独立したcommitにし、境界ごとの対象テストと、バッチ完成後の必須テストを実行してください。
停止条件に該当する境界は無理に進めず、バッチから外してIssueに理由を記録してください。
作業終了時はcommit・pushし、1つのDraft PRとIssueに境界別commit、検証結果、マージ方式、次の操作を記録してください。
完了通知が指定されている場合は、CI成功、マージ、Issue更新の後に指定された方法で通知してください。
```

Issueがまだない場合は、実装を始めず、コードを調査して同じ目的と検証方法を持つ3〜5件の候補を1つのバッチIssueとして提案します。安全にまとめられない候補は単独Issueとして分離します。
