#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
モータを1つずつ回して、配線と「巻き取り方向」を確認する（コントローラ不要）
  python3 tools/test_motors.py
最初はワイヤを外すか、たるませた状態で行うこと。
"+" で回したときにワイヤを巻き取る方向に回らなければ、config.py の invert を反転する。
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
from motors import build_motors

DUTY = 0.3
DURATION = 1.0

ms = build_motors(C, sim="--sim" in sys.argv)
try:
    while True:
        s = input("\nモータ名(UL/UR/LL/LR) と 向き(+/-) 例: UL+   q で終了 > ").strip().upper()
        if s == "Q":
            break
        if len(s) < 3 or s[:2] not in C.MOTORS or s[2] not in "+-":
            print("入力例: UL+ / LR-")
            continue
        v = DUTY if s[2] == "+" else -DUTY
        print(f"{s[:2]}（{C.MOTOR_LABELS[s[:2]]}）を {v:+.2f} で {DURATION}s 回します")
        ms.enable(True)
        ms.set({s[:2]: v})
        time.sleep(DURATION)
        ms.stop_all()
        ms.enable(False)
finally:
    ms.close()
