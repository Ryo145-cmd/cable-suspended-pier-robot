#!/usr/bin/env bash
# DualSense をペアリングし直す（ラズパイ上で実行）
#   bash ~/cable-suspended-pier-robot/scripts/pair_controller.sh
# PC からは: ssh wire-pi "bash ~/cable-suspended-pier-robot/scripts/pair_controller.sh"
# 実行したら 2 分以内にコントローラの PS＋クリエイトを長押し（ライトが速く点滅したら離す）
# 同じコントローラを別の機器（メカナムの Pi・PS5・PC など）につなぐと鍵が上書きされ、
# PS ボタンだけでは再接続できなくなる。そのときに使う
for m in $(bluetoothctl devices | grep -i 'DualSense' | awk '{print $2}'); do
    bluetoothctl remove "$m"
done
bluetoothctl --timeout 120 scan on >/dev/null 2>&1 &
SCAN=$!
NEW=""
for i in $(seq 1 60); do
    NEW=$(bluetoothctl devices | grep -i 'DualSense' | awk '{print $2}' | head -1)
    [ -n "$NEW" ] && break
    sleep 2
done
if [ -z "$NEW" ]; then
    kill $SCAN 2>/dev/null
    echo "NOT_FOUND: 2分以内に DualSense が見つかりませんでした"
    exit 1
fi
echo "FOUND $NEW"
# デスクトップ版では "Failed to register agent object" が出るが、ペアリングは成功する
LOG=$(mktemp)
{ echo "agent NoInputNoOutput"; echo "default-agent"; echo "pair $NEW"; sleep 10
  echo "trust $NEW"; sleep 1; echo "connect $NEW"; sleep 6; echo "quit"; } | bluetoothctl >"$LOG" 2>&1
kill $SCAN 2>/dev/null
grep -E 'Pairing successful|Failed|trust succeeded|Connection successful|Error' "$LOG"
rm -f "$LOG"
echo "--- info"
bluetoothctl info "$NEW" | grep -E 'Name|Paired|Bonded|Trusted|Connected'
