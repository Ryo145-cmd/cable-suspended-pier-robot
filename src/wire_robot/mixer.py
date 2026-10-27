# -*- coding: utf-8 -*-
"""スティック入力 → 4ドラムの指令値 への変換（ハードウェア非依存）"""


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def apply_deadzone(v, dz):
    """デッドゾーン処理。外側は 0〜1 に引き伸ばす"""
    if abs(v) < dz:
        return 0.0
    s = 1.0 if v > 0 else -1.0
    return s * (abs(v) - dz) / (1.0 - dz)


def axis_lock(vy, vx):
    """上下・左右のうち大きい方だけを残す"""
    if abs(vy) >= abs(vx):
        return vy, 0.0
    return 0.0, vx


def mix(vy, vx, corr, lateral_sign=1):
    """
    vy   : 上下指令（+ = 上昇 = 4本とも巻き取り）
    vx   : 左右指令（+ = 右）
    corr : 傾き補正（+ = 右側を持ち上げる）
    戻り値: {"UL","UR","LL","LR"} 各 -1〜1（+ = 巻き取り）

    ・上下移動 : 4本を同方向に回す
    ・左右移動 : 上下プーリはそのまま、左右プーリを逆回転（巻き取り／巻き出し）
    ・傾き補正 : 上下プーリ（外側）の差動で姿勢を保つ
    """
    vx = vx * lateral_sign
    cmd = {
        "UL": vy - corr,
        "UR": vy + corr,
        "LL": vy + vx,
        "LR": vy - vx,
    }
    # 飽和したら比率を保ったまま縮める
    m = max(1.0, max(abs(v) for v in cmd.values()))
    return {k: v / m for k, v in cmd.items()}


def wire_adjust(selected, v, names=("UL", "UR", "LL", "LR")):
    """ワイヤ調整モード：selected（ボタンを押しているモータの集合）だけを v（+ = 巻き取り）で回す"""
    v = clamp(v, -1.0, 1.0)
    return {k: (v if k in selected else 0.0) for k in names}
