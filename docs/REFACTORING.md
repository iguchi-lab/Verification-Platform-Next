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
2. 1回の指示では、同じ目的と検証方法を持つ20〜30境界を1つの作業パッケージとして扱い、レビュー可能な2〜3件のPRへ分割します。
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

既存モジュールをこの規則へ移行する前に、import元、再公開される名前、外部利用、テストを棚卸しし、現在のimport/API契約をテストで固定します。呼び出し側の更新は1つのPRで行い、互換importが必要な場合だけ旧モジュールを一時的なshimとして残します。shimの削除は、利用がないことを確認した別の整理として扱います。

## 作業パッケージとPRの単位

大量の挙動維持リファクタリングは、1回の指示で20〜30境界を1つの作業パッケージとして進めます。作業パッケージは1つの追跡Issueで管理し、原則2〜3件のPRへ分割します。候補が少ない場合、安全に分離できない場合、または停止条件に該当する場合は、無理に件数を満たしません。

1つのPRは8〜12境界を既定とし、上限は15境界です。20〜30境界を1つのPRへまとめるのは、同じ関数・同じ処理段階・同じ不変条件に限定され、差分を独立してレビューできる例外的な場合だけとします。各境界は原則1 commitとし、5境界ごとに対象テストと静的検査を実行するチェックポイントを設けます。全体テスト、Phase 5、計算エンジン内部テスト、GitHub ActionsはPRごとに実行します。

次の条件をすべて満たす変更だけを同じPRへ含めます。

- 目的、対象レイヤー、依存方向、検証方法が共通している
- 各境界を単独でレビュー、テスト、取り消しできる
- 各境界の変更後もブランチが実行可能な状態を保つ
- 公開API、入力・出力契約、計算式、Phase 5基準値を変更しない
- PR全体の差分を1回のレビューで追跡できる

