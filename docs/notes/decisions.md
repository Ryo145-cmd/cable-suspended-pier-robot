# 決めたことと理由（追記のみ。過去は書き換えない）

## 2026-10-27 以前（仕様書 v1.0 時点）
- ハード：Raspberry Pi 4B / IBT-2(BTS7960)×4 / 12V ウォームギアモータ×4（エンコーダなし）/ MPU6050 / PS5 DualSense
  - ウォームギア：停止中に電流なしで保持できるため
- IBT-2 の VCC は 3.3V：入力バッファ 74HC244 を 5V で動かすと H 判定が 3.5V 以上になり、Pi の 3.3V 出力では不安定
- EN（R_EN+L_EN 4台共通）を GPIO26 で制御：起動直後プルダウンで、プログラムが動くまでモータが回らない。将来ウォッチドッグ回路を入れられる
- 電源2系統：DCブレーカー15A→IBT-2（ブレーカー＝物理非常停止）／トグルSW→DCDC 5V3A→ラズパイ
- 操作：押しっぱなしボタンなし。スティック ±0.2 超で動き、離すと停止
- 起動・モード切替・非常停止解除・再接続後は、スティックが一度中央に戻るまで動かない（倒しっぱなしでの急発進防止）
- 傾き補正は外側（上下プーリ UL/UR）の差動で行う。左右移動は内側（LL/LR）の逆回転
- 停止は即時、加速だけ SLEW_RATE で制限
- ワイヤ調整モード：肩ボタンの位置＝ドラムの位置（L1左上LL、R1右上LR、L2左下UL、R2右下UR）、1回押して選択

## 2026-10-27
- Bluetooth 通信途絶で 0.2 秒停止（LINK_TIMEOUT_SEC=0.2）
  - 理由：本体デバイスは変化時しかイベントを出さず、電波断でも最後のスティック値が残る。カーネルの切断判定は数秒かかることがある
  - 方法：DualSense の「Motion Sensors」デバイスは静止中も毎レポートイベントを出すので、その受信時刻を生存確認に使う
  - 途絶・復帰とも need_center（スティックを一度離すまで動かない）
- モーションセンサが見つからなければ動かさない（LINK_REQUIRE_MOTION=True）：生存確認できない状態で動かすより安全側
- deploy スクリプトは既定で config.py を上書きしない：現場で調整した値を消さないため
- 開発体制：ユーザーの Windows PC の Claude Code から SSH（鍵認証）でラズパイを操作。GitHub で管理
- モータを回すコマンドは Claude Code が勝手に実行しない（CLAUDE.md 安全ルール）
- リポジトリ構成を wall-climbing-robot-mecanum に揃える（ユーザー指示）
  - notes/ → docs/notes/（current.md → status.md）、program/wire_robot/ → src/wire_robot/、docs/wire_robot_spec.pdf → docs/SPEC.pdf、
    図・写真（docs/figs/、docs/*.png）→ docs/images/、実験データ用に data/（中身は git 管理外）
  - scripts/（setup_pi.sh, deploy.*）は mecanum に無いが、ROS なしの本機では転送・構築に必要なので残す
  - ラズパイ側の配置先 ~/wire_robot/ は変えない
- ラズパイへの反映を mecanum と同じ `git push pi main` 方式に変更（scp+tar 方式をやめる。ユーザー承認）
  - ラズパイ側：`~/cable-suspended-pier-robot` を `git init -b main` し `receive.denyCurrentBranch=updateInstead`（setup_pi.sh で作る）。GitHub の認証は入れない
  - `~/wire_robot` はそこから `src/wire_robot` へのシンボリックリンクにする（README・仕様書の `~/wire_robot` の記述をそのまま使えるように）
  - config.py の保護：ラズパイの作業ツリーに変更があると updateInstead が push を拒否する。拒否されたら `git diff` を見てユーザーに聞く（勝手に捨てない）
  - 理由：手順を mecanum と1本化、ラズパイ上のコードがどのコミットか git で分かる。得失はユーザーに提示済み
  - deploy.ps1 / deploy.sh は消さず「push pi → ラズパイでテスト」の薄いラッパーに書き換え
- ラズパイの OS は既存の Raspberry Pi OS デスクトップ版（Debian 13 trixie, aarch64, Python 3.13.5）をそのまま使う（Lite に入れ直さない）
  - 理由：既存ファイル（Dynamixel_tutorial, venv, test）を消さずに済む。メモリ 3.8GB 中 使用 338MB で余裕。必要パッケージは全て apt にあり、ryosuke は gpio/i2c/input 所属済み
  - 欠点：起動が遅い、デスクトップの Bluetooth 管理と競合しうる（ペアリングは bluetoothctl で）、Python 3.13 は未検証（Pi 上のテストで確認）
- PC からの接続名は SSH config の別名 `wire-pi`（ryosuke@172.20.10.2、HostKeyAlias raspberrypi.local）。PI_HOST=wire-pi、remote pi=wire-pi:cable-suspended-pier-robot

## 2026-10-28
- IH 塗膜剥離装置からの電磁ノイズ対策として、制御回路（ラズパイ・IBT-2 など）を電装ボックスに収める（ユーザー決定）
  - 未定（ユーザーに確認中）：ボックスの材質（金属か樹脂か）、収める範囲（リポ・DCDC・ブレーカー・IMU を入れるか）、以前の案「基板の下にアルミ板＋1点接地」との関係（置き換えか併用か）
  - 金属ボックスの場合の懸念：内蔵 Bluetooth（DualSense）と Wi-Fi（SSH）の電波が遮られる → 通信途絶で常に停止しうる。外付けアンテナ／USB ドングルを延長で箱の外へ、などが必要
