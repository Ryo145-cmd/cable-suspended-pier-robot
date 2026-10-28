# 現在地（最終更新 2026-10-27）

## 動いているもの
- 制御プログラム一式（src/wire_robot/）。ハードなしのテスト（tests/test_logic.py, tests/test_link.py）は全部通る
- `main.py --sim` で結合確認済み：通信途絶（受信停止）から全モータ停止まで 0.207 秒
- 実機では一度も動かしていない

## 進行中
- ラズパイの環境構築（既存の Raspberry Pi OS デスクトップ版 trixie をそのまま使う）。`scripts/setup_pi.sh` → 再起動 → `scripts/deploy.ps1`（中身は `git push pi main`。PC に remote pi は追加済み）
- 2026-10-27：リポジトリは PC の `~/cable-suspended-pier-robot`、構成は wall-climbing-robot-mecanum に揃えた。origin=GitHub(Ryo145-cmd/cable-suspended-pier-robot)、main を push 済み
- 2026-10-27：SSH 鍵認証 設定済み（`ssh wire-pi`）。PI_HOST=wire-pi（ユーザー環境変数）。sudo はパスワード要
- 2026-10-27：DualSense を入れ替え。旧 D4:2F:4B:50:E5:70 の登録を削除、新 34:6F:3F:7E:A8:FC をペアリング・信頼・接続済み（bluetoothctl）
- 2026-10-27：setup_pi.sh 実行済み → 再起動 → deploy.ps1（push pi）で反映。Pi 上で tests 12 件すべて OK（Python 3.13.5）。IBT-2・IMU は未接続
- 2026-10-27：link_check（机上・静止・近距離、8 秒）：Motion Sensors で生存確認 ok、受信 378〜766 回/秒、最大間隔 10.7〜28.7 ms（しきい値 200 ms に対し十分小さい）。作業距離での確認・gamepad_check は未実施
- 2026-10-27：link_check で電源 OFF（PS 長押し）を確認：18:53:32 に lost を経ずに直接 disconnected（コントローラが正規に切断を送るため即時に切断扱い）。main.py は link != "ok" で停止なので停止する。直前まで最大間隔 13〜33 ms
  - 未確認：切断を送らない電波断（遠ざかる、金属で覆う）での lost（0.2 秒タイムアウト）経路
- 2026-10-27：ユーザーが Pi で `main.py --sim`（実コントローラ＋ダミーのモータ・IMU）を操作し「動いてそう」。項目ごと（中央復帰待ち・非常停止ラッチ・ワイヤ調整・傾き補正・ライトバー色）の合否は未記録
  → PC 上で確認済み（2026-10-27）：空のリポジトリへの最初の push で作業ツリーが展開される／作業ツリーに変更があると push は "Working directory has unstaged changes" で拒否される

## 次の一手（2026-10-27 終了時点）
1. `main.py --sim` の安全項目を個別に確認して記録：起動時の中央復帰待ち、非常停止ラッチ（倒したまま OPTIONS で解除されない）、動作中の電源 OFF で停止、ライトバー色
2. 電波断（遠ざかる／金属で覆う）で link_check が lost＋約 0.2 秒を出すか
3. IMU（MPU6050）を接続 → `i2cdetect -y 1` で 0x68 → `tools/imu_check.py`
4. IBT-2 を接続し、仕様書第9章の空転試験（ワイヤなし。モータを回すのでユーザーが実行）
5. 空転試験で invert / LATERAL_SIGN / IMU_AXIS_* の符号を確定し、decisions.md に記録

## 未確認・推定
- ドラム配置（上段=左右プーリ、下段=上下プーリ）→ 違えば WIRE_BUTTONS
- 左右移動の向き LATERAL_SIGN、各モータの invert、IMU_AXIS_* の符号
- モータ電流（概算：通常1〜2A/台、ロック4〜6A/台）
- IHヘッドの位置、下部シリンダの役割
- 実機で DualSense のモーションセンサが見つかるか、普段の最大受信間隔 → 2026-10-27 机上で確認済み（見つかる、最大 28.7 ms）。作業距離では未確認
- レール固定マグネット：配置、吊り荷重合計、試験体の膜厚（docs/magnet_rail.md）

## 未実装・課題
- R_IS＋ADCで過電流停止、ENにハードウェアウォッチドッグ（Pi フリーズ時は今は止まらない）、systemd 自動起動、リポアラーム
- IHノイズ対策：2026-10-28 制御回路を電装ボックスに収めると決定（decisions.md）。材質・収める範囲・Bluetooth の出し方は未定。以前の案：基板を載せる板をアルミ板に（1.5〜2mm、GND1点接続、スペーサー）
- 仕様書PDFに通信途絶の停止が未反映（README には記載済み）
- レール固定方法の見直し（docs/magnet_rail.md）
