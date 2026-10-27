# -*- coding: utf-8 -*-
"""ハードなしで動くロジックのテスト:  python3 -m pytest tests  （または python3 tests/test_logic.py）"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
from controller import SlewLimiter, TiltController
from imu import SimIMU, TiltEstimator
from mixer import apply_deadzone, axis_lock, mix
from motors import build_motors


def test_vertical_all_same():
    c = mix(0.5, 0.0, 0.0)
    assert all(abs(v - 0.5) < 1e-9 for v in c.values())


def test_lateral_outer_fixed_inner_opposite():
    c = mix(0.0, 0.4, 0.0, lateral_sign=1)
    assert c["UL"] == 0 and c["UR"] == 0
    assert c["LL"] > 0 and c["LR"] < 0 and abs(c["LL"] + c["LR"]) < 1e-9


def test_correction_raises_right():
    c = mix(0.0, 0.0, 0.2)
    assert c["UR"] > c["UL"]


def test_saturation_keeps_ratio():
    c = mix(0.9, 0.5, 0.0)
    assert max(abs(v) for v in c.values()) <= 1.0 + 1e-9
    assert abs(c["LL"] / c["UL"] - 1.4 / 0.9) < 1e-9


def test_deadzone_and_lock():
    assert apply_deadzone(0.05, 0.12) == 0.0
    assert abs(apply_deadzone(1.0, 0.12) - 1.0) < 1e-9
    assert axis_lock(0.3, 0.6) == (0.0, 0.6)


def test_slew_accel_limited_stop_immediate():
    s = SlewLimiter(2.0)
    assert abs(s.step(1.0, 0.1) - 0.2) < 1e-9
    assert s.step(0.0, 0.1) == 0.0
    s.step(0.5, 1.0)
    assert s.step(-0.5, 0.1) < 0 and s.step(-0.5, 0.1) >= -0.5


def test_wire_adjust_single_motor():
    from mixer import wire_adjust
    c = wire_adjust({"LR"}, -0.3)
    assert c == {"UL": 0.0, "UR": 0.0, "LL": 0.0, "LR": -0.3}
    c = wire_adjust({"UL", "UR"}, 0.5)
    assert c == {"UL": 0.5, "UR": 0.5, "LL": 0.0, "LR": 0.0}
    assert wire_adjust(set(), 0.8) == {"UL": 0.0, "UR": 0.0, "LL": 0.0, "LR": 0.0}


def test_closed_loop_levels_robot():
    """シミュレータで 3° 傾いた機体が水平に戻るか"""
    ms = build_motors(C, sim=True)
    imu = SimIMU(initial_tilt=3.0)
    imu.attach(ms)
    est = TiltEstimator(imu, C)
    est.calibrate(5)
    tc = TiltController(C.TILT_KP, C.TILT_KI, C.TILT_I_LIMIT,
                        C.TILT_MAX_CORRECTION, C.TILT_DEADBAND_DEG)
    dt = 1.0 / C.LOOP_HZ
    for _ in range(int(10 / dt)):
        imu.step(dt)
        th = est.update(dt)
        ms.set(mix(0.0, 0.0, tc.update(th, dt)))
    assert abs(imu.theta) < 1.0, imu.theta


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
