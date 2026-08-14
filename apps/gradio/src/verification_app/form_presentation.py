from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from verification_core import FieldDefinition


@dataclass(frozen=True, slots=True)
class FieldPresentation:
    section: str
    group: str
    label: str
    description: str
    choices: tuple[Any, ...]


SECTION_ORDER = (
    "① 計算条件・外部データ",
    "② 住宅基本情報",
    "③ 外皮性能",
    "④ 床下・空気搬送",
    "⑤ 暖房設備",
    "⑥ 冷房設備",
    "⑦ 熱交換型換気設備",
    "⑧ 詳細設定・比較検証",
)

SECTION_DESCRIPTIONS = {
    "① 計算条件・外部データ": (
        "計算条件名を付け、必要に応じて標準データを置き換える外部ファイルを指定します。"
        "外部ファイルを指定しない場合は、プログラムに同梱した標準データを使用します。"
    ),
    "② 住宅基本情報": (
        "建研Webプログラムの「基本情報」に対応する項目です。"
        "床面積と地域の区分は、設備容量、負荷、気象条件などの算定に使用します。"
    ),
    "③ 外皮性能": (
        "建研Webプログラムの「外皮」に対応する項目です。"
        "外皮面積、熱貫流率、日射熱取得率を入力します。"
    ),
    "④ 床下・空気搬送": (
        "建研Webの床下換気と、Verification Platformで追加した床下空調・風量制御を設定します。"
        "床下換気と床下空調は目的と計算経路が異なるため、説明を確認して選択してください。"
    ),
    "⑤ 暖房設備": (
        "暖房方式を選択すると、その方式で必要な項目だけが表示されます。"
        "青色の項目名は建研Webプログラムの文言を引き継いでいます。"
    ),
    "⑥ 冷房設備": (
        "冷房方式を選択すると、その方式で必要な項目だけが表示されます。"
        "青色の項目名は建研Webプログラムの文言を引き継いでいます。"
    ),
    "⑦ 熱交換型換気設備": (
        "建研Webプログラムの「熱交換型換気設備」に対応する項目です。"
        "設置する場合だけ温度交換効率を入力します。"
    ),
    "⑧ 詳細設定・比較検証": (
        "計算式の比較、研究用の補助定数、機器モデルの詳細条件を変更する上級者向け設定です。"
        "通常の計算では既定値のまま使用してください。"
    ),
}

