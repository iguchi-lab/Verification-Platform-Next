# 建研本家・旧Verification Platformとの計算差分

## 1. 目的

Verification Platform Nextは、建築研究所等の技術的協力のもと公開されている
`BRI-EES-House/pyhees`を基礎とし、検証用の計算方法と入力機能を追加している。
そのため、数値結果が異なる場合は、少なくとも次の二つを区別する必要がある。

1. 建研本家に由来する式・実装のうち、物理または設定上の不整合と判断して
   Nextで変更した箇所
2. 旧Verification Platformの独自実装から、Nextで変更した箇所

本書は、この二種類の差を一つの台帳として管理する。建研本家の保守者による
公式な不具合認定ではないものは、「建研本家のバグ」と断定せず、
**建研本家の不具合候補**と表記する。

## 2. 比較基準

| 対象 | 基準 |
| --- | --- |
| 建研本家 | `BRI-EES-House/pyhees` Ver.3.10、commit `d5224c4a01def00a8421bcd2fcc0d4b4a5b88644` |
| 旧Verification Platform | Next移行時の基準commit `0f91ba8381df1b4960557b92b39339385cc9009f` |
| Verification Platform Next | ver.1.0.2、入力仕様 `260809` |

建研本家の版は[`packages/pyhees-jjj/UPSTREAM.md`](../packages/pyhees-jjj/UPSTREAM.md)、
Nextの製品版は[`jjjexperiment/release.py`](../packages/pyhees-jjj/src/jjjexperiment/release.py)
でも固定している。

## 3. 結論一覧

| ID | 不具合候補・変更点 | 建研本家 | 旧Verification Platform | Next（入力仕様260809） |
| --- | --- | --- | --- | --- |
| BRI-01 | 冷房時の居室・非居室間の間仕切熱移動の符号 | `+Q_trs` | `+Q_trs` | 既定OFFは`+Q_trs`、①をONにすると全経路で`-Q_trs` |
| BRI-02 | 全般換気なし時も区画別全般換気量を給気下限に使用 | 使用する | 使用する。最低風量直接入力時は過大値が拡大 | 既定OFFは建研式、②をONにすると換気下限と設備最低風量を分離 |

両項目とも既定値はOFFである。建研本家との比較照合ではOFF、物理的に正しいと
判断した方法を使う計算ではONにする。①と②は独立して選択できる。

## 4. BRI-01：冷房時の間仕切熱移動の符号

### 4.1 熱移動量の定義

式(11)の居室から非居室への熱移動量を次のように定義する。

```math
Q^{*}_{\mathrm{trs,prt},i}
=U_{\mathrm{prt}}A_{\mathrm{prt},i}
\left(
\theta^{*}_{\mathrm{HBR}}-\theta^{*}_{\mathrm{NR}}
\right)
\times 3600\times 10^{-6}
```

- $Q^{*}_{\mathrm{trs,prt},i}>0$：居室から非居室へ熱が流出する。
- $Q^{*}_{\mathrm{trs,prt},i}<0$：非居室から居室へ熱が流入する。

冷房顕熱負荷$L_{CS,i}$は、居室へ入る熱取得を正の大きさで表す。
したがって、居室から非居室へ熱が逃げる場合は冷房負荷が減り、非居室から
居室へ熱が入る場合は冷房負荷が増える。物理的な符号は次式となる。

```math
L^{*}_{CS,i}
=\max\left(
L_{CS,i}-Q^{*}_{\mathrm{trs,prt},i},
0
\right)
```

### 4.2 建研本家と旧版

建研本家Ver.3.10の式(9)実装は、冷房負荷へ間仕切熱移動を加算している。

```math
L^{*}_{CS,i}
=\max\left(
L_{CS,i}+Q^{*}_{\mathrm{trs,prt},i},
0
\right)
```

