# Architecture

## 方針

このリポジトリは、1つの製品を1つのリポジトリで変更できるようにしつつ、計算エンジン、共通契約、UIの境界を維持するモノレポです。

## 構成

- `apps/gradio`: Gradio Web UIと実行オーケストレーション
- `packages/verification-core`: 入力項目、表示条件、デフォルト値、検証ルールの正本
- `packages/pyhees-jjj`: 固定コミットまでの履歴を保持して統合した計算エンジン
- `notebooks`: Colab用の薄いランチャー
- `tests`: パッケージをまたぐ契約・回帰テスト
- `regression/phase5`: 旧版との数値一致を保証する代表ケースと固定基準

## 依存方向

```text
apps/gradio
  ├── verification-core
  └── pyhees-jjj

verification-core
  └── 標準ライブラリのみ

pyhees-jjj
  ├── jjjexperiment（検証用プラットフォーム独自コード）
  └── pyhees（建築研究所由来コード）
```

UIから計算エンジンの内部モジュールを直接参照せず、公開された計算APIと結果モデルだけを使用します。

計算エンジン内の依存方向は `jjjexperiment -> pyhees` の一方向です。PR #140で移行前から残っていた `pyhees -> jjjexperiment` の逆依存をすべて除去しました。Verification Platform固有の定数、共有Enum、ログ、実行コンテキストは、上流由来ではない `pyhees.jjj_runtime` 接続アダプターへ `jjjexperiment` 側から登録します。契約テストで逆依存0件を固定し、新しい逆依存は追加しません。

## 開発の正本

Phase 5 完了後は、このモノレポがUI、入力契約、計算エンジンの開発正本です。`jjjexperiment` の修正は `packages/pyhees-jjj/src/jjjexperiment` で行い、同じ変更でエンジンテスト、契約テスト、Phase 5数値回帰を実行します。

移行元の `Verification-Platform` と `pyhees-jjj` は履歴確認と比較のための参照用です。建築研究所由来の `pyhees` 更新を取り込む場合も、影響を確認したうえでこのモノレポに反映します。

`packages/pyhees-jjj/src/pyhees` は建築研究所由来コードとして扱います。既存の独自変更を分離するまでは完全な上流コピーではありませんが、新しい独自機能はここへ直接追加せず、`jjjexperiment` または上流接続用のアダプターへ実装します。基準コミットと更新手順は `packages/pyhees-jjj/UPSTREAM.md` を正本とします。

## 入力スキーマ

入力項目の正本は `verification-core` に置きます。Gradio部品、JSONデフォルト値、入力検証、方式別の有効・無効条件、マニュアルの項目表は同じスキーマから生成します。

製品の入力JSONは宣言的な入力バインディングから生成します。旧NotebookのPythonフォームを
解釈する評価器は製品APIではなく、Phase 5で旧版との一致を確認するための非公開回帰専用
モジュールです。製品コードから旧フォーム評価器へ依存させません。

## 製品版と計算成果物

製品版の正本は`jjjexperiment.release`です。UI、入力契約、計算エンジンを
別々の日付ではなく、モノレポ全体のSemantic Versioningで管理します。
計算成果物のファイル名には製品版を付け、同じ接頭辞のJSONマニフェストへ
ソースコミット、上流pyhees版・コミット、床下仕様、入力SHA-256を記録します。
詳細な運用は[`RELEASING.md`](RELEASING.md)を参照します。