GROUP_DESCRIPTIONS = {
    "計算条件": "計算結果や出力ファイルを識別するための名称です。",
    "外部データ（任意）": (
        "気象データまたは暖冷房負荷データを差し替える場合だけ指定します。"
        "「-」のままなら標準データを使用します。"
    ),
    "床面積": (
        "建研Webの「床面積」に対応します。主たる居室、その他の居室、合計の関係を確認して入力してください。"
    ),
    "地域": "建設地に対応する省エネルギー基準の地域区分を選択します。",
    "外皮性能": (
        "建研Webで外皮性能を直接入力する場合の項目です。記号と単位は各項目の説明に示します。"
    ),
    "床下換気（建研Web）": (
        "外気を床下経由で導入する建研Webの換気方式です。床下を空調給気経路として使う設定ではありません。"
    ),
    "全館空調の風量制御": (
        "ダクト式セントラル空調機の全体風量を制御します。床下空調の有無にかかわらず影響します。"
    ),
    "床下空調": (
        "床下を一体の給気空間として扱うVerification Platform独自方式です。"
        "Excel床下14に合わせたPass 1・Pass 2と地盤逐時計算を使用します。"
    ),
    "床下空調｜補助定数": (
        "手動設定を有効にした場合だけ使用します。通常は既定値または自動算定値を使用してください。"
    ),
    "建研式との比較・補正": (
        "OFFは建研式との比較用、ONは確認済みの不整合を補正する計算です。"
        "比較結果を追跡できるよう、補正は個別に切り替えられます。"
    ),
    "蓄熱・過剰熱量の持ち越し": (
        "前時刻の過剰熱量を建物の熱容量へ持ち越すVerification Platform独自計算です。"
        "床下空調とは同時に使用できません。"
    ),
    "暖房方式": "暖房の評価方法を選択します。選択した方式の入力欄だけが表示されます。",
    "冷房方式": "冷房の評価方法を選択します。選択した方式の入力欄だけが表示されます。",
    "ダクト・換気方式": (
        "ダクトの断熱区画、VAV方式、全般換気機能の有無を設定します。"
        "暖房と冷房はそれぞれ独立した入力です。"
    ),
    "風量・送風機電力": (
        "設計風量、サーモOFF時などの最低風量、最低送風機電力を設定します。"
        "入力しない場合は計算モデルの既定式で算定します。"
    ),
    "熱交換型換気設備": "設置の有無と、設置する場合の温度交換効率を設定します。",
    "熱源機出口温度の制限": "暖房・冷房時の熱源機出口空気温度に適用する上下限です。",
    "ダクト式セントラル空調機のデフロスト": (
        "低外気温・高湿度時の暖房能力低下を表すダクト式セントラル空調機用の条件です。"
    ),
    "ダクト・送風機の補助定数": "ダクト熱損失と設計風量算定に用いる補助定数です。",
    "ルームエアコンディショナーのデフロスト": (
        "低外気温・高湿度時の暖房能力低下を表すルームエアコンディショナー用の条件です。"
    ),
    "冷房能力・湿度補正": "冷房出力の湿度補正と定格冷房能力の上限を設定します。",
    "計算方法の比較切替": (
        "建研由来式と検討中の代替式を比較するためのスイッチです。結果への影響を確認して使用してください。"
    ),
}


_SECTION_MAP = {
    "①・② 計算条件・外部ファイル": "① 計算条件・外部データ",
    "④ 基本情報": "② 住宅基本情報",
    "⑤ 外皮条件": "③ 外皮性能",
    "⑥ その他": "④ 床下・空気搬送",
    "⑦ 暖房全般": "⑤ 暖房設備",
    "⑧ 冷房全般": "⑥ 冷房設備",
    "⑨ 熱交換型換気設備": "⑦ 熱交換型換気設備",
    "③ 計算時定数等": "⑧ 詳細設定・比較検証",
}

_METHOD_NAMES = {
    "⑦-1": "ダクト式セントラル空調",
    "⑦-2": "RAC活用型（省エネ法モデル）",
    "⑦-3": "RAC活用型（潜熱評価モデル）",
    "⑦-4": "RAC活用型（電中研モデル）",
    "⑧-1": "ダクト式セントラル空調",
    "⑧-2": "RAC活用型（省エネ法モデル）",
    "⑧-3": "RAC活用型（潜熱評価モデル）",
    "⑧-4": "RAC活用型（電中研モデル）",
}

_GROUP_RENAMES = {
    "外部ファイル（任意）": "外部データ（任意）",
    "基本項目": "床面積",
    "床下換気（建研方式）": "床下換気（建研Web）",
    "床下空調（Verification Platform）": "床下空調",
    "手動設定する補助定数": "床下空調｜補助定数",
    "建研本家との比較設定": "建研式との比較・補正",
    "過剰熱量持越し": "蓄熱・過剰熱量の持ち越し",
    "暖房機器の種類": "暖房方式",
    "冷房機器の種類": "冷房方式",
    "設計風量": "風量・送風機電力",
    "最低風量": "風量・送風機電力",
    "最低電力": "風量・送風機電力",
    "ダクト・送風機": "ダクト・送風機の補助定数",
    "計算方法の切替": "計算方法の比較切替",
}

