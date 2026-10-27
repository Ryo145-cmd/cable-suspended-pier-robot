#!/usr/bin/env bash
# PC(Linux/WSL/Git Bash) → ラズパイへ反映する（git push pi main → ラズパイでテスト）
#   scripts/deploy.sh                            （PI_HOST を使う）
#   scripts/deploy.sh ryosuke@raspberrypi.local
# 前提：ラズパイで setup_pi.sh 済み、PC に remote "pi" がある
# ラズパイ側に未コミットの変更（現場で書き換えた config.py など）があると push は拒否される。
# そのときは表示される git diff を確認してから対処する（勝手に捨てない）
set -euo pipefail
HOST="${1:-${PI_HOST:-}}"
[ -n "$HOST" ] || { echo "接続先を指定してください（例: ryosuke@raspberrypi.local）"; exit 1; }
REPO="~/cable-suspended-pier-robot"

if ! git -C "$(dirname "$0")/.." push pi main; then
    echo "push が拒否されました。ラズパイ側の変更："
    ssh "$HOST" "cd $REPO && git status --short && git diff"
    exit 1
fi
ssh "$HOST" "cd $REPO/src/wire_robot && python3 tests/test_logic.py && python3 tests/test_link.py"
echo "反映完了: $HOST:$REPO（~/wire_robot はここの src/wire_robot へのリンク）"
