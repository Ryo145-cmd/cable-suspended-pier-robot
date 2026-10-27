# 踏んだ地雷・触ると壊れる所

## 配線
- IBT-2 は内部で信号GNDと B− がつながっている。B− は太い線でリポ − に直接。細い信号GNDにモータ電流を流さない
- GPIO2/3 は I2C（IMU）なのでモータに使わない

## ラズパイ・Windows 間
- SSH のパスワード入力・sudo のパスワード入力は対話になり、Claude Code からは止まる → 鍵認証、sudo はユーザーに手で
- Windows の scp はローカル側のワイルドカード（`dir\*`）が使えない → tar にまとめて送る（deploy.ps1）
- PowerShell 5.1 は BOM なし UTF-8 の .ps1 を Shift-JIS として読み、日本語で壊れる → .ps1 は UTF-8 BOM 付きで保存
- Windows で git checkout すると .sh/.py が CRLF になりラズパイで動かない → .gitattributes で LF 固定済み。消さない
- エクスプローラーで zip 展開すると .sh の実行ビットが落ちて git に差分が出る → PC のクローンは `git config core.fileMode false` 済み
- tests/test_link.py は Windows では動かない（os.set_blocking がパイプに使えない）→ ラズパイで実行する。test_logic.py は Windows でも通る
- Wi-Fi 2.4GHz と Bluetooth は干渉する → ラズパイの Wi-Fi は 5GHz か有線

## 検討時の取り違え
- 2026-10-27：レール固定マグネットを「腹板（壁面）に付けた」と思い込んでこじりの検討をしたが、実際は**上フランジ下面（天井面）**だった。
  取付方向・荷重方向は推測せずに確認してから検討する
- 「銅板」は「鋼板」の誤記だった（銅にはマグネットは付かない）。材料名が不自然なら確認する
