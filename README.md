# 自立循環型住宅 全館暖冷房委員会 検証用プラットフォーム

[自立循環プロジェクト](https://www.jjj-design.org/) の全館暖冷房委員会で開発している検証用プラットフォームの計算プログラムです。

[pyhees](https://github.com/BRI-EES-House/pyhees)（[エネルギー消費性能の算定⽅法](https://www.kenken.go.jp/becc/house.html) に基づく計算ファイル）をベースにして、一部計算方法を追加・変更しています。

# ディレクトリ構成

計算ロジックの変更、検証に必要なディレクトリ構成は、以下の通りです。

```
.
├── src
│   ├── jjjexperiment     # 検証用PF独自のコード。入力パラメータの定義と処理、検証用PF独自の計算ロジックはこちらに追加します。
│   │   ├── carryover_heat     # 【独自ロジック】過剰熱量繰越
│   │   ├── denchu             # 【独自ロジック】電中研モデル
│   │   ├── latent_load        # 【独自ロジック】潜熱評価モデル
│   │   ├── underfloor_ac      # 【独自ロジック】床下空調新ロジック
│   │   ├── v_min_input        # 【独自ロジック】最低風量
│   │   ├── v_supply_cap       # 【独自ロジック】風量上限キャップ
│   │   ├── inputs             # 【共通】入力パラメータの定義、処理
│   │   │   ├── ac_setting.py  # 【共通】空調（暖房、冷房）の入力項目
│   │   │   └── common.py      # 【共通】地域区分、床面積、外皮性能等のその他の入力項目
│   │   ├── main.py            # 【共通】モジュール利用時 最初に呼び出される関数
│   │   └── section4_2.py      # 【共通】改変ロジックのメインとなる 未処理負荷計算
│   └── pyhees            # 元のpyhees由来のコード。軽微なロジック追加・変更の場合、こちらのコードを変更します。
├── README.md             # このファイルです。
├── pyproject.toml        # プロジェクトの設定ファイルです。ライブラリを追加・変更する際に編集します。
└── poetry.lock           # Poetryの依存関係の管理ファイルです。ライブラリを追加・変更した際に `poetry lock` コマンドで更新します。
```

# 機能変更をする際の手順

## 入力パラメータの追加方法

1. 検証用PFのColabファイルに、入力パラメータを追加

2. inputsフォルダ以下に、入力パラメータを入れるクラス（DTO）を作成

    ```python
    @dataclass
    class MaxPowerConsumption:
        max: float  # デフォルト値を指定することもできる
        """電力の最大値"""

        @classmethod
        def from_dict(cls, data: dict) -> 'MaxPowerConsumption':
            # 対応する JSON のキーを指定
            cls(max = data['max_power_consumption'])
    ```

3. jjjexperiment/inputs/di_container.py に、データを登録する

    ```python
    @singleton  # 必須のおまじない
    @provider   # 必須のおまじない
    # 関数名は任意
    def create_max_power_consumption(self) -> MaxPowerConsumption:  # 戻り値の型として上記を指定
        return MaxPowerConsumption.from_dict(self._input if self._input is not None else {})
    ```

4. データを取得する

   トップで呼び出している下記関数の定義に、型指定した引数を追加する必要があります。

    ```python
    # ファイル main.py > calc_main()
    def calc_main(
        ...
        max_power_consumption: MaxPowerConsumption  # 追加
    ) -> dict | None:

    # ファイル section4_2.py > calc_Q_UT_A()
    @jjj_cloning
    @inject
    def calc_Q_UT_A(
        ...
        max_power_consumption: MaxPowerConsumption  # 追加
    ):
    ```

    これ以降の関数では、通常通り引数に渡す 呼び出しコードになります。

## 従来ロジックの軽微な変更

WEBPROのロジックを軽微に変更する場合、`src/pyhees` フォルダ以下のコードを直接編集します。
該当する関数に引数や戻り値を追加する場合、呼び出し元のコードも変更する必要があります。

## 新規ロジックの追加

検証用プラットフォーム独自の計算ロジックを追加する場合、`src/jjjexperiment` フォルダ以下にソースコードファイルを作成します。
これまでに追加したものが[ディレクトリ構成](#ディレクトリ構成)にありますので、参考にしてください。

# 無視して良いコード

* `@jjj_cloning` ... pyheesのコードをコピーした上で、変更をしていることの目印です。この印は、計算に影響はありません。
* `@log_res(...)` ... イズミが検証時にログを出力するためのものです。計算に影響はありません。