調査中に次のいずれかが判明した境界は、そのPRまたは作業パッケージから外して単独Issueまたは次の作業パッケージへ移します。

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
- [PR #52](https://github.com/iguchi-lab/Verification-Platform-Next/pull/52): `calc_Q_UT_A` の床下空調温度補正を、熱繰越の旧方式1st/2nd、新方式1st/2nd、通常計算の旧方式2ndの5境界へ分離し、`np.clip`と`np.where`、逆算フラグ、定格上下限、診断出力順を維持したまま関数本体を131行縮小しました。
- [PR #54](https://github.com/iguchi-lab/Verification-Platform-Next/pull/54): `calc_Q_UT_A` の通常経路から、新床下空調の式(8)/(9)負荷補正、式(46)居室温度、式(48)非居室温度の3境界を分離し、新方式8760時刻順、従来式の引数列、調査出力順を維持したまま関数本体を60行縮小しました。
- [PR #56](https://github.com/iguchi-lab/Verification-Platform-Next/pull/56): `calc_Q_UT_A` の繰越有無分岐前から、式(52)/(49)/(47)/(11)/(10)の5境界を分離し、新床下空調と従来式の分岐、式番号、計算引数、DataFrame世代と列順を維持したまま関数本体を68行縮小しました。
- [PR #58](https://github.com/iguchi-lab/Verification-Platform-Next/pull/58): `calc_Q_UT_A` 冒頭から、気象条件、居室・非居室面積と式(67)、式(66)/(65)/(64)の5境界を分離し、取得順、合計引数、DataFrame直接代入順を維持したまま関数本体を47行縮小しました。
- [PR #60](https://github.com/iguchi-lab/Verification-Platform-Next/pull/60): `calc_Q_UT_A` の式(63)から式(50)周辺を、局所換気、全般換気、間仕切、等価外気温度・ダクト長さ、負荷バランス時の室内・ダクト周囲状態の5境界へ分離し、式番号、評価順、DataFrame直接代入と`assign`の世代・列順を維持したまま関数本体を35行縮小しました。
- [PR #62](https://github.com/iguchi-lab/Verification-Platform-Next/pull/62): `calc_Q_UT_A` の式(40)初期熱源出力、式(39)最低風量、定格熱源能力、床下地盤応答・補正要否、VAV前風量反復・出力列組み立ての5境界を分離し、新床下補正の有無、1回・2回の再計算順、DataFrame直接代入と2世代の`assign`を維持したまま関数本体を49行縮小しました。
- [PR #64](https://github.com/iguchi-lab/Verification-Platform-Next/pull/64): `calc_Q_UT_A` の式(53)非居室絶対湿度、式(52)非居室温度分岐、式(49)/(47)実湿度、式(11)/(10)負荷バランス、過剰熱量繰越の時刻状態初期化を5境界へ分離し、式番号、新床下分岐、DataFrame世代、配列形状・生成順、季節取得順を維持したまま関数本体を22行縮小しました。
- [PR #66](https://github.com/iguchi-lab/Verification-Platform-Next/pull/66): 過剰熱量繰越なし経路の式(9)/(8)負荷、計算モデル別能力、式(20)/(19)熱源入口、熱源出口要求・床下1st補正、出口・供給状態・床下2nd補正の5境界を分離し、モデル分岐、能力上限、診断順、新旧床下補正を維持したまま`calc_Q_UT_A`を74行縮小しました。
- [PR #68](https://github.com/iguchi-lab/Verification-Platform-Next/pull/68): 20境界の作業パッケージ運用を文書化し、繰越時刻ループと分岐後出力の10境界を分離して、`calc_Q_UT_A`を98行縮小しました。
- [PR #69](https://github.com/iguchi-lab/Verification-Platform-Next/pull/69): 式(14)/(42)/(35)/(34)/(13)/(12)、実負荷、未処理負荷、一次エネルギー、最終出力の10境界を分離し、作業パッケージ全体で`calc_Q_UT_A`を554行から423行へ131行縮小しました。
- [PR #72](https://github.com/iguchi-lab/Verification-Platform-Next/pull/72): `section4_2_jjj.py`の能力、床下地盤応答、VAV前風量、熱源出口状態など前半10境界の複数戻り値を、建研由来の変数名と並びを保つ内部`NamedTuple`へ整理しました。
- [PR #73](https://github.com/iguchi-lab/Verification-Platform-Next/pull/73): 実負荷、未処理負荷、気象・面積、室・ダクト状態、繰越状態など後半10境界を内部`NamedTuple`へ整理し、繰越有無で同じ並びを持つ能力状態と供給状態を共通型にしました。作業パッケージ全体で20境界を型付き結果化し、既存のtuple互換性、戻り値順、式・評価順を維持しました。
- [PR #76](https://github.com/iguchi-lab/Verification-Platform-Next/pull/76): `section4_2_jjj.py`の型付き結果を利用側でも名前付き属性として参照する前半12境界を整理し、30〜40境界を12〜15境界ずつのPRへ分割する作業パッケージ方針を文書化しました。
- [PR #77](https://github.com/iguchi-lab/Verification-Platform-Next/pull/77): 型付き結果の残り8利用境界と、長い引数列を内部コンテキストへまとめる入力側の前半4境界を整理しました。
- [PR #78](https://github.com/iguchi-lab/Verification-Platform-Next/pull/78): 入力側の残り12境界を内部コンテキストへ整理しました。PR #76〜#78の作業パッケージ全体で36境界を完了し、建研由来の変数名、式番号、評価順、配列形状、公開APIを維持しました。
- [PR #81](https://github.com/iguchi-lab/Verification-Platform-Next/pull/81): 熱源・VAV・時刻負荷に関する内部ヘルパー12境界の長い引数列を、建研由来の変数名と処理順を保つ入力コンテキストへ整理しました。
- [PR #82](https://github.com/iguchi-lab/Verification-Platform-Next/pull/82): 負荷・出力・床下補正に関する内部ヘルパー12境界を入力コンテキストへ整理しました。
- [PR #83](https://github.com/iguchi-lab/Verification-Platform-Next/pull/83): 室温・状態準備に関する内部ヘルパー12境界を入力コンテキストへ整理しました。PR #81〜#83の作業パッケージ全体で36境界を完了し、計算式、評価順、分岐条件、配列形状、公開APIを維持しました。

この一覧は完了した設計判断を把握するためのものです。次の作業は必ず最新の`main`とGitHub上のIssue・PRを確認して決めます。

## 次の候補

以下は候補であり、着手順ではありません。調査結果をIssueに記録し、同じ目的と検証方法を持ち、独立してcommitできる30〜40境界を1つの作業パッケージとして選び、12〜15境界ずつのPRへ分割します。同種で機械的な変更に限り、1 PRを最大18境界まで拡大できます。

1. `jjjexperiment`のモジュールと公開APIを棚卸しし、利用箇所のないコード、建研モジュールに対応する変更版、独自機能の境界を区別する。
2. `carryover_heat/section4_2.py`など節番号を持つ残存独自モジュールが、建研対応版か純粋な独自機能かを判定し、前者は`_jjj`命名、後者は責務を表す名前へ段階的に移行する。
3. `jjjexperiment`に残るワイルドカードimportを棚卸しし、同じ依存元を持つ8〜12境界ずつ明示的なimportへ置き換える。
4. `calc_Q_UT_A` の次段階として、残る8760時刻ループのオーケストレーションと抽出済みヘルパーの長い引数列を、建研の式番号、時刻スライス、評価順を追跡できる内部コンテキストへ段階的に整理する。
5. 既存の`pyhees -> jjjexperiment`逆依存を独立して検証できる境界へ分け、同種の8〜12境界ずつ削減する。
6. カレントディレクトリ、グローバル状態、暗黙のファイル名などの副作用を境界へ集約する。
7. 辞書と長い引数列を、既存契約と建研コードとの対応を保ったまま内部DTOや型付き結果へ段階的に整理する。`section4_2_jjj.py`では、複数戻り値20境界をPR #72/#73、利用側20境界と入力側16境界をPR #76〜#78、内部ヘルパー入力36境界をPR #81〜#83で整理済みです。次は残るオーケストレーション境界や他モジュールを対象とする。

## 1作業パッケージの進め方

1. 最新の`main`へ同期します。
2. `.github/ISSUE_TEMPLATE/refactoring.yml`からIssueを作成します。
3. 作業パッケージ共通の目的、非対象、保持する挙動、検証方法、30〜40件の境界チェックリスト、PR分割案をIssueに記入します。
4. 最初のPR用ブランチを作り、PR全体と各境界の変更前テストを追加または確認します。
5. 境界を1件ずつ変更し、対象テストの成功を確認して独立commitにします。
6. 5境界ごとに対象テストと静的検査を実行し、チェックポイント結果を記録します。
7. 境界が停止条件に該当した場合はPRまたは作業パッケージから外し、残りの境界を続行します。
8. PRの12〜15境界（同種で機械的な変更は最大18境界）が完成したら必須テストをすべて実行し、境界別commitと検証結果をPRへ記録します。
9. Draft PRで統合差分を確認し、CI成功後にレビュー可能へ変更してmergeします。
10. 最新の`main`へ同期し、次のPR用ブランチで手順4〜9を繰り返します。
11. 全PRのmerge後、Issueの全境界、完了条件、次候補を更新します。

## マージ方式

- 複数の独立した境界commitを含むPRは、履歴と個別の切り戻し単位を残すため、merge commitを既定とします。
- 単一境界のPR、または途中commitに独立したレビュー価値がないPRは、squash mergeを選べます。
- 各commitが自己完結し、線形履歴を優先する場合はrebase mergeも選べます。ただしcommit SHAが変わり、作業単位を示すmerge commitが残らない点をPRで明示します。
- 作業パッケージ内のPR間は依存順を明記し、先行PRをmergeして最新の`main`へ同期してから次のPRを開始します。
- マージ方式にかかわらず、Draft PR、必須CI、Issue更新は省略しません。

## 検証

各境界の変更後は、その境界に対応する最小のテストを実行します。5境界ごとのチェックポイントでは対象テストと`ruff check .`を実行します。PR内の全境界が完成した後、計算コードまたはその境界を変更した場合は、リポジトリルートで次を1回実行します。

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

## PR・作業パッケージ完了通知

別のPCで作業中でも完了を把握できるように、Issueで希望された作業パッケージは、各PRのCI成功・merge・Issue更新の直後と、作業パッケージ全体の完了時にメールまたはSlackで通知します。通知にはIssue、PR、マージ結果、テスト結果、完了境界数、次のPRまたは次候補へのリンクを含めます。

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

新しいPCまたは新しいCodexタスクでは、作業パッケージIssue番号を指定して次のように依頼します。

```text
このリポジトリの計算コードのリファクタリングを続けます。

最初にAGENTS.md、docs/ARCHITECTURE.md、docs/REFACTORING.md、
packages/pyhees-jjj/UPSTREAM.mdとGitHub Issue #<番号>を読んでください。
最新のmain、関連PR、作業ブランチの状態も確認してください。

機能追加、計算式変更、上流更新、Phase 5基準値の変更は行わず、
建研コードに対応する節、関数、変数、式番号、処理順を可能な限り維持してください。
建研モジュールのJJJ変更版には<建研モジュール名>_jjj.pyの命名規則を適用し、
Issueに記載された挙動維持のリファクタリングを、1作業パッケージ20〜30境界で進めてください。
着手前に作業パッケージ共通の対象、非対象、保持する挙動、境界一覧、PR分割、実行するテストを説明してください。
1PRは8〜12境界、上限15境界とし、各境界を独立したcommitにしてください。
5境界ごとの対象テスト・静的検査と、各PR完成後の必須テストを実行してください。
停止条件に該当する境界は無理に進めず、PRまたは作業パッケージから外してIssueに理由を記録してください。
各PRの終了時はcommit・pushし、Draft PRとIssueに境界別commit、検証結果、マージ方式、次の操作を記録してください。
CI成功後にmergeし、最新mainへ同期して同じIssueの次PRを続けてください。
完了通知が指定されている場合は、各PRと作業パッケージのCI成功、merge、Issue更新の後に指定された方法で通知してください。
```

Issueがまだない場合は、実装を始めず、コードを調査して同じ目的と検証方法を持つ20〜30件の候補を1つの作業パッケージIssueとして提案し、8〜12境界ずつのPRへ分割します。安全にまとめられない候補は別の作業パッケージへ分離します。
