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
  └── pyhees由来コードと計算依存
```

UIから計算エンジンの内部モジュールを直接参照せず、公開された計算APIと結果モデルだけを使用します。

## 開発の正本

Phase 5 完了後は、このモノレポがUI、入力契約、計算エンジンの開発正本です。`jjjexperiment` の修正は `packages/pyhees-jjj/src/jjjexperiment` で行い、同じ変更で契約テストとPhase 5数値回帰を実行します。

移行元の `Verification-Platform` と `pyhees-jjj` は履歴確認と比較のための参照用です。建築研究所由来の `pyhees` 更新を取り込む場合も、影響を確認したうえでこのモノレポに反映します。

## 入力スキーマ

入力項目の正本は `verification-core` に置きます。Gradio部品、JSONデフォルト値、入力検証、方式別の有効・無効条件、マニュアルの項目表は同じスキーマから生成します。
