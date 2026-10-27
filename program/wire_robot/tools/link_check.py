#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通信の生存確認（ウォッチドッグ）の確認
  python3 tools/link_check.py

コントローラのモーションセンサからの受信間隔を1秒ごとに表示する。
  ・「最大間隔」が普段から LINK_TIMEOUT_SEC（0.2秒）より十分小さいこと（目安 0.05 秒以下）
  ・コントローラを置いたまま（静止）でも受信が続くこと
  ・機体の作業位置（橋脚の裏側など）まで離れても途絶が出ないこと
  ・コントローラの電源を切る（PSボタン長押し 10秒）と「途絶」が 0.2 秒程度で出ること
を確認する。Ctrl+C で終了。
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
from gamepad import Gamepad

pad = Gamepad(C)
pad.start()
print(f"判定しきい値 LINK_TIMEOUT_SEC = {C.LINK_TIMEOUT_SEC} 秒（Ctrl+C で終了）")

last_state = None
last_rx = 0.0
gap_max = 0.0
count = 0
lost_since = None
t_print = time.monotonic() + 1.0
try:
    while True:
        now = time.monotonic()
        state = pad.link(now)
        if state != last_state:
            extra = ""
            if state == "ok":
                extra = f"  {pad.name} / 生存確認: {pad.motion_name or 'なし'}"
                if lost_since is not None:
                    extra += f"（途絶 {now - lost_since:.2f} 秒）"
                lost_since = None
            elif state == "lost":
                lost_since = now
                extra = f"  最後の受信から {now - pad.last_rx:.3f} 秒"
            print(f"\n[{time.strftime('%H:%M:%S')}] {state}{extra}")
            last_state = state
        rx = pad.last_rx
        if rx != last_rx:
            if last_rx:
                gap_max = max(gap_max, rx - last_rx)
            last_rx = rx
            count += 1
        if now >= t_print:
            t_print = now + 1.0
            warn = "  ← しきい値に近い!" if gap_max > C.LINK_TIMEOUT_SEC * 0.5 else ""
            print(f"\r受信 {count:4d} 回/秒  最大間隔 {gap_max * 1000:6.1f} ms{warn}      ",
                  end="", flush=True)
            gap_max = 0.0
            count = 0
        time.sleep(0.001)
except KeyboardInterrupt:
    print()
