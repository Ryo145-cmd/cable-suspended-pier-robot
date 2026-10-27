# 橋脚用ワイヤ吊り下げ式ロボット 制御システム

橋脚・鋼桁の塗膜を IH で加熱しスクレーパで剥がす装置を、上部レールから4本のワイヤで吊って壁面に沿って動かすロボットの制御プログラム（Raspberry Pi 4B / Python3 / PS5 コントローラ / IMU 傾き補正）。

| パス | 内容 |
|---|---|
| `program/wire_robot/` | 制御プログラム。セットアップ・操作は [README](program/wire_robot/README.md) |
| `docs/` | 仕様書 PDF・図・写真・検討メモ |
| `scripts/` | ラズパイ環境構築 `setup_pi.sh`、転送 `deploy.ps1` / `deploy.sh` |
| `notes/` | 記録（現在地・決定・棄てた案・地雷） |
| `CLAUDE.md` | Claude Code 向けの運用規範と安全ルール |

## 使い方（概要）
1. ラズパイに Raspberry Pi OS 64bit Lite を入れ、SSH 鍵認証を設定
2. `scripts/setup_pi.sh` をラズパイで実行 → 再起動
3. PC から `scripts/deploy.ps1 ユーザー名@raspberrypi.local`
4. 試験手順は仕様書第9章と program/wire_robot/README.md
