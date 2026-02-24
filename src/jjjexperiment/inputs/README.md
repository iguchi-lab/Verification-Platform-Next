# インプットシステム

## 変更概要図

### BEFORE

```mermaid
flowchart LR

input1@{ shape: lin-doc, label: インプットファイル }
var1((変数))
var2((変数))
var3((変数))
var4((変数))
logic1[ロジック1]
logic2[ロジック2]
out1(((計算値1)))
out2(((計算値2)))

input1 --> var1 --> logic1 --> out1
var1 --> logic2
input1 --> var2 --> logic1
input1 --> var3 --> logic1
var3 --> logic2
input1 --> var4 --> logic2 --> out2

note1@{ shape: notch-rect, label: ✘ 変数がむき出しで存在、変化の危険 }
note1 -.- var4
note2@{ shape: notch-rect, label: ✘ 関数・変数がバラバラに存在 計算の度ただしい組合せが必要 }
note2 -.- logic2

```

### AFTER

```mermaid
flowchart LR

input2@{ shape: lin-doc, label: インプットファイル }
container[(データコンテナ)]
var5((変数))
var6((変数))
var7((変数))
var8((変数))
logic3[ロジック1]
logic4[ロジック2]
out3(((計算値1)))
out4(((計算値2)))

subgraph データクラス
    var5 --> logic3
    var6 --> logic3
    var6 --> logic4
    var7 --> logic3
    var7 --> logic4
    var8 --> logic4
end

note3@{ shape: notch-rect, label: ◎ 変数がデータクラス内に格納 変化の心配がない }
note3 -.- var5
note4@{ shape: notch-rect, label: ◎ 一緒に使われる関数・変数がセットで存在 }
note4 -.- logic4
note5@{ shape: notch-rect, label: ◎ 意味のまとまり（気候・間取り・外皮 等） }
note5 -.- データクラス

input2 --> container --> データクラス
logic3 --> out3
logic4 --> out4

```

## プログラム構成図

### BEFORE

```mermaid
flowchart LR

A@{ shape: doc, label: ユーザー入力 }
B[グローバル定数<br>constants.py]
C[変数展開<br>inputs.py<br>○○○○]
D[グローバルデータクラス<br>app_config.py]
E[計算処理]

proc2(全ての変数が別個<br>入力値/計算値が混在<br>○○○●○●●)

note1@{ shape: notch-rect, label: ✘トレースしづらい }
note2@{ shape: notch-rect, label: ✘大量の引数で渡される }

service(ロジックサービス)
subgraph どこからでも利用
    direction LR
    service
    B
    D
end
どこからでも利用 -.- note1

proc2 -.- note2
A --> C --> proc2 --> E
A --> D --> service --> E
A --> B --> E

```

### AFTER

```mermaid
flowchart LR

A@{ shape: doc, label: ユーザー入力 }
B[グローバル定数<br>constants.py]
E[計算処理]

F[データクラス間整合]
F0[共通データ]
F1[機能①データ]
F2[機能②データ]
subgraph データクラス
    direction LR
    F --> F0
    F --> F1
    F --> F2
end
service1[ロジックサービス1]
service2[ロジックサービス2]
F0 --> service1 --> E
F1 --> service1
F1 --> E
F1 --> service2 --> E
F2 --> service2
A --> F

note1@{ shape: notch-rect, label: 必須でないものを削減予定 }
note2@{ shape: notch-rect, label: まとまりのあるデータ }
note3@{ shape: notch-rect, label: グローバルデータクラスを除去 }

subgraph どこからでも利用
    direction LR
    B
end
note3 -.- どこからでも利用

note1 -.- B
note2 -.- F2
A --> B --> E

```

### 比較表

| 観点                 | BEFORE             | AFTER                  |
| -------------------- | ------------------ | ---------------------- |
| 変数の数             | 多い(全てバラバラ) | 少ない(関連でまとまり) |
| フローの数           | ３本(違いが曖昧)   | ２本(違いが明確)       |
| 入力値/計算値の区別  | つかない           | つく                   |
| 入力値が所属する機能 | ロジック内に埋没   | ファイル配置で明確化   |
| グローバル定数の数   | 多い               | 減らしやすい           |

