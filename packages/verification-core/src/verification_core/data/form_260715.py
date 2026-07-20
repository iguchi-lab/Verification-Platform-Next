#@title (1) UIを使って入力する場合

import jjjexperiment.main

input_data = {}

#@markdown # <font color="orange">**＜① 計算条件名＞**</font>
#@markdown #### <font color="lightgreen">**計算条件名**</font>
case_name = 'default' #@param {type:"string"}
input_data['case_name'] = case_name

#@markdown ---
#@markdown # <font color="orange">**＜② 外部ファイル名の入力（ある場合のみ）＞**</font>
#@markdown #### <font color="lightgreen">**気象データファイル名**</font>
climateFile = '-' #@param {type:"string"}
input_data['climateFile'] = climateFile
#@markdown #### <font color="lightgreen">**暖冷房負荷データファイル名**</font>
loadFile = '-' #@param {type:"string"}
input_data['loadFile'] = loadFile

#@markdown ---
#@markdown # <font color="orange">**＜③ 計算時定数等＞**</font>
#@markdown #### <font color="lightgreen">**最大暖房出力時の熱源機の出口における空気温度の最大値の上限値**</font>
Theta_hs_out_max_H_d_t_limit = 45.0       #@param {type:"number"}
input_data['Theta_hs_out_max_H_d_t_limit'] = Theta_hs_out_max_H_d_t_limit
#@markdown #### <font color="lightgreen">**最大冷房出力時の熱源機の出口における空気温度の最低値の下限値**</font>
Theta_hs_out_min_C_d_t_limit = 15.0       #@param {type:"number"}
input_data['Theta_hs_out_min_C_d_t_limit'] = Theta_hs_out_min_C_d_t_limit
#@markdown #### <font color="lightgreen">**デフロストに関する暖房出力補正係数（ダクトセントラル空調機）**</font>
C_df_H_d_t_defrost_ductcentral = 0.77     #@param {type:"number"}
input_data['C_df_H_d_t_defrost_ductcentral'] = C_df_H_d_t_defrost_ductcentral
#@markdown #### <font color="lightgreen">**デフロスト発生外気温度（ダクトセントラル空調機）**</font>
defrost_temp_ductcentral = 5.0            #@param {type:"number"}
input_data['defrost_temp_ductcentral'] = defrost_temp_ductcentral
#@markdown #### <font color="lightgreen">**デフロスト発生外気相対湿度（ダクトセントラル空調機）**</font>
defrost_humid_ductcentral = 80.0          #@param {type:"number"}
input_data['defrost_humid_ductcentral'] = defrost_humid_ductcentral
#@markdown #### <font color="lightgreen">**ダクトiの線熱損失係数**</font>
phi_i = 0.49                              #@param {type:"number"}
input_data['phi_i'] = phi_i
#@markdown #### <font color="lightgreen">**暖房時の送風機の設計風量に関する係数**</font>
C_V_fan_dsgn_H = 0.79                     #@param {type:"number"}
input_data['C_V_fan_dsgn_H'] = C_V_fan_dsgn_H
#@markdown #### <font color="lightgreen">**冷房時の送風機の設計風量に関する係数**</font>
C_V_fan_dsgn_C = 0.79                     #@param {type:"number"}
input_data['C_V_fan_dsgn_C'] = C_V_fan_dsgn_C
#@markdown #### <font color="lightgreen">**デフロストに関する暖房出力補正係数（ルームエアコンディショナー）**</font>
C_df_H_d_t_defrost_rac = 0.77             #@param {type:"number"}
input_data['C_df_H_d_t_defrost_rac'] = C_df_H_d_t_defrost_rac
#@markdown #### <font color="lightgreen">**デフロスト発生外気温度（ルームエアコンディショナー）**</font>
defrost_temp_rac = 5.0                    #@param {type:"number"}
input_data['defrost_temp_rac'] = defrost_temp_rac
#@markdown #### <font color="lightgreen">**デフロスト発生外気相対湿度（ルームエアコンディショナー）**</font>
defrost_humid_rac = 80.0                  #@param {type:"number"}
input_data['defrost_humid_rac'] = defrost_humid_rac
#@markdown ####<font color="lightgreen">**室内機吸い込み湿度に関する冷房出力補正係数**</font>
C_hm_C = 1.15                             #@param {type:"number"}
input_data['C_hm_C'] = C_hm_C
#@markdown #### <font color="lightgreen">**定格冷房能力の最大値(固定:5600)**</font>
q_rtd_C_limit = 5600                      #@param [5600] {allow-input: false}
input_data['q_rtd_C_limit'] = q_rtd_C_limit
#@markdown #### <font color="lightgreen">**VAV調整前の吹き出し風量の式を変更**</font>
change_supply_volume_before_vav_adjust = False  #@param {type:"boolean"}
input_data['change_supply_volume_before_vav_adjust'] = '2' if change_supply_volume_before_vav_adjust else '1'
#@markdown #### <font color="lightgreen">**熱源機の出口における空気温度**</font>
change_heat_source_outlet_required_temperature = False  #@param {type:"boolean"}
input_data['change_heat_source_outlet_required_temperature'] = '2' if change_heat_source_outlet_required_temperature else '1'
#@markdown #### <font color="lightgreen">**V_supply_d_t_iの上限キャップを外す**</font>
change_V_supply_d_t_i_max = "従来上限を維持"  #@param ["従来上限を維持", "設計風量を上限(各室均一)", "設計風量を上限(風量増の部屋のみ)"] {type:"string"}
if change_V_supply_d_t_i_max == '従来上限を維持':
    input_data['change_V_supply_d_t_i_max'] = 1
elif change_V_supply_d_t_i_max == '設計風量を上限(各室均一)':
    input_data['change_V_supply_d_t_i_max'] = 2
elif change_V_supply_d_t_i_max == '設計風量を上限(風量増の部屋のみ)':
    input_data['change_V_supply_d_t_i_max'] = 3

#@markdown ---
#@markdown # <font color="orange">**＜④ 基本情報＞**</font>
#@markdown #### <font color="lightgreen">**面積の合計 [m2]**</font>
A_A = 120.08  #@param {type:"number"}
input_data['A_A'] = A_A
#@markdown #### <font color="lightgreen">**主たる居室の面積 [m2]**</font>
A_MR = 29.81  #@param {type:"number"}
input_data['A_MR'] = A_MR
#@markdown #### <font color="lightgreen">**その他の居室の面積 [m2]**</font>
A_OR = 51.34  #@param {type:"number"}
input_data['A_OR'] = A_OR
#@markdown #### <font color="lightgreen">**地域区分**</font>
region = 6    #@param [1, 2, 3, 4, 5, 6, 7] {type:"raw"}
input_data['region'] = region

#@markdown ---
#@markdown # <font color="orange">**＜⑤ 外皮条件＞**</font>
#@markdown #### <font color="lightgreen">**外皮面積 [m2]**</font>
A_env = 307.51    #@param {type:"number"}
input_data['A_env'] = A_env
#@markdown #### <font color="lightgreen">**外皮平均熱貫流率 UA [W/(m2・K)]**</font>
U_A = 0.87        #@param {type:"number"}
input_data['U_A'] = U_A
#@markdown #### <font color="lightgreen">**冷房期平均日射熱取得率ηAC**</font>
eta_A_C = 2.8     #@param {type:"number"}
input_data['eta_A_C'] = eta_A_C
#@markdown #### <font color="lightgreen">**暖房期平均日射熱取得率ηAH**</font>
eta_A_H = 4.3     #@param {type:"number"}
input_data['eta_A_H'] = eta_A_H

