# -*- coding: utf-8 -*-
"""傾き補正のPI制御と加速制限"""
from mixer import clamp


class TiltController:
    def __init__(self, kp, ki, i_limit, out_limit, deadband):
        self.kp, self.ki = kp, ki
        self.i_limit, self.out_limit, self.deadband = i_limit, out_limit, deadband
        self.integ = 0.0

    def reset(self):
        self.integ = 0.0

    def update(self, theta_deg, dt):
        """theta_deg: + = 右側が下がっている → 戻り値 + = 右を持ち上げる"""
        a = abs(theta_deg) - self.deadband
        e = 0.0 if a <= 0 else (a if theta_deg > 0 else -a)
        self.integ = clamp(self.integ + e * dt, -self.i_limit, self.i_limit)
        out = self.kp * e + self.ki * self.integ
        return clamp(out, -self.out_limit, self.out_limit)


class SlewLimiter:
    """加速だけを制限（減速・停止は即時）"""

    def __init__(self, rate):
        self.rate = rate
        self.value = 0.0

    def step(self, target, dt):
        cur = self.value
        # 減速方向（0に近づく／符号反転を含む）なら、まず即座に0までは落とす
        if cur != 0.0 and (target == 0.0 or (target > 0) != (cur > 0)):
            cur = 0.0
        if abs(target) < abs(cur):
            cur = target
        else:
            d = clamp(target - cur, -self.rate * dt, self.rate * dt)
            cur += d
        self.value = cur
        return cur

    def reset(self):
        self.value = 0.0
