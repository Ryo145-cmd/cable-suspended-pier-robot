#!/usr/bin/env bash
# PC(Linux/WSL/Git Bash) → ラズパイへプログラムを転送する
#   scripts/deploy.sh pi@raspberrypi.local            （config.py は上書きしない）
#   scripts/deploy.sh pi@raspberrypi.local --config   （config.py も上書きする）
# 環境変数 PI_HOST があれば接続先は省略可。SSH は鍵認証を設定しておくこと
set -euo pipefail
HOST="${1:-${PI_HOST:-}}"
[ -n "$HOST" ] || { echo "接続先を指定してください（例: pi@raspberrypi.local）"; exit 1; }
WITH_CONFIG=0
[ "${2:-}" = "--config" ] && WITH_CONFIG=1

SRC="$(cd "$(dirname "$0")/../src/wire_robot" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp -r "$SRC/." "$TMP/"
find "$TMP" -name __pycache__ -prune -exec rm -rf {} +

ssh "$HOST" "mkdir -p ~/wire_robot"
if [ $WITH_CONFIG -eq 0 ] && ssh "$HOST" "test -f ~/wire_robot/config.py"; then
    rm "$TMP/config.py"
    echo "config.py はラズパイ側のものを残します（上書きするなら --config）"
fi
tar -C "$TMP" -cf - . | ssh "$HOST" "tar -C ~/wire_robot -xf -"
ssh "$HOST" "cd ~/wire_robot && python3 tests/test_logic.py && python3 tests/test_link.py"
echo "転送完了: $HOST:~/wire_robot/"
