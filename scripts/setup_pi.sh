#!/usr/bin/env bash
# ラズパイの環境構築（Raspberry Pi OS 64bit Lite 上で実行。何度実行してもよい）
#   bash setup_pi.sh
# 終わったら再起動（グループ設定の反映のため）
set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
    echo "sudo を付けずに、普段のユーザーで実行してください"; exit 1
fi

echo "== パッケージ =="
sudo apt-get update
sudo apt-get install -y python3-gpiozero python3-lgpio python3-evdev python3-smbus2 \
    i2c-tools bluez git

echo "== I2C を有効化 =="
sudo raspi-config nonint do_i2c 0

echo "== グループ（sudo なしで GPIO・入力・I2C を使う） =="
sudo usermod -aG input,gpio,i2c "$USER"

echo "== ライトバー用 udev ルール =="
sudo tee /etc/udev/rules.d/99-dualsense-led.rules >/dev/null <<'RULE'
ACTION=="add", SUBSYSTEM=="leds", KERNEL=="*:rgb:indicator", RUN+="/bin/chgrp input /sys%p/brightness /sys%p/multi_intensity", RUN+="/bin/chmod g+w /sys%p/brightness /sys%p/multi_intensity"
RULE
sudo udevadm control --reload-rules

echo "== ハードなしのテスト =="
DIR="$HOME/wire_robot"
if [ -d "$DIR" ]; then
    (cd "$DIR" && python3 tests/test_logic.py && python3 tests/test_link.py)
else
    echo "($DIR がまだありません。deploy 後に tests を実行してください)"
fi

echo "== 情報 =="
uname -r
python3 --version
echo
echo "完了。sudo reboot で再起動してください。"
echo "再起動後：i2cdetect -y 1 で 0x68、bluetoothctl でコントローラをペアリング（README 参照）"