#@markdown ---
#@markdown # <font color="orange">**＜⑥ その他＞**</font>
#@markdown #### <font color="lightgreen">**床下空間を経由して外気を導入する換気方式の利用（☐：評価しない or ☑：評価する）**</font>
underfloor_ventilation = False                    #@param {type:"boolean"}
input_data['underfloor_ventilation'] = '2' if underfloor_ventilation else '1'
#@markdown #### <font color="lightgreen">**外気が経由する床下の面積の割合 [%]**</font>
r_A_ufvnt = 100.0                                 #@param {type:"number"}
input_data['r_A_ufvnt'] = r_A_ufvnt
#@markdown #### <font color="lightgreen">**床下空間の断熱（☐：断熱区画外 or ☑：断熱区画内）**</font>
underfloor_insulation = False                     #@param {type:"boolean"}
input_data['underfloor_insulation'] = '2' if underfloor_insulation else '1'
#@markdown #### <font color="lightgreen">**全体風量を固定する （☐：固定しない or ☑：固定する）**</font>
hs_CAV = False                                    #@param {type:"boolean"}
input_data['hs_CAV'] = '2' if hs_CAV else '1'

#@markdown #### <font color="lightgreen">**空調空気を床下を通して給気する （☐：床下を通して給気しない or ☑：床下を通して給気する）**</font>
underfloor_air_conditioning_air_supply = False    #@param {type:"boolean"}
input_data['underfloor_air_conditioning_air_supply'] = '2' if underfloor_air_conditioning_air_supply else '1'
#@markdown #### <font color="lightgreen">**床下空調のロジックを変更する**</font>
change_underfloor_temperature = False    #@param {type:"boolean"}
input_data['change_underfloor_temperature'] = '2' if change_underfloor_temperature else '1'

#@markdown #### <font color="lightgreen">**地盤またはそれを覆う基礎の表面熱伝達抵抗 [(m2・K)/W]**</font>
R_g = 0.15    #@param {type:"number"}
input_data['R_g'] = R_g

#@markdown #### <font color="lightgreen">**床下空調に関する定数を上書きする**</font>
input_ufac_consts = False    #@param {type:"boolean"}
input_data['input_ufac_consts'] = 2 if input_ufac_consts else 1
#@markdown #### <font color="lightgreen">**地盤内の不易層の温度 [℃]**</font>
Theta_g_avg = 15.7    #@param {type:"number"}
input_data['Theta_g_avg'] = Theta_g_avg
#@markdown #### <font color="lightgreen">**床板(床チャンバー上面)の熱貫流率 [W/(m2・K)]**</font>
U_s_vert = 2.223    #@param {type:"number"}
input_data['U_s_vert'] = U_s_vert
#@markdown #### <font color="lightgreen">**基礎(床チャンバー側面)の線熱貫流率 [W/(m・K)]**</font>
phi = 0.846    #@param {type:"number"}
input_data['phi'] = phi

#@markdown ---
#@markdown ## <font color="orange">**＜⑥-1. 過剰熱量持越し＞**</font>
#@markdown #### <font color="lightgreen">**過剰熱量の持ち越し計算を行う**</font>
carry_over_heat = False    #@param {type:"boolean"}
input_data['carry_over_heat'] = 2 if carry_over_heat else 1

#@markdown #### <font color="lightgreen">**SimHeatモデル熱容量(空間・什器のみ)の変更 [J/K]**</font>
c1_BR_R_1 = 893676  #@param {type:"number"}
c1_BR_R_2 = 500835  #@param {type:"number"}
c1_BR_R_3 = 400667  #@param {type:"number"}
c1_BR_R_4 = 325488  #@param {type:"number"}
c1_BR_R_5 = 325598  #@param {type:"number"}
c1_NR_R = 1195534  #@param {type:"number"}
input_data['C1_BR_R_i'] = [c1_BR_R_1, c1_BR_R_2, c1_BR_R_3, c1_BR_R_4, c1_BR_R_5]
input_data['C1_NR_R'] = c1_NR_R

""" 暖房 共通入力項目 """

#@markdown ---
#@markdown # <font color="orange">**＜⑦ 暖房全般＞**</font>
#@markdown #### <font color="lightgreen">**暖房設備の種類 (1.ﾀﾞｸﾄ式ｾﾝﾄﾗﾙ空調機, 2.ﾙｰﾑｴｱｺﾝﾃﾞｨｼｮﾅ活用型全館空調(現行省ｴﾈ法ﾙｰﾑｴｱｺﾝﾓﾃﾞﾙ), 3.ﾙｰﾑｴｱｺﾝﾃﾞｨｼｮﾅ活用型全館空調(潜熱評価ﾓﾃﾞﾙ), 4.電中研ﾓﾃﾞﾙ)**</font>
input_data['H_A']  = {}
H_A_type = "\u30C0\u30AF\u30C8\u5F0F\u30BB\u30F3\u30C8\u30E9\u30EB\u7A7A\u8ABF\u6A5F" #@param ["ダクト式セントラル空調機", "ルームエアコンディショナ活用型全館空調（現行省エネ法ルームエアコンモデル）", "ルームエアコンディショナ活用型全館空調（潜熱評価モデル）", "電中研モデル"] {type:"string"}
if H_A_type == 'ダクト式セントラル空調機':
    input_data['H_A']['type'] = 1
elif 'ルームエアコン' in H_A_type and '現行省エネ' in H_A_type:
    input_data['H_A']['type'] = 2
elif 'ルームエアコン' in H_A_type and '潜熱評価モデル' in H_A_type:
    input_data['H_A']['type'] = 3
elif '電中研モデル' in H_A_type:
    input_data['H_A']['type'] = 4
else:
    raise Exception('未定義の方式が選択されました')

#@markdown #### <font color="lightgreen">**ダクトが通過する空間　（全てもしくは一部が断熱区画外である or 全て断熱区画内である）**</font>
H_A_duct_insulation = "\u5168\u3066\u3082\u3057\u304F\u306F\u4E00\u90E8\u304C\u65AD\u71B1\u533A\u753B\u5916\u3067\u3042\u308B"    #@param ["全てもしくは一部が断熱区画外である", "全て断熱区画内である"] {type:"string"}
if H_A_duct_insulation == "全てもしくは一部が断熱区画外である":
    input_data['H_A']['duct_insulation'] = 1
else:
    input_data['H_A']['duct_insulation'] = 2
#@markdown #### <font color="lightgreen">**VAV方式　（採用しない or 採用する）**</font>
H_A_VAV = "採用しない" #@param ["採用しない", "採用する"] {type:"string"}
if H_A_VAV == "採用しない":
    input_data['H_A']['VAV'] = 1
else:
    input_data['H_A']['VAV'] = 2
#@markdown #### <font color="lightgreen">**全般換気機能　（あり or なし）**</font>
H_A_general_ventilation = "\u3042\u308A" #@param ["あり", "なし"] {type:"string"}
if H_A_general_ventilation == "あり":
    input_data['H_A']['general_ventilation'] = 1
else:
    input_data['H_A']['general_ventilation'] = 2

#@markdown #### <font color="orange">**―設計風量―**</font>
#@markdown #### <font color="lightgreen">**設計風量（入力しない or 入力する）**</font>
H_A_input_V_hs_dsgn_H = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['H_A']['input_V_hs_dsgn'] = 1 if H_A_input_V_hs_dsgn_H == "入力しない" else 2
#@markdown #### <font color="lightblue">**設計風量 [m3/h]（入力する場合のみ）**</font>
H_A_V_hs_dsgn_H = 1500    #@param {type:"number"}
input_data['H_A']['V_hs_dsgn'] = H_A_V_hs_dsgn_H

#@markdown #### <font color="orange">**―最低風量―**</font>
#@markdown [ユーザーマニュアル 最低風量・最低電力 を開く](https://iguchi-lab.github.io/pyhees-jjj/%E6%9C%80%E4%BD%8E%E9%A2%A8%E9%87%8F_%E6%9C%80%E4%BD%8E%E9%9B%BB%E5%8A%9B_%E7%9B%B4%E6%8E%A5%E5%85%A5%E5%8A%9B.html)
#@markdown #### <font color="lightgreen">**ファン消費電力から換気分を引くか（換気分を引く or 換気分を引かない）**</font>
H_A_subtract_ventilation_power = "換気分を引く" #@param ["換気分を引く", "換気分を引かない"] {type:"string"}
input_data['H_A']['subtract_ventilation_power'] = 1 if H_A_subtract_ventilation_power == "換気分を引く" else 2
#@markdown > ※ 上記の消費電力計算修正は最低風量入力がないときのみ有効です。
#@markdown #### <font color="lightgreen">**最低風量（入力しない or 入力する）**</font>
H_A_input_V_hs_min = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['H_A']['input_V_hs_min'] = 1 if H_A_input_V_hs_min == "入力しない" else 2
#@markdown #### <font color="lightblue">**最低風量 [m3/h]（入力する場合のみ）**</font>
H_A_V_hs_min = 1200    #@param {type:"number"}
input_data['H_A']['V_hs_min'] = H_A_V_hs_min

