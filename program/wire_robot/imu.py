# -*- coding: utf-8 -*-
"""IMU（MPU6050）と傾き推定（相補フィルタ）"""
import math
import time


class MPU6050:
    def __init__(self, bus=1, addr=0x68):
        from smbus2 import SMBus
        self.bus = SMBus(bus)
        self.addr = addr
        self.bus.write_byte_data(addr, 0x6B, 0x00)  # スリープ解除
        self.bus.write_byte_data(addr, 0x1A, 0x03)  # DLPF 44Hz
        self.bus.write_byte_data(addr, 0x1B, 0x00)  # ジャイロ ±250dps
        self.bus.write_byte_data(addr, 0x1C, 0x00)  # 加速度 ±2g
        time.sleep(0.05)

    @staticmethod
    def _s16(h, l):
        v = (h << 8) | l
        return v - 65536 if v >= 32768 else v

    def read(self):
        """戻り値: accel{x,y,z}[g], gyro{x,y,z}[deg/s]"""
        d = self.bus.read_i2c_block_data(self.addr, 0x3B, 14)
        ax, ay, az = (self._s16(d[i], d[i + 1]) / 16384.0 for i in (0, 2, 4))
        gx, gy, gz = (self._s16(d[i], d[i + 1]) / 131.0 for i in (8, 10, 12))
        return {"x": ax, "y": ay, "z": az}, {"x": gx, "y": gy, "z": gz}

    def close(self):
        self.bus.close()


class SimIMU:
    """シミュレーション用。モータの差動で傾きが変わる簡易モデル"""

    def __init__(self, initial_tilt=3.0):
        self.theta = initial_tilt
        self.rate = 0.0
        self.motors = None

    def attach(self, motorset):
        self.motors = motorset

    def step(self, dt):
        if self.motors:
            last = self.motors.last
            # 右の外側を巻き取る（UR > UL）と右が上がる → θ減少
            self.rate = -40.0 * (last["UR"] - last["UL"])
        self.theta += self.rate * dt

    def read(self):
        t = math.radians(self.theta)
        return ({"x": -math.sin(t), "y": math.cos(t), "z": 0.0},
                {"x": 0.0, "y": 0.0, "z": self.rate})

    def close(self):
        pass


def _pick(vec, spec):
    s = -1.0 if spec[0] == "-" else 1.0
    return s * vec[spec[-1]]


class TiltEstimator:
    def __init__(self, imu, cfg):
        self.imu = imu
        self.cfg = cfg
        self.alpha = cfg.COMPLEMENTARY_ALPHA
        self.bias = 0.0
        self.zero = 0.0
        self.angle = 0.0
        self.raw_rate = 0.0

    def _accel_angle(self, a):
        r = _pick(a, self.cfg.IMU_AXIS_RIGHT)
        u = _pick(a, self.cfg.IMU_AXIS_UP)
        # 右側が下がる(θ>0)と、上向き重力反力の「右」成分が負になる
        return math.degrees(math.atan2(-r, u))

    def calibrate(self, n):
        gs, angs = 0.0, 0.0
        for _ in range(n):
            a, g = self.imu.read()
            gs += _pick(g, self.cfg.IMU_AXIS_NORMAL)
            angs += self._accel_angle(a)
            time.sleep(0.005)
        self.bias = gs / n
        self.angle = angs / n

    def update(self, dt):
        a, g = self.imu.read()
        self.raw_rate = _pick(g, self.cfg.IMU_AXIS_NORMAL) - self.bias
        acc = self._accel_angle(a)
        self.angle = self.alpha * (self.angle + self.raw_rate * dt) + (1 - self.alpha) * acc
        return self.angle - self.zero

    def set_zero(self):
        self.zero = self.angle


def build_imu(cfg, sim=False):
    if sim:
        return SimIMU()
    if cfg.IMU_TYPE == "mpu6050":
        return MPU6050(cfg.IMU_I2C_BUS, cfg.IMU_I2C_ADDR)
    raise ValueError(f"不明な IMU_TYPE: {cfg.IMU_TYPE}")
