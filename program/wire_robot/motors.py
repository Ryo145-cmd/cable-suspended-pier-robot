# -*- coding: utf-8 -*-
"""モータドライバ（gpiozero）。--sim のときはダミーを使う"""
from mixer import clamp


def shape_duty(v, min_duty):
    """回り始めのデューティを底上げ"""
    if abs(v) < 1e-3:
        return 0.0
    s = 1.0 if v > 0 else -1.0
    return s * (min_duty + (1.0 - min_duty) * abs(v))


class Ibt2Motor:
    """IBT-2 (BTS7960)：RPWM / LPWM の片側だけにPWMを出す。+指令で RPWM"""

    def __init__(self, rpwm, lpwm, invert, freq, **_):
        from gpiozero import PWMOutputDevice
        self.r = PWMOutputDevice(rpwm, frequency=freq, initial_value=0)
        self.l = PWMOutputDevice(lpwm, frequency=freq, initial_value=0)
        self.invert = invert

    def set(self, v):
        v = clamp(-v if self.invert else v, -1.0, 1.0)
        if v >= 0:
            self.l.value = 0.0   # 先に反対側を落とす（上下アームの同時ONを避ける）
            self.r.value = v
        else:
            self.r.value = 0.0
            self.l.value = -v

    def stop(self):
        self.r.value = 0.0
        self.l.value = 0.0

    def close(self):
        self.stop()
        self.r.close()
        self.l.close()


class PwmDirMotor:
    def __init__(self, pwm, dir, invert, freq, **_):
        from gpiozero import PWMOutputDevice, DigitalOutputDevice
        self.pwm = PWMOutputDevice(pwm, frequency=freq)
        self.dir = DigitalOutputDevice(dir)
        self.invert = invert

    def set(self, v):
        v = clamp(-v if self.invert else v, -1.0, 1.0)
        self.dir.value = 1 if v >= 0 else 0
        self.pwm.value = abs(v)

    def stop(self):
        self.pwm.value = 0.0

    def close(self):
        self.stop()
        self.pwm.close()
        self.dir.close()


class InInMotor:
    def __init__(self, in1, in2, invert, freq, **_):
        from gpiozero import Motor
        self.m = Motor(forward=in1, backward=in2, pwm=True)
        self.m.forward_device.frequency = freq
        self.m.backward_device.frequency = freq
        self.invert = invert

    def set(self, v):
        v = clamp(-v if self.invert else v, -1.0, 1.0)
        self.m.value = v

    def stop(self):
        self.m.stop()

    def close(self):
        self.m.stop()
        self.m.close()


class SimMotor:
    def __init__(self, name, **_):
        self.name = name
        self.value = 0.0

    def set(self, v):
        self.value = clamp(v, -1.0, 1.0)

    def stop(self):
        self.value = 0.0

    def close(self):
        self.stop()


class MotorSet:
    def __init__(self, motors, min_duty, enable_pin=None):
        self.motors = motors
        self.min_duty = min_duty
        self.last = {k: 0.0 for k in motors}
        self.en = None
        if enable_pin is not None:
            from gpiozero import DigitalOutputDevice
            self.en = DigitalOutputDevice(enable_pin, initial_value=False)

    def enable(self, on):
        """全ドライバの EN（R_EN/L_EN）を入り切り。OFF でブリッジが切れる"""
        if self.en is not None:
            self.en.value = 1 if on else 0

    def set(self, cmd):
        for k, m in self.motors.items():
            v = shape_duty(cmd.get(k, 0.0), self.min_duty)
            m.set(v)
            self.last[k] = v

    def stop_all(self):
        for k, m in self.motors.items():
            m.stop()
            self.last[k] = 0.0

    def close(self):
        self.stop_all()
        self.enable(False)
        for m in self.motors.values():
            try:
                m.close()
            except Exception:
                pass
        if self.en is not None:
            self.en.close()


def build_motors(cfg, sim=False):
    motors = {}
    mode = cfg.MOTOR_DRIVER_MODE
    cls = {"ibt2": Ibt2Motor, "pwm_dir": PwmDirMotor, "in1_in2": InInMotor}.get(mode)
    if cls is None and not sim:
        raise ValueError(f"不明な MOTOR_DRIVER_MODE: {mode}")
    for name, p in cfg.MOTORS.items():
        motors[name] = SimMotor(name) if sim else cls(freq=cfg.PWM_FREQUENCY, **p)
    en = None if sim else getattr(cfg, "ENABLE_PIN", None)
    return MotorSet(motors, cfg.MIN_DUTY, en)
