# Architecture

## 方針

このリポジトリは、1つの製品を1つのリポジトリで変更できるようにしつつ、計算エンジン、共通契約、UIの境界を維持するモノレポです。

## 構成

- `apps/gradio`: Gradio Web UIと実行オーケストレーション
- `packages/verification-core`: 入力項目、表示条件、デフォルト値、検証ルールの正本
- `packages/pyhees-jjj`: 計算エンジン。履歴移行が完了するまでは外部Git依存
- `notebooks`: Colab用の薄いランチャー
- `tests`: パッケージをまたぐ契約・回帰テスト

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

## 入力スキーマ

入力項目の正本は `verification-core` に置きます。Gradio部品、JSONデフォルト値、入力検証、方式別の有効・無効条件、マニュアルの項目表は同じスキーマから生成します。
