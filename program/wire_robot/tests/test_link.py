# -*- coding: utf-8 -*-
"""
通信の生存確認（ウォッチドッグ）のテスト。evdev をダミーに差し替えるのでハード不要
  python3 -m pytest tests   （または python3 tests/test_link.py）
"""
import os
import sys
import time
import types
from collections import namedtuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C
from gamepad import link_state

# ---------------- 判定ロジック ----------------


def test_link_state_basic():
    assert link_state(False, True, 0.0, 10.0, 0.2) == "disconnected"
    assert link_state(True, True, 9.9, 10.0, 0.2) == "ok"
    assert link_state(True, True, 9.7, 10.0, 0.2) == "lost"
    assert link_state(True, False, 0.0, 10.0, 0.2, require_motion=True) == "no_motion"
    assert link_state(True, False, 0.0, 10.0, 0.2, require_motion=False) == "ok"


# ---------------- ダミー evdev（パイプでイベントを流す） ----------------

Ev = namedtuple("Ev", "type code value")
AbsInfo = namedtuple("AbsInfo", "value min max fuzz flat resolution")
EV_KEY, EV_ABS, EV_MSC = 1, 3, 4
CODES = {"ABS_Y": 1, "ABS_RX": 3, "BTN_SOUTH": 304, "BTN_NORTH": 307, "BTN_TL": 310,
         "BTN_TR": 311, "BTN_TL2": 312, "BTN_TR2": 313, "BTN_SELECT": 314,
         "BTN_START": 315, "BTN_MODE": 316}


class FakeDev:
    def __init__(self, path, name, uniq, caps):
        self.path, self.name, self.uniq, self._caps = path, name, uniq, caps
        self.r, self.w = os.pipe()
        os.set_blocking(self.r, False)
        self.queue = []
        self.gone = False

    def capabilities(self):
        return self._caps

    def fileno(self):
        return self.r

    def push(self, *evs):
        self.queue.extend(evs)
        os.write(self.w, b"x")

    def unplug(self):
        self.gone = True
        os.write(self.w, b"x")

    def read(self):
        if self.gone:
            raise OSError(19, "No such device")
        try:
            os.read(self.r, 4096)
        except BlockingIOError:
            raise
        evs, self.queue = self.queue, []
        return iter(evs)

    def close(self):
        pass


def make_fake_evdev(devices):
    ecodes = types.SimpleNamespace(EV_KEY=EV_KEY, EV_ABS=EV_ABS, EV_MSC=EV_MSC, ecodes=CODES)
    mod = types.ModuleType("evdev")
    mod.ecodes = ecodes
    mod.list_devices = lambda: [d.path for d in devices if not d.gone]
    by_path = {d.path: d for d in devices}

    def InputDevice(path):
        d = by_path[path]
        if d.gone:
            raise OSError(19, "No such device")
        return d
    mod.InputDevice = InputDevice
    return mod


def make_pad(with_motion=True):
    ai = AbsInfo(128, 0, 255, 0, 0, 0)
    main = FakeDev("/dev/input/event5", "DualSense Wireless Controller", "aa:bb",
                   {EV_ABS: [(1, ai), (3, ai)], EV_KEY: [304, 316, 311]})
    devs = [main]
    motion = None
    if with_motion:
        motion = FakeDev("/dev/input/event6", "DualSense Wireless Controller Motion Sensors",
                         "aa:bb", {EV_ABS: [(0, ai)]})
        devs.append(motion)
    sys.modules["evdev"] = make_fake_evdev(devs)
    sys.modules["evdev"].ecodes = sys.modules["evdev"].ecodes
    sys.modules["evdev.ecodes"] = sys.modules["evdev"].ecodes
    import importlib
    import gamepad
    importlib.reload(gamepad)
    pad = gamepad.Gamepad(C)
    pad.start()
    return pad, main, motion


def wait_for(cond, timeout=2.0):
    t = time.monotonic() + timeout
    while time.monotonic() < t:
        if cond():
            return True
        time.sleep(0.005)
    return False


def test_watchdog_stops_when_stream_stops():
    """モーションセンサの受信が止まると 0.2 秒で lost、再開で ok に戻る"""
    pad, main, motion = make_pad()
    assert wait_for(lambda: pad.connected and pad.has_motion)
    # スティックを上に倒したまま…
    main.push(Ev(EV_ABS, 1, 0))
    for _ in range(20):                          # 約 4ms 間隔で受信が続く
        motion.push(Ev(EV_MSC, 5, 0))
        time.sleep(0.004)
    assert pad.link() == "ok"
    assert pad.axis("ABS_Y") < -0.9              # 倒したままの値が残っている
    # ここで電波が途切れた（以後イベントなし）
    t_cut = time.monotonic()
    assert wait_for(lambda: pad.link() == "lost", 1.0)
    elapsed = time.monotonic() - t_cut
    assert C.LINK_TIMEOUT_SEC - 0.01 <= elapsed <= C.LINK_TIMEOUT_SEC + 0.1, elapsed
    # 復帰
    motion.push(Ev(EV_MSC, 5, 0))
    assert wait_for(lambda: pad.link() == "ok", 0.5)


def test_unplug_becomes_disconnected():
    pad, main, motion = make_pad()
    assert wait_for(lambda: pad.link() == "ok")
    motion.unplug()
    main.unplug()
    assert wait_for(lambda: pad.link() == "disconnected", 1.0)
    assert pad.axis("ABS_Y") == 0.0              # 古い値は消える


def test_no_motion_device_refuses():
    pad, main, _ = make_pad(with_motion=False)
    assert wait_for(lambda: pad.connected)
    assert pad.link() == "no_motion"             # LINK_REQUIRE_MOTION=True なので動かさない


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