_BRI_LABELS = {
    "A_A__0": "合計",
    "A_MR__0": "主たる居室",
    "A_OR__0": "その他の居室",
    "region__0": "地域の区分",
    "A_env__0": "外皮面積の合計",
    "U_A__0": "外皮平均熱貫流率（U_A）",
    "eta_A_C__0": "冷房期の平均日射熱取得率（η_AC）",
    "eta_A_H__0": "暖房期の平均日射熱取得率（η_AH）",
    "underfloor_ventilation__0": "床下空間を経由して外気を導入する換気方式の利用",
    "r_A_ufvnt__0": "外気が経由する床下の面積の割合",
    "underfloor_insulation__0": "床下空間の断熱",
    "H_A_duct_insulation__0": "ダクトが通過する空間",
    "H_A_VAV__0": "VAV方式",
    "H_A_general_ventilation__0": "全般換気機能",
    "H_A_input_V_hs_dsgn_H__0": "設計風量の入力",
    "H_A_V_hs_dsgn_H__0": "設計風量",
    "C_A_duct_insulation__0": "ダクトが通過する空間",
    "C_A_VAV__0": "VAV方式",
    "C_A_general_ventilation__0": "全般換気機能",
    "C_A_input_V_hs_dsgn_C__0": "設計風量の入力",
    "C_A_V_hs_dsgn_C__0": "設計風量",
    "H_A_input__0": "機器の仕様の入力",
    "C_A_input__0": "機器の仕様の入力",
    "H_A_input_mode__0": "エネルギー消費効率の入力",
    "H_A_mode__0": "エネルギー消費効率の区分",
    "H_A_dualcompressor__0": "小能力時高効率型コンプレッサー",
    "C_A_input_mode__0": "エネルギー消費効率の入力",
    "C_A_mode__0": "エネルギー消費効率の区分",
    "C_A_dualcompressor__0": "小能力時高効率型コンプレッサー",
    "HEX_install__0": "熱交換型換気設備",
    "etr_t__0": "温度交換効率",
}

_PLATFORM_LABELS = {
    "case_name__0": "計算条件名",
    "climateFile__0": "気象データ（任意）",
    "loadFile__0": "暖冷房負荷データ（任意）",
    "change_supply_volume_before_vav_adjust__0": "VAV調整前の風量配分を時刻別負荷比へ変更する",
    "change_heat_source_outlet_required_temperature__0": "熱源機出口温度を区画別要求温度から決定する",
    "change_V_supply_d_t_i_max__0": "区画別吹き出し風量の上限方式",
    "hs_CAV__0": "熱源機の全体風量を設計風量に固定する",
    "change_underfloor_temperature__0": "床下空調を使用する",
    "input_ufac_consts__0": "床下空調の補助定数を手動設定する",
    "R_g__0": "地盤表面熱伝達抵抗 R_g",
    "phi__0": "基礎側面の線熱貫流率 φ",
    "correct_cooling_partition_heat_transfer__0": "冷房時の間仕切壁熱移動を物理的な符号へ補正する",
    "correct_no_general_ventilation_airflow__0": "全般換気なし時の給気風量下限を補正する",
    "carry_over_heat__0": "過剰熱量の持ち越し計算を行う",
    "H_A_input_V_hs_min__0": "最低風量の入力",
    "H_A_V_hs_min__0": "最低風量",
    "H_A_input_E_E_fan_min__0": "最低送風機電力の入力",
    "H_A_E_E_fan_logic__0": "最低送風機電力の計算方法",
    "H_A_E_E_fan_min__0": "最低送風機電力",
    "C_A_input_V_hs_min__0": "最低風量の入力",
    "C_A_V_hs_min__0": "最低風量",
    "C_A_input_E_E_fan_min__0": "最低送風機電力の入力",
    "C_A_E_E_fan_logic__0": "最低送風機電力の計算方法",
    "C_A_E_E_fan_min__0": "最低送風機電力",
    "H_A_type__0": "暖房方式",
    "C_A_type__0": "冷房方式",
}

