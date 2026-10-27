# -*- coding: utf-8 -*-
"""
設定ファイル ― 配線・機体に合わせてここだけ書き換える

座標・符号の約束
  ・モータ指令 +1.0 = ワイヤを「巻き取る」方向、-1.0 = 「巻き出す」方向
    → 実際の回転方向が逆なら各モータの invert を True にする
  ・傾き θ [deg] は、機体を正面（壁の反対側）から見て「右側が下がる」向きを正
"""

# ============================================================
# モータ（ドラム）
# ============================================================
#   UL : 左 上下プーリ（外側ワイヤ）   UR : 右 上下プーリ（外側ワイヤ）
#   LL : 左 左右プーリ（内側ワイヤ）   LR : 右 左右プーリ（内側ワイヤ）
#
# MOTOR_DRIVER_MODE
#   "ibt2"    : IBT-2 (BTS7960)。RPWM / LPWM の2本をPWM、R_EN・L_EN は共通の ENABLE_PIN へ
#   "pwm_dir" : PWMピン + 方向ピン（Cytron MD10C / MDD10A など）
#   "in1_in2" : 2本の入力ピンをPWM（L298N / DRV8833 など）
MOTOR_DRIVER_MODE = "ibt2"
PWM_FREQUENCY = 1000            # [Hz]

# 4台の IBT-2 の R_EN と L_EN をすべてまとめてこのピンへ（BCM番号）
# Lにすると全ブリッジが切れる＝全モータ停止。None なら EN は IBT-2 上で VCC(3.3V) に直結している扱い
# GPIO26 は起動直後プルダウンなので、プログラムが動くまでモータは回らない
ENABLE_PIN = 26

# ピン番号は BCM 番号（I2C の GPIO2/3 は IMU 用なので使わない）
#   rpwm : IBT-2 の RPWM（+指令でこちらにPWM）
#   lpwm : IBT-2 の LPWM
MOTORS = {
    "UL": {"rpwm": 12, "lpwm": 13, "invert": False},
    "UR": {"rpwm": 18, "lpwm": 19, "invert": True},
    "LL": {"rpwm": 20, "lpwm": 21, "invert": False},
    "LR": {"rpwm": 23, "lpwm": 24, "invert": True},
}
# 表示名
MOTOR_LABELS = {
    "UL": "左 上下プーリ",
    "UR": "右 上下プーリ",
    "LL": "左 左右プーリ",
    "LR": "右 左右プーリ",
}

# 左右移動の向き。+1: 右へ動くとき LL を巻き取り・LR を巻き出し
# （資料12枚目の矢印からの推定。逆に動いたら -1 にする）
LATERAL_SIGN = +1

MAX_DUTY = 0.8           # 最大デューティ（0〜1）
LOW_SPEED_SCALE = 0.4    # 通常時の速度倍率（FAST ボタンを押している間は 1.0）
MIN_DUTY = 0.12          # これ未満ではモータが回らない分の底上げ（0で無効）
SLEW_RATE = 2.0          # 加速の上限 [デューティ/秒]（停止は即時）

# ワイヤ調整モード：肩ボタンを1回押すとそのモータを選択（別のボタンで切り替え）
#   選んだモータだけを左スティック上下で動かす。上 = 巻き取り / 下 = 巻き出し
#   速度は倒し具合 × WIRE_ADJUST_SCALE
WIRE_ADJUST_SCALE = 0.3
# ボタンの位置 = 機体のドラムの位置（実機の配置と違えば右側の名前を入れ替える）
WIRE_BUTTONS = {
    "BTN_TL":  "LL",   # L1 = 左上
    "BTN_TR":  "LR",   # R1 = 右上
    "BTN_TL2": "UL",   # L2 = 左下
    "BTN_TR2": "UR",   # R2 = 右下
}

