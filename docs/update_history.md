# 更新履歴の詳細

利用者からの指摘に対応した変更を、日付・目的・計算への影響とともに記録します。
日付は日本時間のmainへのマージ日です。正式版ごとの全履歴は
[CHANGELOG](../CHANGELOG.md)、操作手順は[入力画面ガイド](input_guide.md)を参照してください。

## 版番号と公開Web版の関係

2026-10-23時点の正式版は **v1.6.0** です。10月22日以降の変更はmainへ取り込んだ
追加更新であり、新しい正式タグは発行していません。画面の製品版表示が同じでも、
ソースコミットによって内容が異なります。

mainへのマージとCloud Runへの公開は別の操作です。公開履歴は
[Deploy to Cloud Run](https://github.com/iguchi-lab/Verification-Platform-Next/actions/workflows/deploy-cloud-run.yml)
で、計算に使ったソースは出力マニフェストのコミット情報で確認できます。

## 2026-10-23：RAC活用型の効率入力を整理

関連：[PR #211](https://github.com/iguchi-lab/Verification-Platform-Next/pull/211)

従来は能力を直接入力するとCOPも直接入力する扱いでしたが、効率区分の選択欄も
表示されるため、どちらが計算に使われるか分かりにくい状態でした。
自立方式のRAC活用型（省エネ法モデル）では、能力と効率を別々に設定します。

| 効率の設定方法 | 表示する入力欄 | 計算に使う値 |
|---|---|---|
| 規定値を使用 | なし | 区分「は」相当の式で算定したCOP |
| 効率区分を指定 | い・ろ・は | 選択区分と定格冷房能力から算定したCOP |
| 定格COPを直接入力〔検証用〕 | 定格暖房COPまたは定格冷房COP | 入力したCOP |

- 暖房・冷房は同じ構成で、異なる方法を選択できます。
- 区分とCOPの入力欄は同時に表示せず、非表示の値は効率計算に使用しません。
- 能力を直接入力し、効率は区分から算定する組合せも選べます。
- COPは定格能力÷定格消費電力であり、APFではありません。正の有限値を指定します。
- 能力はWで入力し、最大能力は定格能力以上とします。
- 手入力欄の初期値は標準条件を参考にした固定値です。面積に追従しないため実機仕様へ変更してください。

**互換性：** 新JSONは`rac_efficiency_mode`で設定方法を保存します。このキーがない
旧JSONは、能力直接入力時に保存COPを優先する従来ルールを維持します。暖房の区分指定を
持たない旧JSONは、従来どおり冷房COPから暖房COPを換算します。TG方式はTG専用の設定を
使います。建研由来の計算式は変更していません。

**検証：** 画面・入力・サービス459件、Phase 5試験1件（標準・RACの2ケース）、
計算エンジン559件、Ruffが成功しています。年間CSVの数値基準は変更していません。
既存計算のゼロ除算・無効演算等の警告はPRに記録しています。

## 2026-10-22：入力画面と結果の確認・取得を改善

| 指摘・要望 | 対応内容 | 関連PR |
|---|---|---|
| 暖房設備の機器仕様欄に余白が残る | 非表示の入力項目だけになった行も隠す | [#208](https://github.com/iguchi-lab/Verification-Platform-Next/pull/208) |
| 出力ファイルをまとめて取得したい | チェックボックス選択、全選択・全解除、ZIP一括ダウンロードを追加 | [#208](https://github.com/iguchi-lab/Verification-Platform-Next/pull/208) |
| 年間結果でピーク負荷を見たい | 暖冷房別の建物全体ピーク負荷・熱源機最大処理熱量と発生日時を表示 | [#208](https://github.com/iguchi-lab/Verification-Platform-Next/pull/208) |
| 代表期間の室内湿度を見たい | 居室・非居室・外気の相対湿度と絶対湿度を表示 | [#208](https://github.com/iguchi-lab/Verification-Platform-Next/pull/208) |
| プルダウンを読みやすくしたい | 交互の背景色と選択中の強調表示を追加 | [#208](https://github.com/iguchi-lab/Verification-Platform-Next/pull/208) |
| 小数を入力すると警告が出る | 小数入力を許可し、96項目の整数型への誤分類も修正 | [#209](https://github.com/iguchi-lab/Verification-Platform-Next/pull/209) |
| 配色変更後も選択肢と文字が重なる | 開いているメニューの親要素も前面へ出し、背面ラベルとの重なりを解消 | [#210](https://github.com/iguchi-lab/Verification-Platform-Next/pull/210) |

### 結果の読み方と計算への影響

**一括ダウンロード：** 詳細CSVは「CSVファイルを出力」を押した後で選択できます。
CSVと入力JSONなどをまとめてZIP化でき、従来の個別ダウンロードも使えます。
再計算や選択変更時には、前のZIPをクリアします。

**ピーク負荷：** 1時間平均値の年間最大です。冷房は同時刻の顕熱と潜熱を合計します。
瞬間最大値や、そのまま機器の必要定格能力を示す値ではありません。

**室内湿度：** 既存の計算系列を表示しています。居室の絶対湿度は冷房期は設定値、
暖房期・中間期は外気と同値で、相対湿度は各区画の温度と絶対湿度から換算します。
新しい湿気収支計算を追加した変更ではありません。

**小数入力：** 面積・外皮性能・効率・補正係数・能力などの入力値を、小数桁数を
制限せず計算へ渡します。従来、整数型に誤分類された項目で小数を入力していた場合は、
切り捨てがなくなるため結果が変わる可能性があります。既定値・整数値は維持します。

余白・配色・重なり順の修正と、結果の集計・グラフ追加は、計算式を変更しません。

### 設定ガイドの整備

[PR #206](https://github.com/iguchi-lab/Verification-Platform-Next/pull/206)で、
自立を基本とした修正内容別の設定手順を追加しました。
[PR #207](https://github.com/iguchi-lab/Verification-Platform-Next/pull/207)で、
RAC活用型への熱源置換と比較条件の設定を追記しました。
詳しくは[修正内容ごとの設定方法](calculation_settings_from_default.md)を参照してください。

## 2026-10-21：TG比較と年間集計の拡張

| 正式版 | 主な更新 | 関連PR |
|---|---|---|
| v1.6.0 | TGで修正内容を個別選択し、現行式・出口温度・最低風量・送風機特性・換気・間仕切り熱移動などを比較 | [#204](https://github.com/iguchi-lab/Verification-Platform-Next/pull/204)、[#205](https://github.com/iguchi-lab/Verification-Platform-Next/pull/205) |
| v1.5.2 | 年間結果に暖冷房合計を追加 | [#203](https://github.com/iguchi-lab/Verification-Platform-Next/pull/203) |
| v1.5.1 | 計算方式の表示を「自立」「TG」に統一 | [#202](https://github.com/iguchi-lab/Verification-Platform-Next/pull/202) |
| v1.5.0 | 従来方式とTG方式の切替、TGの風量・送風機・RAC計算と内訳出力を追加 | [#201](https://github.com/iguchi-lab/Verification-Platform-Next/pull/201) |

TGの個別比較はダクト式に対応し、RAC活用型はTG総合で使います。
TGと床下空調の組合せは未対応です。計算範囲は[TG方式の説明](tg_calculation_method.md)を参照してください。
これより前の版は[CHANGELOG](../CHANGELOG.md)に記録しています。

## 今後の記録方法

利用者に影響する変更は、実装PRでCHANGELOGのUnreleasedへ要約を追加します。
入力方法や計算結果に影響がある変更は、この文書にも背景・対象・旧入力との互換性・
検証内容・関連PRを追記します。正式リリース時にはUnreleasedの項目を該当版へ移し、
公開Web版への反映は成功したデプロイ履歴とソースコミットで確認します。