#@markdown #### <font color="orange">**―最低電力―**</font>
#@markdown #### <font color="lightgreen">**最低電力（入力しない or 入力する）**</font>
H_A_input_E_E_fan_min = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['H_A']['input_E_E_fan_min'] = 1 if H_A_input_E_E_fan_min == "入力しない" else 2
#@markdown #### <font color="lightgreen">**ファン消費電力算定方法**</font>
H_A_E_E_fan_logic = "直線近似法" #@param ["直線近似法", "風量三乗近似法"] {type:"string"}
input_data['H_A']['E_E_fan_logic'] = 1 if H_A_E_E_fan_logic == "直線近似法" else 2
#@markdown #### <font color="lightblue">**最低電力 [W]（入力する場合のみ）**</font>
H_A_E_E_fan_min = 100    #@param {type:"number"}
input_data['H_A']['E_E_fan_min'] = H_A_E_E_fan_min

# デフォルト入力として「入力しない」を設定し、あとで必要なら上書きする
input_data['H_A']['input'] = 1
input_data['H_A']['input_f_SFP'] = 1
input_data['H_A']['input_C_af_H2'] = 1
input_data['H_A']['dedicated_chamber2'] = 1
input_data['H_A']['fixed_fin_direction2'] = 1
input_data['H_A']['input_C_af_H3'] = 1
input_data['H_A']['dedicated_chamber3'] = 1
input_data['H_A']['fixed_fin_direction3'] = 1
input_data['H_A']['input_C_af_H4'] = 1
input_data['H_A']['dedicated_chamber4'] = 1
input_data['H_A']['fixed_fin_direction4'] = 1


""" 暖房 方式別入力項目 """

if input_data['H_A']['type'] == 1:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑦-1 暖房 ダクト式セントラル空調機＞**</font>

    #@markdown #### <font color="orange">**―機器仕様の入力―**</font>
    #@markdown #### <font color="lightgreen">**機器仕様の入力（入力しない or 定格能力試験の値を入力する or 定格能力試験と中間能力試験の値を入力する）**</font>
    H_A_input = "入力しない" #@param ["入力しない", "定格能力試験の値を入力する", "定格能力試験と中間能力試験の値を入力する"] {type:"string"}
    if H_A_input == "入力しない":
        input_data['H_A']['input'] = 1
    elif H_A_input == "定格能力試験の値を入力する":
        input_data['H_A']['input'] = 2
    else:
        input_data['H_A']['input'] = 3

    #@markdown #### <font color="orange">**―定格暖房能力試験―**</font>
    #@markdown #### <font color="lightblue">**定格暖房能力 [W]（入力する場合のみ）**</font>
    H_A_q_hs_rtd_H1 = 0.0    #@param {type:"number"}
    input_data['H_A']['q_hs_rtd'] = H_A_q_hs_rtd_H1
    #@markdown #### <font color="lightblue">**定格暖房消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_hs_rtd_H1 = 0.0    #@param {type:"number"}
    input_data['H_A']['P_hs_rtd'] = H_A_P_hs_rtd_H1
    #@markdown #### <font color="lightblue">**定格運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    H_A_V_fan_rtd_H1 = 0.0   #@param {type:"number"}
    input_data['H_A']['V_fan_rtd'] = H_A_V_fan_rtd_H1
    #@markdown #### <font color="lightblue">**定格運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_fan_rtd_H1 = 0.0   #@param {type:"number"}
    input_data['H_A']['P_fan_rtd'] = H_A_P_fan_rtd_H1

    #@markdown #### <font color="orange">**―中間暖房能力試験―**</font>
    #@markdown #### <font color="lightblue">**中間暖房能力 [W]（入力する場合のみ）**</font>
    H_A_q_hs_mid_H1 = 0.0    #@param {type:"number"}
    input_data['H_A']['q_hs_mid'] = H_A_q_hs_mid_H1
    #@markdown #### <font color="lightblue">**中間暖房消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_hs_mid_H1 = 0.0    #@param {type:"number"}
    input_data['H_A']['P_hs_mid'] = H_A_P_hs_mid_H1
    #@markdown #### <font color="lightblue">**中間運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    H_A_V_fan_mid_H1 = 0.0   #@param {type:"number"}
    input_data['H_A']['V_fan_mid'] = H_A_V_fan_mid_H1
    #@markdown #### <font color="lightblue">**中間運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_fan_mid_H1 = 0.0   #@param {type:"number"}
    input_data['H_A']['P_fan_mid'] = H_A_P_fan_mid_H1

