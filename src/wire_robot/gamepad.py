# -*- coding: utf-8 -*-
"""
ゲームパッド入力（evdev）。別スレッドで読み、切断時は自動で再接続を試みる

PS5 DualSense は Linux 上で「本体」「タッチパッド」「モーションセンサ」の
3デバイスに分かれて見えるので、使うスティック・ボタンを全部持つものだけを選ぶ。

ライトバーは /sys/class/leds/inputN:rgb:indicator に出てくる（hid-playstation ドライバ）。
書き込みには権限が必要（README の udev ルール参照）。失敗しても操縦には影響しない。

通信の生存確認（ウォッチドッグ）
  本体デバイスはスティックやボタンが「変化したとき」しかイベントを出さないため、
  Bluetooth が途切れても最後の値（倒したままのスティック）が残ってしまう。
  カーネルが切断と判定するまで数秒かかることもある。
  そこで、常に流れ続けている「モーションセンサ」デバイスのイベント
  （コントローラが静止していても毎レポート MSC_TIMESTAMP が出る）を受信の証拠とし、
  最後の受信から LINK_TIMEOUT_SEC 経ったら通信途絶とみなす（main 側で全停止）。
"""
import glob
import os
import select
import threading
import time


def link_state(connected, has_motion, last_rx, now, timeout, require_motion=True):
    """
    通信状態を判定する（ハードウェア非依存）
      "ok"           : 動いてよい
      "disconnected" : コントローラが見つからない／切断
      "lost"         : 接続はあるが受信が timeout 秒以上止まっている
      "no_motion"    : モーションセンサが見つからず生存確認できない（require_motion=True のとき停止）
    """
    if not connected:
        return "disconnected"
    if not has_motion:
        return "no_motion" if require_motion else "ok"
    return "ok" if (now - last_rx) <= timeout else "lost"