_DESCRIPTIONS = {
    "case_name__0": "出力ファイル名と計算結果の識別に使用します。計算式には影響しません。",
    "climateFile__0": "「-」の場合は地域区分に対応する標準気象データを使用します。",
    "loadFile__0": "「-」の場合は同梱した標準暖冷房負荷を使用します。",
    "A_A__0": "住戸の床面積の合計です。単位は m² です。",
    "A_MR__0": "主たる居室の床面積です。単位は m² です。",
    "A_OR__0": "その他の居室の床面積です。単位は m² です。",
    "region__0": "建設地に対応する1～7地域を選択します。",
    "A_env__0": "当該住戸の外皮面積の合計です。単位は m² です。",
    "U_A__0": "外皮平均熱貫流率です。単位は W/(m²・K) です。",
    "eta_A_C__0": "冷房期の平均日射熱取得率です。単位は % です。",
    "eta_A_H__0": "暖房期の平均日射熱取得率です。単位は % です。",
    "H_A_input_V_hs_dsgn_H__0": "入力しない場合は建研式で暖房時の設計風量を算定します。",
    "H_A_V_hs_dsgn_H__0": "暖房時の設計風量です。単位は m³/h です。",
    "C_A_input_V_hs_dsgn_C__0": "入力しない場合は建研式で冷房時の設計風量を算定します。",
    "C_A_V_hs_dsgn_C__0": "冷房時の設計風量です。単位は m³/h です。",
    "H_A_input__0": "入力しない場合は建研Webと同じ既定の機器特性を使用します。",
    "C_A_input__0": "入力しない場合は建研Webと同じ既定の機器特性を使用します。",
    "H_A_input_mode__0": "入力しない場合は暖房の既定区分で評価します。",
    "C_A_input_mode__0": "入力しない場合は冷房の既定区分で評価します。",
    "H_A_dualcompressor__0": "暖房能力の直接入力とは独立した設定です。",
    "C_A_dualcompressor__0": "冷房能力の直接入力とは独立した設定です。",
    "HEX_install__0": "設置する場合だけ温度交換効率の入力欄が表示されます。",
    "etr_t__0": "熱交換型換気設備の温度交換効率です。単位は % です。",
}

_THERMAL_CAPACITY_LABELS = {
    "c1_BR_R_1__0": "主たる居室（区画1）の熱容量",
    "c1_BR_R_2__0": "その他の居室（区画2）の熱容量",
    "c1_BR_R_3__0": "その他の居室（区画3）の熱容量",
    "c1_BR_R_4__0": "その他の居室（区画4）の熱容量",
    "c1_BR_R_5__0": "その他の居室（区画5）の熱容量",
    "c1_NR_R__0": "非居室の熱容量",
}


def present_field(field: FieldDefinition) -> FieldPresentation:
    section = _section_name(field.section)
    group = _group_name(field)
    label = _field_label(field)
    description = _field_description(field)
    return FieldPresentation(
        section=section,
        group=group,
        label=label,
        description=description,
        choices=_field_choices(field),
    )


def _section_name(source_section: str) -> str:
    for prefix in _METHOD_NAMES:
        if source_section.startswith(prefix):
            return "⑤ 暖房設備" if prefix.startswith("⑦") else "⑥ 冷房設備"
    try:
        return _SECTION_MAP[source_section]
    except KeyError as error:
        raise ValueError(f"Unknown input section: {source_section}") from error


def _group_name(field: FieldDefinition) -> str:
    for prefix, method_name in _METHOD_NAMES.items():
        if field.section.startswith(prefix):
            return f"{method_name}｜{field.group}"
    if field.section == "④ 基本情報":
        return "地域" if field.key == "region__0" else "床面積"
    if field.section == "⑤ 外皮条件":
        return "外皮性能"
    if field.section == "⑨ 熱交換型換気設備":
        return "熱交換型換気設備"
    return _GROUP_RENAMES.get(field.group, field.group)


def _field_label(field: FieldDefinition) -> str:
    if field.key in _BRI_LABELS:
        return _BRI_LABELS[field.key]
    if field.key in _PLATFORM_LABELS:
        return _PLATFORM_LABELS[field.key]
    if field.key in _THERMAL_CAPACITY_LABELS:
        return _THERMAL_CAPACITY_LABELS[field.key]
    test_value_label = _test_value_label(field.key)
    if test_value_label is not None:
        return test_value_label
    coefficient = _coefficient_label(field)
    if coefficient is not None:
        return coefficient
    return _clean_label(field.label)


