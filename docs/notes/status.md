# 現在地（最終更新 2026-10-27）

## 動いているもの
- 制御プログラム一式（src/wire_robot/）。ハードなしのテスト（tests/test_logic.py, tests/test_link.py）は全部通る
- `main.py --sim` で結合確認済み：通信途絶（受信停止）から全モータ停止まで 0.207 秒
- 実機では一度も動かしていない

## 進行中
- ラズパイの環境構築（Raspberry Pi OS 64bit Lite）。`scripts/setup_pi.sh` → 再起動 → `scripts/deploy.ps1`（中身は `git push pi main`。PC に remote pi は追加済み）
- Claude Code（ユーザーの Windows PC）から SSH で作業する体制に移行中。SSH 鍵認証の設定がまだなら最初にやる
- 2026-10-27：リポジトリは PC の `~/cable-suspended-pier-robot`、構成は wall-climbing-robot-mecanum に揃えた。origin=GitHub(Ryo145-cmd/cable-suspended-pier-robot)、main を push 済み
- 2026-10-27：ラズパイが手元になく SSH 未確認（raspberrypi.local の名前解決不可）。PC に鍵 ~/.ssh/id_ed25519 あり、known_hosts に Pi なし。接続先 ryosuke@raspberrypi.local、PI_HOST 未設定
  → Pi が来たら：鍵登録 → PI_HOST 設定 → setup_pi.sh（受け取り用リポジトリも作る）→ 再起動 → deploy.ps1（push pi＋テスト）
  → PC 上で確認済み（2026-10-27）：空のリポジトリへの最初の push で作業ツリーが展開される／作業ツリーに変更があると push は "Working directory has unstaged changes" で拒否される

## 次の一手
1. ラズパイで `tools/gamepad_check.py` → `tools/link_check.py`（Motion Sensors が見つかるか、受信の最大間隔）
2. 仕様書第9章の空転試験（ワイヤなし）。手順5（安全）に「コントローラ電源OFFで約0.2秒で停止」を追加して確認
3. 空転試験で invert / LATERAL_SIGN / IMU_AXIS_* の符号を確定し、decisions.md に記録

## 未確認・推定
- ドラム配置（上段=左右プーリ、下段=上下プーリ）→ 違えば WIRE_BUTTONS
- 左右移動の向き LATERAL_SIGN、各モータの invert、IMU_AXIS_* の符号
- モータ電流（概算：通常1〜2A/台、ロック4〜6A/台）
- IHヘッドの位置、下部シリンダの役割
- 実機で DualSense のモーションセンサが見つかるか、普段の最大受信間隔
- レール固定マグネット：配置、吊り荷重合計、試験体の膜厚（docs/magnet_rail.md）

## 未実装・課題
- R_IS＋ADCで過電流停止、ENにハードウェアウォッチドッグ（Pi フリーズ時は今は止まらない）、systemd 自動起動、リポアラーム
- IHノイズ対策：基板を載せる板をアルミ板に（1.5〜2mm、GND1点接続、スペーサー）
- 仕様書PDFに通信途絶の停止が未反映（README には記載済み）
- レール固定方法の見直し（docs/magnet_rail.md）
