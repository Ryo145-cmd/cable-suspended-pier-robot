#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMUの取り付け向き（config.py の IMU_AXIS_*）が正しいか確認する
  python3 tools/imu_check.py

確認手順：
  1. 機体をまっすぐ吊るす → 「加速度角」がほぼ 0°
  2. 正面から見て右側を下げる → 「加速度角」がプラスになる
     マイナスになるなら IMU_AXIS_RIGHT の符号を反転
  3. 右側を下げる動きの最中に「角速度」がプラス
     マイナスなら IMU_AXIS_NORMAL の符号を反転
  4. 「推定角」が加速度角と同じ向きに滑らかに追従すればOK
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
from imu import TiltEstimator, build_imu

imu = build_imu(C)
est = TiltEstimator(imu, C)
print("校正中… 静止させてください")
est.calibrate(C.IMU_CALIB_SAMPLES)
last = time.monotonic()
try:
    while True:
        now = time.monotonic()
        dt, last = now - last, now
        th = est.update(dt)
        a, _ = imu.read()
        print(f"\r加速度角 {est._accel_angle(a):+7.2f}°  角速度 {est.raw_rate:+7.2f}°/s  "
              f"推定角 {th:+7.2f}°   raw a=({a['x']:+.2f},{a['y']:+.2f},{a['z']:+.2f})   ",
              end="", flush=True)
        time.sleep(0.02)
except KeyboardInterrupt:
    print()
finally:
    imu.close()
