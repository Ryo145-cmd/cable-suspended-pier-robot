#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ゲームパッドのボタン・スティックのコード名を表示する
  python3 tools/gamepad_check.py
表示された名前（BTN_TL, ABS_Y など）を config.py に書く。
"""
import evdev
from evdev import ecodes

devs = [evdev.InputDevice(p) for p in evdev.list_devices()]
for i, d in enumerate(devs):
    print(f"[{i}] {d.path}  {d.name}")
if not devs:
    raise SystemExit("入力デバイスが見つかりません（USB/Bluetooth接続と権限を確認）")

idx = int(input("番号を選択 > ") or 0)
dev = devs[idx]
print(f"{dev.name} の入力を表示します（Ctrl+C で終了）")
for ev in dev.read_loop():
    if ev.type == ecodes.EV_KEY:
        name = ecodes.BTN.get(ev.code) or ecodes.KEY.get(ev.code)
        print(f"ボタン {name}  {'押した' if ev.value == 1 else '離した' if ev.value == 0 else 'リピート'}")
    elif ev.type == ecodes.EV_ABS:
        name = ecodes.ABS.get(ev.code)
        print(f"軸    {name}  {ev.value}")
