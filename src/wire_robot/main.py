#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
橋脚用ワイヤ吊り下げ式ロボット ― PS5コントローラ手動操縦 + IMU傾き補正

  python3 main.py                 実機
  python3 main.py --sim           モータ・IMUをダミーにして動作確認（コントローラは実物）
  python3 main.py --log run.csv   制御ログをCSVに保存（調整用）

スティックを ±0.2 より大きく倒している間だけ動く（離せば停止）。
モード（PSボタンで切り替え、スティックを離した状態で）
  DRIVE : 走行モード（ライトバー青）
          左スティック上下 = 上下移動 / 右スティック左右 = 左右移動
  WIRE  : ワイヤ調整モード（ライトバーオレンジ）
          肩ボタンを1回押すとそのボタンの位置のモータを選択（別のボタンで切り替え）
            L1 = 左上(LL)  R1 = 右上(LR)  L2 = 左下(UL)  R2 = 右下(UR)
          選んだモータだけを左スティック上下で動かす：上 = 巻き取り / 下 = 巻き出し

安全のため、次のあとはスティックが一度中央に戻るまで動かない：
  起動直後 / モード切替 / 非常停止の解除 / コントローラ再接続・通信復帰

通信の生存確認：コントローラからの受信が LINK_TIMEOUT_SEC（0.2秒）途絶えたら全停止
"""
import argparse
import time

import config as C
from controller import SlewLimiter, TiltController
from gamepad import Gamepad
from imu import TiltEstimator, build_imu
from mixer import apply_deadzone, axis_lock, mix, wire_adjust
from motors import build_motors

MOTOR_ORDER = list(C.MOTORS.keys())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", action="store_true", help="モータ・IMUをダミーで動かす")
    ap.add_argument("--log", help="CSVログの保存先")
    args = ap.parse_args()

    motors = build_motors(C, sim=args.sim)
    motors.enable(False)
    imu = build_imu(C, sim=args.sim)
    if args.sim:
        imu.attach(motors)

    est = TiltEstimator(imu, C)
    print("IMU 校正中… 機体を静止させてください")
    est.calibrate(C.IMU_CALIB_SAMPLES)
    print(f"  ジャイロバイアス {est.bias:+.3f} deg/s, 初期傾き {est.angle:+.2f} deg")

    tilt = TiltController(C.TILT_KP, C.TILT_KI, C.TILT_I_LIMIT,
                          C.TILT_MAX_CORRECTION, C.TILT_DEADBAND_DEG)
    slew = {k: SlewLimiter(C.SLEW_RATE) for k in MOTOR_ORDER}

    pad = Gamepad(C)
    pad.start()

    log = open(args.log, "w") if args.log else None
    if log:
        log.write("t,mode,theta,vy,vx,corr,UL,UR,LL,LR,active,link,rx_age\n")

    mode = "DRIVE"
    tilt_on = C.TILT_CORRECTION_DEFAULT_ON
    wire_sel = None             # ワイヤ調整モードで選択中のモータ
    estop = False
    need_center = True          # スティックが中央に戻るまで動かさない
    period = 1.0 / C.LOOP_HZ
    t0 = last = time.monotonic()
    next_status = 0.0
    was_link = None
    LINK_MSG = {
        "ok": "接続",
        "disconnected": "未接続（停止中）",
        "lost": "通信途絶（停止中）",
        "no_motion": "モーションセンサが見つからず生存確認できません（停止中）→ README 参照",
    }

    print("操作: 左スティック上下=上下 / 右スティック左右=左右 | R1高速 | ×非常停止 | OPTIONS解除")
    print("      △傾き補正 | CREATE水平記録 | PSボタン=ワイヤ調整モード（肩ボタン+左スティック上下）")
    try:
        while True:
            now = time.monotonic()
            dt = max(1e-3, now - last)
            last = now

            if args.sim:
                imu.step(dt)
            theta = est.update(dt)

            # ---- スティック ----
            raw_y = pad.axis(C.AXIS_VERTICAL, C.AXIS_VERTICAL_INVERT)
            raw_x = pad.axis(C.AXIS_LATERAL, C.AXIS_LATERAL_INVERT)
            stick_y = apply_deadzone(raw_y, C.STICK_DEADZONE)
            stick_x = apply_deadzone(raw_x, C.STICK_DEADZONE)
            if mode == "WIRE":
                stick_x = 0.0      # ワイヤ調整では左スティック上下だけ使う
            centered = (stick_y == 0.0 and stick_x == 0.0)

            # ---- 接続状態（通信の生存確認を含む） ----
            link = pad.link(now)
            link_ok = (link == "ok")
            if link != was_link:
                msg = LINK_MSG[link]
                if link_ok:
                    msg += f" {pad.name}"
                    if not pad.has_motion:
                        msg += "（生存確認なし）"
                print(f"\nコントローラ: {msg}")
                was_link = link
                need_center = True      # 途絶・復帰のどちらでも、スティックを一度離すまで動かない

            # ---- ボタン（押した瞬間） ----
            edges = pad.pop_edges()
            if pad.code(C.BTN_ESTOP) in edges:
                estop = True
                print("\n!! 非常停止（スティックを離して OPTIONS で解除）")
            if pad.code(C.BTN_RESET) in edges and estop:
                if not centered:
                    print("\nスティックを離してから OPTIONS で解除してください")
                else:
                    estop = False
                    need_center = True
                    print("\n非常停止を解除")
            if pad.code(C.BTN_SWITCH_MODE) in edges:
                if not centered:
                    print("\nスティックを離してからモードを切り替えてください")
                else:
                    mode = "WIRE" if mode == "DRIVE" else "DRIVE"
                    need_center = True
                    pad.rumble(C.RUMBLE_MS)
                    wire_sel = None    # 入るたびに未選択から
                    if mode == "WIRE":
                        print("\n== ワイヤ調整モード ==  L1左上 R1右上 L2左下 R2右下 でモータを選択")
                    else:
                        print("\n== 走行モード ==")
            if mode == "WIRE":
                for b, m in C.WIRE_BUTTONS.items():
                    if pad.code(b) in edges and m != wire_sel:
                        if not centered:
                            print("\nスティックを離してからモータを切り替えてください")
                        else:
                            wire_sel = m
                            pad.rumble(C.SELECT_RUMBLE_MS)
                            print(f"\n選択: {m}（{C.MOTOR_LABELS[m]}）")
            if pad.code(C.BTN_TILT_TOGGLE) in edges:
                tilt_on = not tilt_on
                print(f"\n傾き補正: {'ON' if tilt_on else 'OFF'}")
            if pad.code(C.BTN_LEVEL_ZERO) in edges and centered:
                est.set_zero()
                theta = 0.0
                print("\n現在の姿勢を水平として記録")

            if need_center and centered:
                need_center = False

            # ---- 指令の計算 ----
            selected = {wire_sel} if (mode == "WIRE" and wire_sel) else set()
            ready = link_ok and not estop and not need_center
            active = ready and not centered and (mode == "DRIVE" or bool(selected))
            fast = pad.is_held(C.BTN_FAST) if link_ok else False
            vy = vx = corr = 0.0
            if active:
                if mode == "DRIVE":
                    vy, vx = stick_y, stick_x
                    if C.AXIS_LOCK:
                        vy, vx = axis_lock(vy, vx)
                    scale = C.MAX_DUTY * (1.0 if fast else C.LOW_SPEED_SCALE)
                    vy, vx = vy * scale, vx * scale
                    if abs(theta) > C.TILT_LIMIT_DEG:
                        vy = vx = 0.0   # 傾きすぎ：移動は止めて補正だけ（スティックを倒している間）
                    if tilt_on:
                        corr = tilt.update(theta, dt)
                    else:
                        tilt.reset()
                    target = mix(vy, vx, corr, C.LATERAL_SIGN)
                else:  # WIRE：選択中のモータだけ。傾き補正はしない
                    tilt.reset()
                    vy = stick_y * C.WIRE_ADJUST_SCALE
                    target = wire_adjust(selected, vy, MOTOR_ORDER)
                cmd = {k: slew[k].step(v, dt) for k, v in target.items()}
                motors.enable(True)
                motors.set(cmd)
            else:
                tilt.reset()
                for s in slew.values():
                    s.reset()
                motors.stop_all()
                motors.enable(False)

            # ---- ライトバー ----
            if estop:
                color = C.COLOR_ESTOP
            else:
                color = C.COLOR_DRIVE if mode == "DRIVE" else C.COLOR_WIRE
                if need_center and int(now / C.BLINK_SEC) % 2:
                    color = (0, 0, 0)          # 中央に戻るのを待つ間は点滅
            pad.set_color(color)

            # ---- 表示・ログ ----
            L = motors.last
            if log:
                log.write(f"{now - t0:.3f},{mode},{theta:.3f},{vy:.3f},{vx:.3f},{corr:.3f},"
                          f"{L['UL']:.3f},{L['UR']:.3f},{L['LL']:.3f},{L['LR']:.3f},{int(active)},"
                          f"{link},{now - pad.last_rx:.3f}\n")
            if now >= next_status:
                next_status = now + 1.0 / C.STATUS_HZ
                if estop:
                    state = "非常停止"
                elif link == "lost":
                    state = "通信途絶"
                elif not link_ok:
                    state = "未接続"
                elif need_center:
                    state = "スティックを離して"
                else:
                    state = "動作中" if active else "待機"
                warn = " 傾き過大!" if abs(theta) > C.TILT_LIMIT_DEG else ""
                if mode == "DRIVE":
                    head = f"[走行 {state}] 補正{'ON ' if tilt_on else 'OFF'}"
                else:
                    sel_txt = ",".join(k for k in MOTOR_ORDER if k in selected) or "-"
                    head = f"[ワイヤ {state}] 選択:{sel_txt}"
                print(f"\r{head} θ={theta:+6.2f}° "
                      f"UL{L['UL']:+.2f} UR{L['UR']:+.2f} LL{L['LL']:+.2f} LR{L['LR']:+.2f}{warn}   ",
                      end="", flush=True)

            time.sleep(max(0.0, period - (time.monotonic() - now)))
    except KeyboardInterrupt:
        print("\n終了します")
    finally:
        motors.stop_all()
        motors.close()
        imu.close()
        if log:
            log.close()


if __name__ == "__main__":
    main()