参照：建研本家
[`section4_2.py` 式(9)](https://github.com/BRI-EES-House/pyhees/blob/d5224c4a01def00a8421bcd2fcc0d4b4a5b88644/src/pyhees/section4_2.py#L645-L668)

この式では、居室から非居室へ熱が逃げる$Q^{*}_{\mathrm{trs,prt},i}>0$のときに
冷房負荷が増える。熱流の定義と冷房負荷の正方向が一致しないため、
物理上の不具合候補と判断した。

旧Verification Platformも、建研由来の式(9)をそのまま使用しており、
同じ加算式だった。また、過剰熱量繰越経路でも
`L_CS + Q_trs - carryover`としていた。

- [旧版の建研由来式(9)](https://github.com/iguchi-lab/pyhees-jjj/blob/0f91ba8381df1b4960557b92b39339385cc9009f/src/pyhees/section4_2.py#L670-L695)
- [旧版の過剰熱量繰越式](https://github.com/iguchi-lab/pyhees-jjj/blob/0f91ba8381df1b4960557b92b39339385cc9009f/src/jjjexperiment/carryover_heat/section4_2.py#L91-L132)

### 4.3 Nextの補正モード

新床下空調では、元の住宅負荷に含まれる断熱床経路を取り除くため、
床を通る符号付き熱流$\Delta L_{\mathrm{floor},i}$も同時に扱う。

```math
L^{*}_{CS,i}
=\max\left(
L_{CS,i}
-Q^{*}_{\mathrm{trs,prt},i}
+\Delta L_{\mathrm{floor},i},
0
\right)
```

実装：
[`underfloor_ac/section4_2_jjj.py`](../packages/pyhees-jjj/src/jjjexperiment/underfloor_ac/section4_2_jjj.py#L155-L167)

この符号は、説明資料9枚目、Excel床下14および物理的な熱流方向を照合して
採用した。ただし自動適用はせず、入力欄の
「① 冷房時の間仕切熱移動を物理的な符号に補正する」をONにした場合だけ使う。詳細は
[`underfloor_ac_seven_point_design_review.md`](underfloor_ac_seven_point_design_review.md)の
「式 (8)/(9)：熱損失を含む負荷バランス時の暖冷房負荷」
を参照する。

### 4.4 計算経路ごとの適用

| 計算経路 | ① OFF：建研互換 | ① ON：物理補正 |
| --- | --- | --- |
| 非床下・通常計算 | `L_CS + Q_trs` | `L_CS - Q_trs` |
| 過剰熱量繰越 | `L_CS + Q_trs - carryover` | `L_CS - Q_trs - carryover` |
| 新床下・通常計算 | `L_CS + Q_trs + delta_L_floor` | `L_CS - Q_trs + delta_L_floor` |
| 新床下・逐次ソルバー | `L_CS + Q_trs + delta_L_floor` | `L_CS - Q_trs + delta_L_floor` |

Excel床下14のGolden比較では①をONにする。建研本家の回帰比較ではOFFにする。

## 5. BRI-02：全般換気なし時の区画別給気下限

### 5.1 建研本家の不整合

建研本家には`general_ventilation`という全般換気機能の有無を表す入力がある。
`False`の場合、熱源機が搬送する全般換気量$V_{\mathrm{hs,vent}}$はゼロになる。

一方、式(44)ではこのフラグを参照せず、区画別全般換気量
$V_{\mathrm{vent},g,i}$を常に下限としている。

```math
V'_{\mathrm{supply},i}
=\max\left(
r_{\mathrm{supply},i}V'_{\mathrm{hs,supply}},
V_{\mathrm{vent},g,i}
\right)
```

- [建研本家の式(44)呼出し](https://github.com/BRI-EES-House/pyhees/blob/d5224c4a01def00a8421bcd2fcc0d4b4a5b88644/src/pyhees/section4_2.py#L173-L189)
- [建研本家の式(43)](https://github.com/BRI-EES-House/pyhees/blob/d5224c4a01def00a8421bcd2fcc0d4b4a5b88644/src/pyhees/section4_2.py#L1562-L1638)
- [建研本家の式(44)](https://github.com/BRI-EES-House/pyhees/blob/d5224c4a01def00a8421bcd2fcc0d4b4a5b88644/src/pyhees/section4_2.py#L1647-L1659)

標準住戸では、設備最低風量160 m3/hに対して式(44)の区画別風量が
次のようになる。

```text
[60.000000,
 32.650647,
 40.000000,
 21.215034,
 21.234750]

合計 = 175.100431 m3/h
```

これは丸め誤差ではなく、面積比で配分した風量へ区画別換気下限を適用したことで、
合計が設備最低風量を上回るために生じる。

### 5.2 旧Verification Platform

旧版も、`general_ventilation=False`であっても式(43)・式(44)へ
$V_{\mathrm{vent},g,i}$を渡していた。

さらに最低風量を直接入力する独自機能では、区画別換気量の合計が入力最低風量に
なるよう$V_{\mathrm{vent},g,i}$を比例拡大していた。そのため420 m3/h入力では、
同じ区画別`max`により次の結果になった。

```text
[157.500000,
  85.707948,
 105.000000,
  55.689464,
  55.741220]

合計 = 459.638632 m3/h
```

420 m3/hの直接入力は旧Verification Platformの追加機能であり、建研本家単体には
同じ入力経路がない。ただし、過大値を生む根本は、全般換気なしでも
区画別全般換気量を給気下限に使用する共通の実装にある。

参照：
[旧版の風量呼出し](https://github.com/iguchi-lab/pyhees-jjj/blob/0f91ba8381df1b4960557b92b39339385cc9009f/src/jjjexperiment/section4_2.py#L218-L381)

### 5.3 Nextの選択式補正

Nextでは、次の二つを別の物理量として扱う。

| 変数 | 意味 | 全般換気なし |
| --- | --- | --- |
| $V_{\mathrm{vent},g,i}$ | 住宅の全般換気量。住宅の換気負荷計算に使用 | 維持 |
| $V_{\mathrm{hs,vent},i}$ | 熱源機が搬送する区画別全般換気量。式(43)・式(44)の下限 | 0 |
| $V_{\mathrm{hs,min}}$ | 暖冷房運転時の設備最低風量 | 維持 |

入力欄の「② 全般換気なし時の給気風量下限を補正する」をONにした場合、
式(43)・式(44)へ渡す区画別換気下限だけをゼロにする。その後、暖房期・冷房期には
設備最低風量を独立して保証し、中間期はゼロとする。OFFでは建研本家と同じく、
`general_ventilation=False`でも区画別換気量を下限へ渡す。

- [区画別換気下限の切替](../packages/pyhees-jjj/src/jjjexperiment/section4_2_jjj.py#L1558-L1571)
- [VAV時の設備最低風量保証](../packages/pyhees-jjj/src/jjjexperiment/section4_2_jjj.py#L1886-L1937)
- [詳細な不具合修正メモ](../packages/pyhees-jjj/docs/風量設定_VAV_不具合修正メモ.md)

②をONにした場合の契約は次のとおりである。

| VAV | 全般換気 | 時期・状態 | 合計給気風量 |
| --- | --- | --- | --- |
| なし | なし | 暖冷房期サーモOFF | 設備最低風量と一致 |
| あり | なし | 暖冷房期サーモOFF | 設備最低風量と一致 |
| あり | なし | 暖冷房期小負荷 | 設備最低風量以上 |
| 任意 | なし | 中間期 | 0 m3/h |
| 任意 | あり | サーモOFF | 区画別全般換気量以上 |

## 6. 旧Verification Platformからの差分

この二件に限った旧版との差は次のとおりである。

| 項目 | 旧Verification Platform | Verification Platform Next（入力仕様260809） |
| --- | --- | --- |
| 冷房時の間仕切熱移動 | 建研式の`+Q_trs` | ①OFFは同じ。ONは非床下・繰越・新床下すべて`-Q_trs` |
| 全般換気なしの式(43)/(44)下限 | 区画別全般換気量を使用 | ②OFFは同じ。ONは区画別下限を0へ切替 |
| 最低風量直接入力 | `V_vent_g_i`を拡大し、区画別`max`で合計が過大になる場合がある | ②ONでは設備最低風量を換気量から分離 |
| VAVあり・全般換気なし | サーモOFF・小負荷時の設備下限が不明確 | ②ONでは暖冷房期に設備最低風量を明示的に保証 |
| 全般換気なしの中間期 | 給気またはファン電力が残る経路がある | 給気・ファン電力とも0 |

床下計算全体に関する旧版・Excel床下13・Excel床下14との差は、
[`underfloor_ac_seven_changes.md`](underfloor_ac_seven_changes.md)および
[`underfloor_ac_excel_alignment.md`](underfloor_ac_excel_alignment.md)に記録している。

## 7. 回帰試験

| 対象 | テスト |
| --- | --- |
| 非床下の①OFF/ON | [`test_section4_2_preparation.py`](../tests/test_section4_2_preparation.py) |
| 過剰熱量繰越の①OFF/ON | [`test_4_2_formula_8_9.py`](../packages/pyhees-jjj/src/tests/carryover_heat/test_4_2_formula_8_9.py) |
| 新床下の①OFF/ON | [`test_4_2_f8.py`](../packages/pyhees-jjj/src/tests/underfloor_ac/test_4_2_f8.py) |
| 全般換気なし・最低風量160/420 m3/h | [`test_section4_2_preparation.py`](../tests/test_section4_2_preparation.py#L923-L1001) |
| VAVあり・全般換気なし | [`test_section4_2_preparation.py`](../tests/test_section4_2_preparation.py#L1004-L1031) |

ver.1.0.2リリース時には、全体pytest、Phase 5、Excel床下14 Golden、
計算エンジン内部試験、RuffおよびGitHub Actionsの成功を確認している。

## 8. 今後の管理

1. 建研本家との差を追加するときは、建研の版・commit、式番号、物理的根拠、
   影響する計算経路を記録する。
2. 旧Verification Platformとの差を追加するときは、旧版の基準commitと
   Nextで変更したcommitまたはPRを記録する。
3. 「修正済み」は、対象となる全計算経路と回帰試験が揃った場合だけ使用する。
   一部経路だけの場合は「部分修正」と明記する。
4. 建研本家へ修正が取り込まれた場合は、そのcommitを記録し、Next側の
   アダプターを残すか上流へ戻すかを再評価する。
5. ①②の既定値はOFFを維持する。建研本家が修正された場合は、その版を基準に
   既定値およびチェック項目の廃止可否を再評価する。
