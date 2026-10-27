# 橋脚用ワイヤ吊り下げ式ロボット 制御システム

橋脚・鋼桁の塗膜を IH で加熱しスクレーパで剥がす装置を、上部レールから4本のワイヤで吊って壁面に沿って動かすロボットの制御プログラム（Raspberry Pi 4B / Python3 / PS5 コントローラ / IMU 傾き補正）。

| パス | 内容 |
|---|---|
| `src/wire_robot/` | 制御プログラム。セットアップ・操作は [README](src/wire_robot/README.md) |
| `docs/` | 仕様書 `SPEC.pdf`・図と写真 `images/`・検討メモ |
| `scripts/` | ラズパイ環境構築 `setup_pi.sh`、反映 `deploy.ps1` / `deploy.sh`（`git push pi main`） |
| `docs/notes/` | 記録（現在地・決定・棄てた案・地雷） |
| `data/` | 実験データ（中身は git 管理外） |
| `CLAUDE.md` | Claude Code 向けの運用規範と安全ルール |

## 使い方（概要）
1. ラズパイに Raspberry Pi OS 64bit Lite を入れ、SSH 鍵認証を設定
2. `scripts/setup_pi.sh` をラズパイで実行 → 再起動
3. PC で `git remote add pi ユーザー名@raspberrypi.local:cable-suspended-pier-robot` → `scripts/deploy.ps1 ユーザー名@raspberrypi.local`
4. 試験手順は仕様書第9章と src/wire_robot/README.md