def _test_value_label(field_key: str) -> str | None:
    if not any(
        token in field_key
        for token in ("_hs_rtd_", "_hs_mid_", "_fan_rtd_", "_fan_mid_")
    ):
        return None
    if "_q_hs_" in field_key:
        return "能力"
    if "_P_hs_" in field_key:
        return "消費電力"
    if "_V_fan_" in field_key:
        return "風量"
    if "_P_fan_" in field_key:
        return "室内側送風機の消費電力"
    return None


def _clean_label(label: str) -> str:
    label = re.sub(r"（[^）]* or [^）]*）", "", label)
    label = label.replace("（入力する場合のみ）", "")
    return label.strip()


def _field_description(field: FieldDefinition) -> str:
    description = _DESCRIPTIONS.get(field.key, field.description)
    if description:
        return description
    if "[m3/h]" in field.label:
        return "単位は m³/h です。"
    if "[W/(m2・K)]" in field.label:
        return "単位は W/(m²・K) です。"
    if "[W]" in field.label:
        return "単位は W です。"
    if "[m2]" in field.label:
        return "単位は m² です。"
    return ""


def _field_choices(field: FieldDefinition) -> tuple[Any, ...]:
    return field.choices


def _coefficient_label(field: FieldDefinition) -> str | None:
    if not field.key.startswith(("a4__", "a3__", "a2__", "a1__", "a0__")):
        return None
    degree = field.key[1]
    return f"{degree}次係数 a{degree}"


def group_description(group_name: str) -> str:
    if group_name in GROUP_DESCRIPTIONS:
        return GROUP_DESCRIPTIONS[group_name]
    if "｜" not in group_name:
        return ""
    method, detail = group_name.split("｜", 1)
    detail_descriptions = {
        "設置方法の入力": (
            "熱源機と送風機の組み合わせ方を設定します。補正係数を直接入力する場合だけ係数欄が表示されます。"
        ),
        "機器仕様の入力": (
            "機器仕様を入力する範囲を選択します。選択後、必要な試験値だけが表示されます。"
        ),
        "定格暖房能力試験": "定格暖房能力試験の能力、消費電力、風量、送風機電力を入力します。",
        "中間暖房能力試験": "中間暖房能力試験の能力、消費電力、風量、送風機電力を入力します。",
        "定格冷房能力試験": "定格冷房能力試験の能力、消費電力、風量、送風機電力を入力します。",
        "中間冷房能力試験": "中間冷房能力試験の能力、消費電力、風量、送風機電力を入力します。",
        "エネルギー消費効率の入力": "エネルギー消費効率を直接指定するか選択します。暖房・冷房で個別に設定します。",
        "暖房能力の入力": "暖房能力を床面積から算定するか、機器値を直接入力するか選択します。",
        "冷房能力の入力": "冷房能力を床面積から算定するか、機器値を直接入力するか選択します。",
        "小能力時高効率型コンプレッサー": "能力の入力方法とは独立して、コンプレッサーの特性を設定します。",
        "ファンの消費電力": "送風機の比消費電力を自動算定するか、直接入力するか選択します。",
        "コイル特性": "熱交換器の小容量・大容量時の表面積を設定します。",
        "コンプレッサ効率特性": "コンプレッサー効率を表す多項式係数です。式はこのグループ全体で共通です。",
        "熱伝達特性": "熱伝達特性を表す多項式係数です。式はこのグループ全体で共通です。",
        "風量特性": "最小・最大風量と、風量特性を表す多項式係数を設定します。",
        "ファン消費電力": "送風機消費電力を表す多項式係数です。式はこのグループ全体で共通です。",
    }
    detail_description = detail_descriptions.get(detail, "")
    if detail_description:
        return f"{method}の設定です。{detail_description}"
    return f"{method}の「{detail}」に関する入力です。"