class Gamepad:
    def __init__(self, cfg):
        import evdev
        from evdev import ecodes
        self.evdev, self.ec = evdev, ecodes
        self.cfg = cfg
        self.lock = threading.Lock()
        self.connected = False
        self.name = ""
        self.dev = None
        self.axes = {}        # code -> -1..1
        self.held = set()     # 押されているボタンのコード
        self.edges = set()    # 押された瞬間（main で消費）
        self.absinfo = {}
        self.led_dir = None
        self._led_cache = None
        self._led_warned = False
        self._rumble_id = None
        self.has_motion = False     # モーションセンサ（生存確認用）を開けているか
        self.motion_name = ""
        self.last_rx = 0.0          # 最後に何かを受信した時刻（time.monotonic）
        self._th = threading.Thread(target=self._run, daemon=True)

    def code(self, name):
        return self.ec.ecodes[name]

    def start(self):
        self._th.start()

    # ---------------- 接続 ----------------
    def _required(self):
        c = self.cfg
        axes = {self.code(c.AXIS_VERTICAL), self.code(c.AXIS_LATERAL)}
        keys = {self.code(c.BTN_ESTOP), self.code(c.BTN_SWITCH_MODE)}
        return axes, keys

    def _find(self):
        need_abs, need_key = self._required()
        for path in self.evdev.list_devices():
            try:
                dev = self.evdev.InputDevice(path)
                caps = dev.capabilities()
            except OSError:
                continue
            if self.cfg.GAMEPAD_NAME and self.cfg.GAMEPAD_NAME not in dev.name:
                continue
            abs_codes = {c for c, _ in caps.get(self.ec.EV_ABS, [])}
            key_codes = set(caps.get(self.ec.EV_KEY, []))
            if need_abs <= abs_codes and need_key <= key_codes:
                return dev
        return None

    def _find_motion(self, main):
        """同じコントローラのモーションセンサデバイスを探す（生存確認に使う）"""
        cands = []
        for path in self.evdev.list_devices():
            if path == main.path:
                continue
            try:
                dev = self.evdev.InputDevice(path)
            except OSError:
                continue
            if "Motion Sensors" in dev.name and (not self.cfg.GAMEPAD_NAME
                                                 or self.cfg.GAMEPAD_NAME in dev.name):
                cands.append(dev)
            else:
                dev.close()
        pick = None
        if main.uniq:                         # 同じ MAC アドレスのものを優先
            pick = next((d for d in cands if d.uniq == main.uniq), None)
        if pick is None and len(cands) == 1:
            pick = cands[0]
        for d in cands:
            if d is not pick:
                d.close()
        return pick

    def _find_led(self, dev):
        """このコントローラのライトバーの sysfs ディレクトリを探す"""
        try:
            ev = os.path.basename(dev.path)                       # eventN
            inp = os.path.basename(os.path.realpath(f"/sys/class/input/{ev}/device"))  # inputN
            d = f"/sys/class/leds/{inp}:rgb:indicator"
            if os.path.isdir(d):
                return d
        except OSError:
            pass
        cands = glob.glob("/sys/class/leds/*:rgb:indicator")
        return cands[0] if len(cands) == 1 else None

    def _norm(self, code, value):
        info = self.absinfo.get(code)
        if info is None:
            return 0.0
        center = (info.max + info.min) / 2.0
        half = (info.max - info.min) / 2.0 or 1.0
        return max(-1.0, min(1.0, (value - center) / half))

    def _clear(self):
        with self.lock:
            self.connected = False
            self.dev = None
            self.led_dir = None
            self._led_cache = None
            self._rumble_id = None
            self.axes.clear()
            self.held.clear()

    def _clear_link(self):
        with self.lock:
            self.has_motion = False
            self.motion_name = ""

    def _handle(self, ev):
        with self.lock:
            if ev.type == self.ec.EV_ABS:
                self.axes[ev.code] = self._norm(ev.code, ev.value)
            elif ev.type == self.ec.EV_KEY:
                if ev.value == 1:
                    self.held.add(ev.code)
                    self.edges.add(ev.code)
                elif ev.value == 0:
                    self.held.discard(ev.code)

    def _run(self):
        while True:
            dev = self._find()
            if dev is None:
                time.sleep(1.0)
                continue
            for code, info in dev.capabilities().get(self.ec.EV_ABS, []):
                self.absinfo[code] = info
            motion = self._find_motion(dev)
            with self.lock:
                self.connected, self.name, self.dev = True, dev.name, dev
                self.led_dir = self._find_led(dev)
                self.has_motion = motion is not None
                self.motion_name = motion.name if motion else ""
                self.last_rx = time.monotonic()
            next_retry = time.monotonic() + 1.0
            try:
                while True:
                    devs = [dev] + ([motion] if motion else [])
                    r, _, _ = select.select(devs, [], [], 0.1)
                    for d in r:
                        try:
                            evs = list(d.read())
                        except BlockingIOError:
                            continue
                        self.last_rx = time.monotonic()   # 受信した＝通信が生きている
                        if d is dev:
                            for ev in evs:
                                self._handle(ev)
                    # モーションセンサが後から現れる場合に備えて探し直す
                    if motion is None and time.monotonic() >= next_retry:
                        next_retry = time.monotonic() + 1.0
                        motion = self._find_motion(dev)
                        if motion is not None:
                            with self.lock:
                                self.has_motion = True
                                self.motion_name = motion.name
                                self.last_rx = time.monotonic()
            except OSError:
                pass  # 切断
            for d in (dev, motion):
                if d is not None:
                    try:
                        d.close()
                    except Exception:
                        pass
            self._clear_link()
            self._clear()
            time.sleep(0.5)

    # ---------------- main から呼ぶ ----------------
    def link(self, now=None):
        """通信状態 "ok" / "lost" / "disconnected" / "no_motion"（link_state を参照）"""
        now = time.monotonic() if now is None else now
        with self.lock:
            c, m = self.connected, self.has_motion
        return link_state(c, m, self.last_rx, now,
                          self.cfg.LINK_TIMEOUT_SEC, self.cfg.LINK_REQUIRE_MOTION)

    def axis(self, name, invert=False):
        with self.lock:
            v = self.axes.get(self.code(name), 0.0)
        return -v if invert else v

    def is_held(self, name):
        with self.lock:
            return self.code(name) in self.held

    def pop_edges(self):
        with self.lock:
            e, self.edges = self.edges, set()
        return e

    def set_color(self, rgb):
        """ライトバーの色を変える（同じ色なら何もしない）"""
        d = self.led_dir
        if not d or rgb == self._led_cache:
            return
        try:
            with open(os.path.join(d, "multi_intensity"), "w") as f:
                f.write(f"{rgb[0]} {rgb[1]} {rgb[2]}")
            with open(os.path.join(d, "brightness"), "w") as f:
                f.write("255")
            self._led_cache = rgb
        except OSError as e:
            if not self._led_warned:
                print(f"\n(ライトバーを変更できません: {e} → README の udev ルールを確認)")
                self._led_warned = True
            self.led_dir = None

    def rumble(self, ms):
        """短く振動させる（失敗しても無視）"""
        dev = self.dev
        if dev is None or ms <= 0:
            return
        try:
            from evdev import ff
            ec = self.ec
            if self._rumble_id is None:
                eff = ff.Effect(
                    ec.FF_RUMBLE, -1, 0,
                    ff.Trigger(0, 0), ff.Replay(ms, 0),
                    ff.EffectType(ff_rumble_effect=ff.Rumble(strong_magnitude=0xA000,
                                                              weak_magnitude=0xA000)))
                self._rumble_id = dev.upload_effect(eff)
            dev.write(ec.EV_FF, self._rumble_id, 1)
        except Exception:
            pass