# ============================================================
# 傾き補正（IMU）
# ============================================================
TILT_CORRECTION_DEFAULT_ON = True
TILT_KP = 0.04           # [デューティ/deg]  5°傾くと 0.2
TILT_KI = 0.01           # [デューティ/(deg·s)]
TILT_I_LIMIT = 20.0      # 積分項の上限 [deg·s]
TILT_MAX_CORRECTION = 0.3    # 補正量の上限 [デューティ]
TILT_DEADBAND_DEG = 0.5      # この範囲の傾きは無視
TILT_LIMIT_DEG = 12.0        # 走行モードでこれを超えたら移動を止め、補正だけ行う
COMPLEMENTARY_ALPHA = 0.98   # 相補フィルタ係数（ジャイロ側の重み）

# IMU (MPU6050)
IMU_TYPE = "mpu6050"
IMU_I2C_BUS = 1
IMU_I2C_ADDR = 0x68
# 取り付け向き：機体の「右」「上」がIMUのどの軸か、壁に垂直な軸がどれか
# 例) "+x", "-y", "+z"。tools/imu_check.py で確認する
IMU_AXIS_RIGHT = "+x"
IMU_AXIS_UP = "+y"
IMU_AXIS_NORMAL = "+z"   # 正の角速度 = 右側が下がる向き になる符号を選ぶ
IMU_CALIB_SAMPLES = 200  # 起動時のジャイロバイアス計測サンプル数（静止させる）

# ============================================================
# ゲームパッド：PS5 DualSense（Linux の hid-playstation ドライバでのコード名）
# 違う場合は tools/gamepad_check.py で確認して書き換える
# ============================================================
GAMEPAD_NAME = "Wireless Controller"   # 名前の一部（タッチパッド等の別デバイスは自動で除外）

AXIS_VERTICAL = "ABS_Y"        # 左スティック 上下 → 上下移動
AXIS_VERTICAL_INVERT = True    # スティック上 = 負値なので反転（上に倒す＝上昇）
AXIS_LATERAL = "ABS_RX"        # 右スティック 左右 → 左右移動
AXIS_LATERAL_INVERT = False
STICK_DEADZONE = 0.2      # ±0.2 以内は「触っていない」扱い（ドリフト対策）
AXIS_LOCK = False        # False: 上下と左右を同時に動かせる（斜め移動）／ True: 大きく倒した方だけ

BTN_FAST = "BTN_TR"            # R1：走行モードで押している間は高速
BTN_ESTOP = "BTN_SOUTH"        # ×：非常停止（ラッチ）
BTN_RESET = "BTN_START"        # OPTIONS：非常停止の解除（スティックを離した状態で）
BTN_TILT_TOGGLE = "BTN_NORTH"  # △：傾き補正 ON/OFF
BTN_LEVEL_ZERO = "BTN_SELECT"  # CREATE：今の姿勢を「水平」として記録
BTN_SWITCH_MODE = "BTN_MODE"   # PSボタン：走行モード ⇔ ワイヤ調整モード（スティックを離した状態で）

# 通信の生存確認（ウォッチドッグ）
#   DualSense のモーションセンサから常に流れてくるイベントを受信の証拠にし、
#   最後の受信からこの時間が経ったら「通信途絶」として全モータを止める
#   （復帰後はスティックが一度中央に戻るまで動かない）
#   tools/link_check.py で普段の受信間隔の最大値を確認し、それより十分大きい値にする
LINK_TIMEOUT_SEC = 0.2
#   True : モーションセンサが見つからない（生存確認できない）ときは動かさない（推奨）
#   False: 見つからなくても動かす（従来どおり、切断判定はカーネル任せ）
LINK_REQUIRE_MOTION = True

# ライトバーの色 (R, G, B) 0〜255
COLOR_DRIVE = (0, 0, 255)      # 走行：青
COLOR_WIRE = (255, 90, 0)      # ワイヤ調整：オレンジ
COLOR_ESTOP = (255, 0, 0)      # 非常停止：赤
BLINK_SEC = 0.3                # スティックが中央に戻るのを待つ間の点滅周期（半周期）
RUMBLE_MS = 200                # モード切替時の振動の長さ（0で無効）
SELECT_RUMBLE_MS = 80          # ワイヤ調整モードでモータを選んだときの短い振動

# ============================================================
# ループ
# ============================================================
LOOP_HZ = 50
STATUS_HZ = 2
