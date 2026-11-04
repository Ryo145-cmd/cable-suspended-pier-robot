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
- 電装ボックスの材質は「多分ポリカーボネート」（ユーザー、未確定）
  - 樹脂なので Bluetooth・Wi-Fi は通る。ただし電磁ノイズはほぼ遮らない（防塵・防滴・接触防止の効果が主）
  - ノイズ対策として Claude が提案：箱の中に以前の案のアルミ底板（1点接地）を併用、線の出入口にフェライトコア、モータ線はより線、IH コイルから距離をとる。採否はユーザー

## 2026-11-04
- IBT-2 のピンを配線変更に合わせて変更（ユーザー指示）：UL R27/L17、UR R19/L13、LL R10/L22、LR R6/L5（EN 26・I2C 2/3 は変更なし）
  - UL はユーザーが「R と L が逆」と明言。UR/LL/LR はユーザーが書いた順を RPWM, LPWM と解釈（R/L の対応はテスター確認を省略、ユーザー判断）
  - R/L の取り違えは回転方向が逆になるだけなので、空転試験の invert 決定で吸収する。invert の既定値は変更前のまま
  - GPIO10 は SPI0 MOSI と兼用。SPI が有効だと使えない → 2026-11-04 Pi で SPI 無効を確認済み
  - 仕様書 PDF のピン表は旧番号のまま（PDF は更新不可）
- `main.py --no-imu` を追加（ユーザー承認、案A）：IMU 未接続でコントローラから実モータを回す空転試験用
  - IMU の代わりに傾き 0° 固定のダミー、傾き補正は強制 OFF（△でも ON にならない）。傾き制限は実質働かない
  - 対策：起動時に「ワイヤを外した」ことを yes 入力で確認しないと始まらない。状態表示に常に「IMU なし」
  - 他の安全機能（中央復帰待ち・非常停止ラッチ・通信途絶 0.2 秒停止・EN・加速制限）は本番と同じコードを通る
  - 棄てた案B（専用ツール新規作成）：安全機能を別コードで再実装することになり、ミスの余地が増える。走行モードの試験もできない
- 走行速度を変更（ユーザー指示）：通常 70%・R1（FAST）押下中 100%（デューティ）。MAX_DUTY 0.8→1.0、LOW_SPEED_SCALE 0.4→0.7
  - 以前は通常 0.32・FAST 0.8。ワイヤ調整モード（WIRE_ADJUST_SCALE 0.3）は R1 が選択ボタンのため変更なし
  - 100% では傾き補正の上乗せ余地がないが、mix は飽和時に比率を保って縮めるので補正は効く（test_saturation_keeps_ratio）
- ワイヤ調整の肩ボタンが「L1⇔L2、R1⇔R2 が逆っぽい」（ユーザー、2026-11-04）。ドラム段の想定違い（WIRE_BUTTONS を直す）か、UL⇔LL・UR⇔LR のピン入れ替わり（MOTORS を直す）かを、走行モードの右スティック左右で切り分け中
- IMU の符号を確定：IMU_AXIS_NORMAL "+z"→"-z"（IMU_AXIS_RIGHT "+x"・IMU_AXIS_UP "+y" はそのまま）
  - imu_check で正面から見て右側を下げてもらった（ユーザーに指示した動作。2 回目の記録）：加速度角 −4°→+15° で正、角速度は −12°/s で逆 → ジャイロ軸の符号を反転
  - 1 回目の記録も加速度と角速度が逆向き（動かした向きは不明）で、ジャイロが逆という結論と矛盾しない
  - 置いたままで加速度角 −4°：取付か台の傾き。運用は CREATE（水平記録）で 0 にする
