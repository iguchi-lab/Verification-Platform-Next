# ドキュメント一覧

初めて使う場合は[入力画面ガイド](input_guide.md)から読んでください。
通常の入力は①～⑦で確認し、⑧は詳細条件や個別修正の比較が必要な場合に開きます。
TGの能力・効率も⑤⑥の中で設定でき、別の入力一式を追加する必要はありません。

## 使い方を調べる

| 知りたいこと | 文書 |
|---|---|
| JSONの読込み、入力順序、RAC効率、ピーク負荷・湿度グラフ、CSV・ZIPの保存 | [入力画面ガイド](input_guide.md) |
| 自立とTGの違い、TG標準計算・個別比較、集計範囲 | [自立方式とTG方式の切替](tg_calculation_method.md) |
| 初期状態から個別修正やRAC置換の比較条件を設定する | [修正内容ごとの設定方法](calculation_settings_from_default.md) |
| 自立で床下換気・床下空調を使う | [床下関連入力ガイド](underfloor_ac_input_guide.md) |

## 計算根拠・検証記録を調べる

以下は、自立の計算根拠と、記載した条件での検証記録です。記録中の旧版番号・数値・資料ハッシュは、
検証の追跡に必要なため残しています。最新版の全機能の操作説明や、すべての入力条件での一致保証ではありません。

| 知りたいこと | 文書 |
|---|---|
| 床下空調の数式と変更理由の概要 | [床下空調の7つの変更点](underfloor_ac_seven_changes.md) |
| Excel床下14との比較条件・一致精度・数値基準 | [Excelとの床下計算整合](underfloor_ac_excel_alignment.md) |
| 採用値・資料間の相違・設計判断の詳細 | [床下空調7変更点の設計検証台帳](underfloor_ac_seven_point_design_review.md) |
| 建研本家・旧Verification Platformから変えた式と理由 | [計算差分台帳](calculation_differences.md) |

## 更新・開発・公開を調べる

| 知りたいこと | 文書 |
|---|---|
| 変更日・関連PR・利用者への影響 | [更新履歴の詳細](update_history.md) |
| 正式版ごとの変更要約と未リリースの更新 | [CHANGELOG](../CHANGELOG.md) |
| コード構成と入力・計算・画面の責任範囲 | [アーキテクチャ](ARCHITECTURE.md) |
| 製品版、成果物マニフェスト、リリース手順 | [リリース手順](RELEASING.md) |
| 開発時の検証・PR作成 | [Contributing](../CONTRIBUTING.md) |
| 建研由来コードの固定版と更新方針 | [上流pyheesの追跡方針](../packages/pyhees-jjj/UPSTREAM.md) |

## この文書群の確認基準

操作説明は、2026-10-23のTG入力統合（[PR #213](https://github.com/iguchi-lab/Verification-Platform-Next/pull/213)）を含むmain、
製品版 **1.6.0**・入力仕様 **261023**・TG仕様 **tg-2026-10-v2** に照合しています。
mainへの反映と公開Web版へのデプロイは別です。実際の計算版は出力マニフェストのソースコミットで確認してください。

画面や入力契約を変更する場合は、関連ガイドの選択肢・配置・初期値・操作順を併せて更新します。
過去の検証記録は、操作説明と区別し、固定した数値基準や検証対象を明記したまま管理します。