elif input_data['H_A']['type'] == 2:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑦-2 暖房 ルームエアコンディショナ活用型全館空調（現行省エネ法ルームエアコンモデル）＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    H_A_input_C_af_H2 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if H_A_input_C_af_H2 == "設置方法を入力する":
        input_data['H_A']['input_C_af_H2'] = 1
    else:
        input_data['H_A']['input_C_af_H2'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    H_A_dedicated_chamber2 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_dedicated_chamber2 == "該当しない":
        input_data['H_A']['dedicated_chamber2'] = 1
    else:
        input_data['H_A']['dedicated_chamber2'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    H_A_fixed_fin_direction2 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_fixed_fin_direction2 == "該当しない":
        input_data['H_A']['fixed_fin_direction2'] = 1
    else:
        input_data['H_A']['fixed_fin_direction2'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する暖房出力補正係数の入力（入力する場合のみ）**</font>
    H_A_C_af_H2 = 0   #@param {type:"number"}
    input_data['H_A']['C_af_H2'] = H_A_C_af_H2

    #@markdown #### <font color="orange">**―暖房能力の入力―**</font>
    #@markdown #### <font color="lightgreen">**暖房能力の入力（面積から能力を算出 or 性能を直接入力）**</font>
    H_A_input_rac_performance = "\u9762\u7A4D\u304B\u3089\u80FD\u529B\u3092\u7B97\u51FA" #@param ["面積から能力を算出", "性能を直接入力"] {type:"string"}
    if H_A_input_rac_performance == "面積から能力を算出":
        input_data['H_A']['input_rac_performance'] = 1
    else:
        input_data['H_A']['input_rac_performance'] = 2
    #@markdown #### <font color="lightblue">**暖房定格能力 [W]（入力する場合のみ）**</font>
    H_A_q_rac_rtd_H = 2.2   #@param {type:"number"}
    input_data['H_A']['q_rac_rtd_H'] = H_A_q_rac_rtd_H
    #@markdown #### <font color="lightblue">**暖房最大能力 [W]（入力する場合のみ）**</font>
    H_A_q_rac_max_H = 3.3   #@param {type:"number"}
    input_data['H_A']['q_rac_max_H'] = H_A_q_rac_max_H
    #@markdown #### <font color="lightblue">**定格エネルギー効率 [-]（入力する場合のみ）**</font>
    e_rac_rtd_H = 0   #@param {type:"number"}
    input_data['H_A']['e_rac_rtd_H'] = e_rac_rtd_H
    #@markdown #### <font color="lightgreen">**小能力時高効率型コンプレッサー（評価しない or 搭載する）**</font>
    H_A_dualcompressor = "評価しない" #@param ["評価しない", "搭載する"] {type:"string"}
    if H_A_dualcompressor == "評価しない":
        input_data['H_A']['dualcompressor'] = 1
    else:
        input_data['H_A']['dualcompressor'] = 2

    #@markdown #### <font color="orange">**―ファンの消費電力―**</font>
    #@markdown #### <font color="lightgreen">**ファンの比消費電力（入力しない or 入力する）**</font>
    H_A_input_f_SFP_H = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
    input_data['H_A']['input_f_SFP'] = 1 if H_A_input_f_SFP_H == "入力しない" else 2
    #@markdown #### <font color="lightblue">**ファンの比消費電力W [W / (m3/h)]（入力する場合のみ）**</font>
    f_SFP_H = 0.144    #@param {type:"number"}
    input_data['H_A']['f_SFP'] = f_SFP_H

elif input_data['H_A']['type'] == 3:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑦-3 暖房 ルームエアコンディショナ活用型全館空調（潜熱評価モデル）＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    H_A_input_C_af_H3 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if H_A_input_C_af_H3 == "設置方法を入力する":
        input_data['H_A']['input_C_af_H3'] = 1
    else:
        input_data['H_A']['input_C_af_H3'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    H_A_dedicated_chamber3 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_dedicated_chamber3 == "該当しない":
        input_data['H_A']['dedicated_chamber3'] = 1
    else:
        input_data['H_A']['dedicated_chamber3'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    H_A_fixed_fin_direction3 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_fixed_fin_direction3 == "該当しない":
        input_data['H_A']['fixed_fin_direction3'] = 1
    else:
        input_data['H_A']['fixed_fin_direction3'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する暖房出力補正係数の入力（入力する場合のみ）**</font>
    H_A_C_af_H3 = 0   #@param {type:"number"}
    input_data['H_A']['C_af_H3'] = H_A_C_af_H3

    #@markdown #### <font color="orange">**―機器仕様の入力―**</font>
    #@markdown #### <font color="lightgreen">**機器仕様の入力（入力しない or 定格能力試験の値を入力する or 定格能力試験と中間能力試験の値を入力する）**</font>
    H_A_input = "入力しない" #@param ["入力しない", "定格能力試験の値を入力する", "定格能力試験と中間能力試験の値を入力する"] {type:"string"}
    if H_A_input == "入力しない":
        input_data['H_A']['input'] = 1
    elif H_A_input == "定格能力試験の値を入力する":
        input_data['H_A']['input'] = 2
    else:
        input_data['H_A']['input'] = 3

    #@markdown #### <font color="orange">**―定格暖房能力試験―**</font>
    #@markdown #### <font color="lightblue">**定格暖房能力 [W]（入力する場合のみ）**</font>
    H_A_q_hs_rtd_H3 = 0.0    #@param {type:"number"}
    input_data['H_A']['q_hs_rtd'] = H_A_q_hs_rtd_H3
    #@markdown #### <font color="lightblue">**定格消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_hs_rtd_H3 = 0.0    #@param {type:"number"}
    input_data['H_A']['P_hs_rtd'] = H_A_P_hs_rtd_H3
    #@markdown #### <font color="lightblue">**定格運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    H_A_V_fan_rtd_H3 = 0.0   #@param {type:"number"}
    input_data['H_A']['V_fan_rtd'] = H_A_V_fan_rtd_H3
    #@markdown #### <font color="lightblue">**定格運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_fan_rtd_H3 = 0.0   #@param {type:"number"}
    input_data['H_A']['P_fan_rtd'] = H_A_P_fan_rtd_H3

    #@markdown #### <font color="orange">**―中間暖房能力試験―**</font>
    #@markdown #### <font color="lightblue">**中間暖房能力 [W]（入力する場合のみ）**</font>
    H_A_q_hs_mid_H3 = 0.0    #@param {type:"number"}
    input_data['H_A']['q_hs_mid'] = H_A_q_hs_mid_H3
    #@markdown #### <font color="lightblue">**中間暖房消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_hs_mid_H3 = 0.0    #@param {type:"number"}
    input_data['H_A']['P_hs_mid'] = H_A_P_hs_mid_H3
    #@markdown #### <font color="lightblue">**中間運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    H_A_V_fan_mid_H3 = 0.0   #@param {type:"number"}
    input_data['H_A']['V_fan_mid'] = H_A_V_fan_mid_H3
    #@markdown #### <font color="lightblue">**中間運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    H_A_P_fan_mid_H3 = 0.0   #@param {type:"number"}
    input_data['H_A']['P_fan_mid'] = H_A_P_fan_mid_H3

    #@markdown #### <font color="orange">**―コイル特性―**</font>
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW未満の場合のA_f,hex**</font>
    A_f_hex_small_H = 0.2 #@param {type:"number"}
    input_data['H_A']['A_f_hex_small'] = A_f_hex_small_H
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW未満の場合のA_e,hex**</font>
    A_e_hex_small_H = 6.2 #@param {type:"number"}
    input_data['H_A']['A_e_hex_small'] = A_e_hex_small_H
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW以上の場合のA_f,hex**</font>
    A_f_hex_large_H = 0.3 #@param {type:"number"}
    input_data['H_A']['A_f_hex_large'] = A_f_hex_large_H
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW以上の場合のA_e,hex**</font>
    A_e_hex_large_H = 10.6 #@param {type:"number"}
    input_data['H_A']['A_e_hex_large'] = A_e_hex_large_H

    #@markdown #### <font color="orange">**―コンプレッサ効率特性―**</font>
    #@markdown e<sub>r,H,d,t</sub> = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 0 #@param {type:"number"}
    a2 = -0.0316 #@param {type:"number"}
    a1 = 0.2944 #@param {type:"number"}
    a0 = 0 #@param {type:"number"}
    input_data['H_A']['compressor_coeff'] = [a4, a3, a2, a1, a0]

    #@markdown #### <font color="orange">**―風量特性―**</font>
    #@markdown 最小風量 [m3/min]
    airvolume_minimum_H = 14.38995  #@param {type:"number"}
    input_data['H_A']['airvolume_minimum'] = airvolume_minimum_H
    #@markdown 最大風量 [m3/min]
    airvolume_maximum_H = 24.3824  #@param {type:"number"}
    input_data['H_A']['airvolume_maximum'] = airvolume_maximum_H
    #@markdown V'<sub>hs,supply,d,t</sub> [m<sup>3</sup>/min] = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 0 #@param {type:"number"}
    a2 = 0 #@param {type:"number"}
    a1 = 1.2946 #@param {type:"number"}
    a0 = 12.084 #@param {type:"number"}
    input_data['H_A']['airvolume_coeff'] = [a4, a3, a2, a1, a0]

    #@markdown #### <font color="orange">**―ファン消費電力―**</font>
    #@markdown Pfan<sub>qhs,H,d,t</sub> = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 1.4675 #@param {type:"number"}
    a2 = -8.5886 #@param {type:"number"}
    a1 = 20.217 #@param {type:"number"}
    a0 = 50 #@param {type:"number"}
    input_data['H_A']['fan_coeff'] = [a4, a3, a2, a1, a0]

elif input_data['H_A']['type'] == 4:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑦-4 暖房 電力中央研究所のエアコンモデル＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    H_A_input_C_af_H4 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if H_A_input_C_af_H4 == "設置方法を入力する":
        input_data['H_A']['input_C_af_H4'] = 1
    else:
        input_data['H_A']['input_C_af_H4'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    H_A_dedicated_chamber4 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_dedicated_chamber4 == "該当しない":
        input_data['H_A']['dedicated_chamber4'] = 1
    else:
        input_data['H_A']['dedicated_chamber4'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    H_A_fixed_fin_direction4 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if H_A_fixed_fin_direction4 == "該当しない":
        input_data['H_A']['fixed_fin_direction4'] = 1
    else:
        input_data['H_A']['fixed_fin_direction4'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する暖房出力補正係数の入力（入力する場合のみ）**</font>
    H_A_C_af_H4 = 0   #@param {type:"number"}
    input_data['H_A']['C_af_H4'] = H_A_C_af_H4

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 暖房能力―**</font>

    #@markdown #### <font color="lightgreen">**最小時 [kW]**</font>
    H_A_q_rac_pub_min = 0.7   #@param {type:"number"}
    input_data['H_A']['q_rac_pub_min'] = H_A_q_rac_pub_min
    #@markdown #### <font color="lightgreen">**定格時 [kW]**</font>
    H_A_q_rac_pub_rtd = 2.5   #@param {type:"number"}
    input_data['H_A']['q_rac_pub_rtd'] = H_A_q_rac_pub_rtd
    #@markdown #### <font color="lightgreen">**最大時 [kW]**</font>
    H_A_q_rac_pub_max = 5.4   #@param {type:"number"}
    input_data['H_A']['q_rac_pub_max'] = H_A_q_rac_pub_max

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 消費電力―**</font>

    #@markdown #### <font color="lightgreen">**最小時 [W]**</font>
    H_A_P_rac_pub_min = 95  #@param {type:"number"}
    input_data['H_A']['P_rac_pub_min'] = H_A_P_rac_pub_min
    #@markdown #### <font color="lightgreen">**定格時 [W]**</font>
    H_A_P_rac_pub_rtd = 390  #@param {type:"number"}
    input_data['H_A']['P_rac_pub_rtd'] = H_A_P_rac_pub_rtd
    #@markdown #### <font color="lightgreen">**最大時 [W]**</font>
    H_A_P_rac_pub_max = 1360  #@param {type:"number"}
    input_data['H_A']['P_rac_pub_max'] = H_A_P_rac_pub_max

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 風量(強)―**</font>

    #@markdown #### <font color="lightgreen">**室内機 風量 [m3/min]**</font>
    H_A_V_rac_pub_inner = 13.1   #@param {type:"number"}
    input_data['H_A']['V_rac_pub_inner'] = H_A_V_rac_pub_inner
    #@markdown #### <font color="lightgreen">**室外機 風量 [m3/min]**</font>
    H_A_V_rac_pub_outer = 25.5   #@param {type:"number"}
    input_data['H_A']['V_rac_pub_outer'] = H_A_V_rac_pub_outer

    #@markdown #### <font color="orange">**―温熱環境条件 メーカー公表値想定 (JIS条件)―**</font>

    #@markdown #### <font color="lightgreen">**室内機吸込空気: 温度 [℃]**</font>
    H_A_Theta_rac_pub_inner = 20.0  #@param {type:"number"}
    input_data['H_A']['Theta_rac_pub_inner'] = H_A_Theta_rac_pub_inner
    #@markdown #### <font color="lightgreen">**室内機吸込空気: 相対湿度 [%]**</font>
    H_A_RH_rac_pub_inner = 58.6  #@param {type:"number"}
    input_data['H_A']['RH_rac_pub_inner'] = H_A_RH_rac_pub_inner

    #@markdown #### <font color="lightgreen">**室外機吸込空気: 温度 [℃]**</font>
    H_A_Theta_rac_pub_outer = 7.0  #@param {type:"number"}
    input_data['H_A']['Theta_rac_pub_outer'] = H_A_Theta_rac_pub_outer
    #@markdown #### <font color="lightgreen">**室外機吸込空気: 相対湿度 [%]**</font>
    H_A_RH_rac_pub_outer = 86.7  #@param {type:"number"}
    input_data['H_A']['RH_rac_pub_outer'] = H_A_RH_rac_pub_outer

    #@markdown #### <font color="orange">**―温熱環境条件 機器使用時の実測値―**</font>

    #@markdown #### <font color="lightgreen">**室内機吸込空気: 温度 [℃]**</font>
    H_A_Theta_rac_real_inner = 20.0       #@param {type:"number"}
    input_data['H_A']['Theta_rac_real_inner'] = H_A_Theta_rac_real_inner
    #@markdown #### <font color="lightgreen">**室内機吸込空気: 相対湿度 [%]**</font>
    H_A_RH_rac_real_inner = 60.0       #@param {type:"number"}
    input_data['H_A']['RH_rac_real_inner'] = H_A_RH_rac_real_inner

else:
    raise Exception("Not Implement Type")

""" 冷房 共通入力項目 """
#@markdown ---
#@markdown # <font color="orange">**＜⑧ 冷房全般＞**</font>
#@markdown #### <font color="lightgreen">**冷房設備の種類 (1.ﾀﾞｸﾄ式ｾﾝﾄﾗﾙ空調機, 2.ﾙｰﾑｴｱｺﾝﾃﾞｨｼｮﾅ活用型全館空調(現行省ｴﾈ法ﾙｰﾑｴｱｺﾝﾓﾃﾞﾙ), 3.ﾙｰﾑｴｱｺﾝﾃﾞｨｼｮﾅ活用型全館空調(潜熱評価ﾓﾃﾞﾙ), 4.電中研ﾓﾃﾞﾙ)**</font>
input_data['C_A']  = {}
C_A_type = "\u30C0\u30AF\u30C8\u5F0F\u30BB\u30F3\u30C8\u30E9\u30EB\u7A7A\u8ABF\u6A5F" #@param ["ダクト式セントラル空調機", "ルームエアコンディショナ活用型全館空調（現行省エネ法ルームエアコンモデル）", "ルームエアコンディショナ活用型全館空調（新：潜熱評価モデル）", "電中研モデル"] {type:"string"}
if C_A_type == "ダクト式セントラル空調機":
    input_data['C_A']['type'] = 1
elif 'ルームエアコン' in C_A_type and '現行省エネ' in C_A_type:
    input_data['C_A']['type'] = 2
elif 'ルームエアコン' in C_A_type and '潜熱評価モデル' in C_A_type:
    input_data['C_A']['type'] = 3
elif '電中研モデル' in C_A_type:
    input_data['C_A']['type'] = 4
else:
    raise Exception('未定義の方式が選択されました')

#@markdown #### <font color="lightgreen">**ダクトが通過する空間　（全てもしくは一部が断熱区画外である or 全て断熱区画内である）**</font>
C_A_duct_insulation = "\u5168\u3066\u3082\u3057\u304F\u306F\u4E00\u90E8\u304C\u65AD\u71B1\u533A\u753B\u5916\u3067\u3042\u308B"    #@param ["全てもしくは一部が断熱区画外である", "全て断熱区画内である"] {type:"string"}
if C_A_duct_insulation == "全てもしくは一部が断熱区画外である":
    input_data['C_A']['duct_insulation'] = 1
else:
    input_data['C_A']['duct_insulation'] = 2
#@markdown #### <font color="lightgreen">**VAV方式　（採用しない or 採用する）**</font>
C_A_VAV = "採用しない" #@param ["採用しない", "採用する"] {type:"string"}
if C_A_VAV == "採用しない":
    input_data['C_A']['VAV'] = 1
else:
    input_data['C_A']['VAV'] = 2
#@markdown #### <font color="lightgreen">**全般換気機能　（あり or なし）**</font>
C_A_general_ventilation = "あり" #@param ["あり", "なし"] {type:"string"}
if C_A_general_ventilation == "あり":
    input_data['C_A']['general_ventilation'] = 1
else:
    input_data['C_A']['general_ventilation'] = 2

#@markdown #### <font color="orange">**―設計風量―**</font>
#@markdown #### <font color="lightgreen">**設計風量（入力しない or 入力する）**</font>
C_A_input_V_hs_dsgn_C = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['C_A']['input_V_hs_dsgn'] = 1 if C_A_input_V_hs_dsgn_C == "入力しない" else 2
#@markdown #### <font color="lightblue">**設計風量 [m3/h]（入力する場合のみ）**</font>
C_A_V_hs_dsgn_C = 1500    #@param {type:"number"}
input_data['C_A']['V_hs_dsgn'] = C_A_V_hs_dsgn_C

#@markdown [ユーザーマニュアル 最低風量・最低電力 を開く](https://izumi-system-development.github.io/pyhees-jjj/%E6%9C%80%E4%BD%8E%E9%A2%A8%E9%87%8F_%E6%9C%80%E4%BD%8E%E9%9B%BB%E5%8A%9B_%E7%9B%B4%E6%8E%A5%E5%85%A5%E5%8A%9B.html)
#@markdown #### <font color="orange">**―最低風量―**</font>
#@markdown #### <font color="lightgreen">**ファン消費電力から換気分を引くか（換気分を引く or 換気分を引かない）**</font>
C_A_subtract_ventilation_power = "換気分を引く" #@param ["換気分を引く", "換気分を引かない"] {type:"string"}
input_data['C_A']['subtract_ventilation_power'] = 1 if C_A_subtract_ventilation_power == "換気分を引く" else 2
#@markdown > ※ 上記の消費電力計算修正は最低風量入力がないときのみ有効です。
#@markdown #### <font color="lightgreen">**最低風量（入力しない or 入力する）**</font>
C_A_input_V_hs_min = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['C_A']['input_V_hs_min'] = 1 if C_A_input_V_hs_min == "入力しない" else 2
#@markdown #### <font color="lightblue">**最低風量 [m3/h]（入力する場合のみ）**</font>
C_A_V_hs_min = 1200    #@param {type:"number"}
input_data['C_A']['V_hs_min'] = C_A_V_hs_min

#@markdown #### <font color="orange">**―最低電力―**</font>
#@markdown #### <font color="lightgreen">**最低電力（入力しない or 入力する）**</font>
C_A_input_E_E_fan_min = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
input_data['C_A']['input_E_E_fan_min'] = 1 if C_A_input_E_E_fan_min == "入力しない" else 2
#@markdown #### <font color="lightgreen">**ファン消費電力算定方法**</font>
C_A_E_E_fan_logic = "直線近似法" #@param ["直線近似法", "風量三乗近似法"] {type:"string"}
input_data['C_A']['E_E_fan_logic'] = 1 if C_A_E_E_fan_logic == "直線近似法" else 2
#@markdown #### <font color="lightblue">**最低電力 [W]（入力する場合のみ）**</font>
C_A_E_E_fan_min = 100    #@param {type:"number"}
input_data['C_A']['E_E_fan_min'] = C_A_E_E_fan_min

# デフォルト入力として「入力しない」を設定し、あとで必要なら上書きする
input_data['C_A']['input'] = 1
input_data['C_A']['input_mode'] = 1
input_data['C_A']['input_f_SFP'] = 1
input_data['C_A']['input_C_af_C2'] = 1
input_data['C_A']['dedicated_chamber2'] = 1
input_data['C_A']['fixed_fin_direction2'] = 1
input_data['C_A']['input_C_af_C3'] = 1
input_data['C_A']['dedicated_chamber3'] = 1
input_data['C_A']['fixed_fin_direction3'] = 1
input_data['C_A']['input_C_af_C4'] = 1
input_data['C_A']['dedicated_chamber4'] = 1
input_data['C_A']['fixed_fin_direction4'] = 1


""" 冷房 方式別入力項目 """

if input_data['C_A']['type'] == 1:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑧-1 冷房 ダクト式セントラル空調機＞**</font>

    #@markdown #### <font color="orange">**―機器仕様の入力―**</font>
    #@markdown #### <font color="lightgreen">**機器仕様の入力（入力しない or 定格能力試験の値を入力する or 定格能力試験と中間能力試験の値を入力する）**</font>
    C_A_input = "入力しない" #@param ["入力しない", "定格能力試験の値を入力する", "定格能力試験と中間能力試験の値を入力する"] {type:"string"}
    if C_A_input == "入力しない":
        input_data['C_A']['input'] = 1
    elif C_A_input == "定格能力試験の値を入力する":
        input_data['C_A']['input'] = 2
    else:
        input_data['C_A']['input'] = 3

    #@markdown #### <font color="orange">**―定格冷房能力試験―**</font>
    #@markdown #### <font color="lightblue">**定格冷房能力 [W]（入力する場合のみ）**</font>
    C_A_q_hs_rtd_C1 = 0.0    #@param {type:"number"}
    input_data['C_A']['q_hs_rtd'] = C_A_q_hs_rtd_C1
    #@markdown #### <font color="lightblue">**定格冷房消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_hs_rtd_C1 = 0.0    #@param {type:"number"}
    input_data['C_A']['P_hs_rtd'] = C_A_P_hs_rtd_C1
    #@markdown #### <font color="lightblue">**定格運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    C_A_V_fan_rtd_C1 = 0.0   #@param {type:"number"}
    input_data['C_A']['V_fan_rtd'] = C_A_V_fan_rtd_C1
    #@markdown #### <font color="lightblue">**定格運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_fan_rtd_C1 = 0.0   #@param {type:"number"}
    input_data['C_A']['P_fan_rtd'] = C_A_P_fan_rtd_C1

    #@markdown #### <font color="orange">**―中間冷房能力試験―**</font>
    #@markdown #### <font color="lightblue">**中間冷房能力 [W]（入力する場合のみ）**</font>
    C_A_q_hs_mid_C1 = 0.0    #@param {type:"number"}
    input_data['C_A']['q_hs_mid'] = C_A_q_hs_mid_C1
    #@markdown #### <font color="lightblue">**中間冷房消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_hs_mid_C1 = 0.0    #@param {type:"number"}
    input_data['C_A']['P_hs_mid'] = C_A_P_hs_mid_C1
    #@markdown #### <font color="lightblue">**中間運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    C_A_V_fan_mid_C1 = 0.0   #@param {type:"number"}
    input_data['C_A']['V_fan_mid'] = C_A_V_fan_mid_C1
    #@markdown #### <font color="lightblue">**中間運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_fan_mid_C1 = 0.0   #@param {type:"number"}
    input_data['C_A']['P_fan_mid'] = C_A_P_fan_mid_C1

elif input_data['C_A']['type'] == 2:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑧-2 冷房 ルームエアコンディショナ活用型全館空調（現行省エネ法ルームエアコンモデル）＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    C_A_input_C_af_C2 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if C_A_input_C_af_C2 == "設置方法を入力する":
        input_data['C_A']['input_C_af_C2'] = 1
    else:
        input_data['C_A']['input_C_af_C2'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    C_A_dedicated_chamber2 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_dedicated_chamber2 == "該当しない":
        input_data['C_A']['dedicated_chamber2'] = 1
    else:
        input_data['C_A']['dedicated_chamber2'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    C_A_fixed_fin_direction2 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_fixed_fin_direction2 == "該当しない":
        input_data['C_A']['fixed_fin_direction2'] = 1
    else:
        input_data['C_A']['fixed_fin_direction2'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する冷房出力補正係数の入力（入力する場合のみ）**</font>
    C_A_C_af_C2 = 0.0   #@param {type:"number"}
    input_data['C_A']['C_af_C2'] = C_A_C_af_C2

    #@markdown #### <font color="orange">**―エネルギー消費効率の入力―**</font>
    #@markdown #### <font color="lightgreen">**エネルギー消費効率の入力（入力しない or 入力する）**</font>
    C_A_input_mode = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
    if C_A_input_mode == "入力しない":
        input_data['C_A']['input_mode'] = 1
    else:
        input_data['C_A']['input_mode'] = 2

    #@markdown #### <font color="lightblue">**エネルギー消費効率（い or ろ or は）（入力する場合のみ）**</font>
    C_A_mode = "\u306F" #@param ["い", "ろ", "は"] {type:"string"}
    if C_A_mode == 'い':
        input_data['C_A']['mode'] = 1
    elif C_A_mode == 'ろ':
        input_data['C_A']['mode'] = 2
    else:
        input_data['C_A']['mode'] = 3

    #@markdown #### <font color="orange">**―冷房能力の入力―**</font>
    #@markdown #### <font color="lightgreen">**冷房能力の入力（面積から能力を算出 or 性能を直接入力）**</font>
    C_A_input_rac_performance = "\u9762\u7A4D\u304B\u3089\u80FD\u529B\u3092\u7B97\u51FA" #@param ["面積から能力を算出", "性能を直接入力"] {type:"string"}
    if C_A_input_rac_performance == "面積から能力を算出":
        input_data['C_A']['input_rac_performance'] = 1
    else:
        input_data['C_A']['input_rac_performance'] = 2
    #@markdown #### <font color="lightblue">**冷房定格能力 [W]（入力する場合のみ）**</font>
    C_A_q_rac_rtd_C = 0   #@param {type:"number"}
    input_data['C_A']['q_rac_rtd_C'] = C_A_q_rac_rtd_C
    #@markdown #### <font color="lightblue">**冷房最大能力 [W]（入力する場合のみ）**</font>
    C_A_q_rac_max_C = 0   #@param {type:"number"}
    input_data['C_A']['q_rac_max_C'] = C_A_q_rac_max_C
    #@markdown #### <font color="lightblue">**定格エネルギー効率 [-]（入力する場合のみ）**</font>
    e_rac_rtd_C = 0   #@param {type:"number"}
    input_data['C_A']['e_rac_rtd_C'] = e_rac_rtd_C
    #@markdown #### <font color="lightgreen">**小能力時高効率型コンプレッサー（評価しない or 搭載する）**</font>
    C_A_dualcompressor = "評価しない" #@param ["評価しない", "搭載する"] {type:"string"}
    if C_A_dualcompressor == "評価しない":
        input_data['C_A']['dualcompressor'] = 1
    else:
        input_data['C_A']['dualcompressor'] = 2

    #@markdown #### <font color="orange">**―ファンの消費電力―**</font>
    #@markdown #### <font color="lightgreen">**ファンの比消費電力（入力しない or 入力する）**</font>
    C_A_input_f_SFP_C = "\u5165\u529B\u3057\u306A\u3044" #@param ["入力しない", "入力する"] {type:"string"}
    input_data['C_A']['input_f_SFP'] = 1 if C_A_input_f_SFP_C == "入力しない" else 2
    #@markdown #### <font color="lightblue">**ファンの比消費電力 [W / (m3/h)]（入力する場合のみ）**</font>
    C_A_f_SFP_C = 0.144    #@param {type:"number"}
    input_data['C_A']['f_SFP'] = C_A_f_SFP_C

elif input_data['C_A']['type'] == 3:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑧-3 冷房 ルームエアコンディショナ活用型全館空調（潜熱評価モデル）＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    C_A_input_C_af_C3 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if C_A_input_C_af_C3 == "設置方法を入力する":
        input_data['C_A']['input_C_af_C3'] = 1
    else:
        input_data['C_A']['input_C_af_C3'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    C_A_dedicated_chamber3 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_dedicated_chamber3 == "該当しない":
        input_data['C_A']['dedicated_chamber3'] = 1
    else:
        input_data['C_A']['dedicated_chamber3'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    C_A_fixed_fin_direction3 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_fixed_fin_direction3 == "該当しない":
        input_data['C_A']['fixed_fin_direction3'] = 1
    else:
        input_data['C_A']['fixed_fin_direction3'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する冷房出力補正係数の入力（入力する場合のみ）**</font>
    C_A_C_af_C3 = 0.0   #@param {type:"number"}
    input_data['C_A']['C_af_C3'] = C_A_C_af_C3

    #@markdown #### <font color="orange">**―機器仕様の入力―**</font>
    #@markdown #### <font color="lightgreen">**機器仕様の入力（入力しない or 定格能力試験の値を入力する or 定格能力試験と中間能力試験の値を入力する）**</font>
    C_A_input3 = "入力しない" #@param ["入力しない", "定格能力試験の値を入力する", "定格能力試験と中間能力試験の値を入力する"] {type:"string"}
    if C_A_input3 == "入力しない":
        input_data['C_A']['input'] = 1
    elif C_A_input3 == "定格能力試験の値を入力する":
        input_data['C_A']['input'] = 2
    else:
        input_data['C_A']['input'] = 3

    #@markdown #### <font color="orange">**―定格冷房能力試験―**</font>
    #@markdown #### <font color="lightblue">**定格冷房能力 [W]（入力する場合のみ）**</font>
    C_A_q_hs_rtd_C3 = 0.0    #@param {type:"number"}
    input_data['C_A']['q_hs_rtd'] = C_A_q_hs_rtd_C3
    #@markdown #### <font color="lightblue">**定格冷房消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_hs_rtd_C3 = 0.0    #@param {type:"number"}
    input_data['C_A']['P_hs_rtd'] = C_A_P_hs_rtd_C3
    #@markdown #### <font color="lightblue">**定格運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    C_A_V_fan_rtd_C3 = 0.0   #@param {type:"number"}
    input_data['C_A']['V_fan_rtd'] = C_A_V_fan_rtd_C3
    #@markdown #### <font color="lightblue">**定格運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_fan_rtd_C3 = 0.0   #@param {type:"number"}
    input_data['C_A']['P_fan_rtd'] = C_A_P_fan_rtd_C3

    #@markdown #### <font color="orange">**―中間冷房能力試験―**</font>
    #@markdown #### <font color="lightblue">**中間冷房能力 [W]（入力する場合のみ）**</font>
    C_A_q_hs_mid_C3 = 0.0    #@param {type:"number"}
    input_data['C_A']['q_hs_mid'] = C_A_q_hs_mid_C3
    #@markdown #### <font color="lightblue">**中間冷房消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_hs_mid_C3 = 0.0    #@param {type:"number"}
    input_data['C_A']['P_hs_mid'] = C_A_P_hs_mid_C3
    #@markdown #### <font color="lightblue">**中間運転時の送風機の風量 [m3/h]（入力する場合のみ）**</font>
    C_A_V_fan_mid_C3 = 0.0   #@param {type:"number"}
    input_data['C_A']['V_fan_mid'] = C_A_V_fan_mid_C3
    #@markdown #### <font color="lightblue">**中間運転時の送風機の消費電力 [W]（入力する場合のみ）**</font>
    C_A_P_fan_mid_C3 = 0.0   #@param {type:"number"}
    input_data['C_A']['P_fan_mid'] = C_A_P_fan_mid_C3

    #@markdown #### <font color="orange">**―コイル特性―**</font>
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW未満の場合のA_f,hex**</font>
    A_f_hex_small_C = 0.2 #@param {type:"number"}
    input_data['C_A']['A_f_hex_small'] = A_f_hex_small_C
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW未満の場合のA_e,hex**</font>
    A_e_hex_small_C = 6.2 #@param {type:"number"}
    input_data['C_A']['A_e_hex_small'] = A_e_hex_small_C
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW以上の場合のA_f,hex**</font>
    A_f_hex_large_C = 0.3 #@param {type:"number"}
    input_data['C_A']['A_f_hex_large'] = A_f_hex_large_C
    #@markdown #### <font color="lightgreen">**定格冷却能力が5.6kW以上の場合のA_e,hex**</font>
    A_e_hex_large_C = 10.6 #@param {type:"number"}
    input_data['C_A']['A_e_hex_large'] = A_e_hex_large_C

    #@markdown #### <font color="orange">**―熱伝達特性―**</font>
    #@markdown α'<sub>c,hex,C</sub> = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 0 #@param {type:"number"}
    a2 = 0 #@param {type:"number"}
    a1 = 0.0631 #@param {type:"number"}
    a0 = 0.0015 #@param {type:"number"}
    input_data['C_A']['heat_transfer_coeff'] = [a4, a3, a2, a1, a0]

    #@markdown #### <font color="orange">**―コンプレッサ効率特性―**</font>
    #@markdown e<sub>r,C,d,t</sub> = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 0 #@param {type:"number"}
    a2 = -0.0316 #@param {type:"number"}
    a1 = 0.2944 #@param {type:"number"}
    a0 = 0 #@param {type:"number"}
    input_data['C_A']['compressor_coeff'] = [a4, a3, a2, a1, a0]

    #@markdown #### <font color="orange">**―風量特性―**</font>
    #@markdown 最小風量 [m3/min]
    airvolume_minimum_C = 14.38995  #@param {type:"number"}
    input_data['C_A']['airvolume_minimum'] = airvolume_minimum_C
    #@markdown 最大風量 [m3/min]
    airvolume_maximum_C = 24.3824  #@param {type:"number"}
    input_data['C_A']['airvolume_maximum'] = airvolume_maximum_C
    #@markdown V'<sub>hs,supply,d,t</sub> [m<sup>3</sup>/min] = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 0 #@param {type:"number"}
    a2 = 0 #@param {type:"number"}
    a1 = 2.4855 #@param {type:"number"}
    a0 = 10.209 #@param {type:"number"}
    input_data['C_A']['airvolume_coeff'] = [a4, a3, a2, a1, a0]

    #@markdown #### <font color="orange">**―ファン消費電力―**</font>
    #@markdown P<sub>fan,C,d,t</sub> = a<sub>4</sub> x<sup>4</sup> + a<sub>3</sub> x<sup>3</sup> + a<sub>2</sub> x<sup>2</sup> + a<sub>1</sub> x + a<sub>0</sub>
    a4 = 0 #@param {type:"number"}
    a3 = 1.4675 #@param {type:"number"}
    a2 = 8.5886 #@param {type:"number"}
    a1 = 20.217 #@param {type:"number"}
    a0 = 50 #@param {type:"number"}
    input_data['C_A']['fan_coeff'] = [a4, a3, a2, a1, a0]

elif input_data['C_A']['type'] == 4:
    #@markdown ---
    #@markdown # <font color="orange">**＜⑧-4 冷房 電力中央研究所のエアコンモデル＞**</font>

    #@markdown #### <font color="orange">**―設置方法の入力―**</font>
    #@markdown #### <font color="lightgreen">**設置方法の入力（設置方法を入力する or 補正係数を直接入力する）**</font>
    C_A_input_C_af_C4 = "設置方法を入力する" #@param ["設置方法を入力する", "補正係数を直接入力する"] {type:"string"}
    if C_A_input_C_af_C4 == "設置方法を入力する":
        input_data['C_A']['input_C_af_C4'] = 1
    else:
        input_data['C_A']['input_C_af_C4'] = 2
    #@markdown #### <font color="lightblue">**専用チャンバーに格納される方式（該当しない or 該当する）**</font>
    C_A_dedicated_chamber4 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_dedicated_chamber4 == "該当しない":
        input_data['C_A']['dedicated_chamber4'] = 1
    else:
        input_data['C_A']['dedicated_chamber4'] = 2
    #@markdown #### <font color="lightblue">**フィン向きが中央位置に固定される方式（該当しない or 該当する）**</font>
    C_A_fixed_fin_direction4 = "該当しない" #@param ["該当しない", "該当する"] {type:"string"}
    if C_A_fixed_fin_direction4 == "該当しない":
        input_data['C_A']['fixed_fin_direction4'] = 1
    else:
        input_data['C_A']['fixed_fin_direction4'] = 2
    #@markdown #### <font color="lightblue">**室内機吹き出し風量に関する冷房出力補正係数の入力（入力する場合のみ）**</font>
    C_A_C_af_C4 = 0.0   #@param {type:"number"}
    input_data['C_A']['C_af_C4'] = C_A_C_af_C4

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 冷房能力―**</font>

    #@markdown #### <font color="lightgreen">**最小時 [kW]**</font>
    C_A_q_rac_pub_min = 0.7   #@param {type:"number"}
    input_data['C_A']['q_rac_pub_min'] = C_A_q_rac_pub_min
    #@markdown #### <font color="lightgreen">**定格時 [kW]**</font>
    C_A_q_rac_pub_rtd = 2.2   #@param {type:"number"}
    input_data['C_A']['q_rac_pub_rtd'] = C_A_q_rac_pub_rtd
    #@markdown #### <font color="lightgreen">**最大時 [kW]**</font>
    C_A_q_rac_pub_max = 3.3   #@param {type:"number"}
    input_data['C_A']['q_rac_pub_max'] = C_A_q_rac_pub_max

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 消費電力―**</font>

    #@markdown #### <font color="lightgreen">**最小時 [W]**</font>
    C_A_P_rac_pub_min = 95   #@param {type:"number"}
    input_data['C_A']['P_rac_pub_min'] = C_A_P_rac_pub_min
    #@markdown #### <font color="lightgreen">**定格時 [W]**</font>
    C_A_P_rac_pub_rtd = 395   #@param {type:"number"}
    input_data['C_A']['P_rac_pub_rtd'] = C_A_P_rac_pub_rtd
    #@markdown #### <font color="lightgreen">**最大時 [W]**</font>
    C_A_P_rac_pub_max = 780   #@param {type:"number"}
    input_data['C_A']['P_rac_pub_max'] = C_A_P_rac_pub_max

    #@markdown #### <font color="orange">**―機器性能 メーカー公表値: 風量(強)―**</font>

    #@markdown #### <font color="lightgreen">**室内機 風量 [m3/min]**</font>
    C_A_V_rac_pub_inner = 12.1   #@param {type:"number"}
    input_data['C_A']['V_rac_pub_inner'] = C_A_V_rac_pub_inner
    #@markdown #### <font color="lightgreen">**室外機 風量 [m3/min]**</font>
    C_A_V_rac_pub_outer = 28.2   #@param {type:"number"}
    input_data['C_A']['V_rac_pub_outer'] = C_A_V_rac_pub_outer

    #@markdown #### <font color="orange">**―温熱環境条件 メーカー公表値想定 (JIS条件)―**</font>

    #@markdown #### <font color="lightgreen">**室内機吸込空気: 温度 [℃]**</font>
    C_A_Theta_rac_pub_inner = 27.0       #@param {type:"number"}
    input_data['C_A']['Theta_rac_pub_inner'] = C_A_Theta_rac_pub_inner
    #@markdown #### <font color="lightgreen">**室内機吸込空気: 相対湿度 [%]**</font>
    C_A_RH_rac_pub_inner = 46.6       #@param {type:"number"}
    input_data['C_A']['RH_rac_pub_inner'] = C_A_RH_rac_pub_inner

    #@markdown #### <font color="lightgreen">**室外機吸込空気: 温度 [℃]**</font>
    C_A_Theta_rac_pub_outer = 35.0       #@param {type:"number"}
    input_data['C_A']['Theta_rac_pub_outer'] = C_A_Theta_rac_pub_outer
    #@markdown #### <font color="lightgreen">**室外機吸込空気: 相対湿度 [%]**</font>
    C_A_RH_rac_pub_outer = 40.0       #@param {type:"number"}
    input_data['C_A']['RH_rac_pub_outer'] = C_A_RH_rac_pub_outer

    #@markdown #### <font color="orange">**―温熱環境条件 機器使用時の実測値―**</font>

    #@markdown #### <font color="lightgreen">**室内機吸込空気: 温度 [℃]**</font>
    C_A_Theta_rac_real_inner = 27.0       #@param {type:"number"}
    input_data['C_A']['Theta_rac_real_inner'] = C_A_Theta_rac_real_inner
    #@markdown #### <font color="lightgreen">**室内機吸込空気: 相対湿度 [%]**</font>
    C_A_RH_rac_real_inner = 60.0       #@param {type:"number"}
    input_data['C_A']['RH_rac_real_inner'] = C_A_RH_rac_real_inner

else:
    raise Exception("Not Implement Type")

""" 熱交換型換気設備 """

#@markdown ---
#@markdown # <font color="orange">**＜⑨ 熱交換型換気設備）＞**</font>
#@markdown #### <font color="lightblue">**熱交換型換気設備（設置しない or 設置する）**</font>
input_data['HEX'] = {}

HEX_install = "\u8A2D\u7F6E\u3057\u306A\u3044" #@param ["設置しない", "設置する"] {type:"string"}
if HEX_install == "設置しない":
    input_data['HEX']['install'] = 1
else:
    input_data['HEX']['install'] = 2
#@markdown #### <font color="lightblue">**温度交換効率（設置する場合のみ）**</font>
etr_t = 40   #@param {type:"number"}
input_data['HEX']['etr_t'] = etr_t / 100

jjjexperiment.main.calc(input_data)
