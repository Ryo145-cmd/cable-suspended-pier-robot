# PC(Windows) → ラズパイへプログラムを転送する
#   .\scripts\deploy.ps1 pi@raspberrypi.local          （config.py は上書きしない）
#   .\scripts\deploy.ps1 pi@raspberrypi.local -Config  （config.py も上書きする）
# 環境変数 PI_HOST があれば引数は省略可。SSH は鍵認証を設定しておくこと
param(
    [string]$PiHost = $env:PI_HOST,
    [switch]$Config
)
$ErrorActionPreference = "Stop"
if (-not $PiHost) { Write-Error "接続先を指定してください（例: pi@raspberrypi.local）" }

$src = Join-Path $PSScriptRoot "..\program\wire_robot"
$tmp = Join-Path $env:TEMP "wire_robot_deploy"
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
Copy-Item $src $tmp -Recurse
Get-ChildItem $tmp -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

ssh $PiHost "mkdir -p ~/wire_robot"
if (-not $Config) {
    # ラズパイ側に config.py があれば残す（現場で調整した値を消さないため）
    $exists = ssh $PiHost "test -f ~/wire_robot/config.py && echo yes"
    if ($exists -eq "yes") {
        Remove-Item (Join-Path $tmp "config.py")
        Write-Host "config.py はラズパイ側のものを残します（上書きするなら -Config）"
    }
}
# tar にまとめて送る（Windows の scp はワイルドカードが使えないため。tar は Windows 10 以降に標準）
$tar = Join-Path $env:TEMP "wire_robot_deploy.tar"
tar -C $tmp -cf $tar .
scp $tar "${PiHost}:/tmp/wire_robot_deploy.tar"
ssh $PiHost "tar -C ~/wire_robot -xf /tmp/wire_robot_deploy.tar && rm /tmp/wire_robot_deploy.tar"
Remove-Item $tar
ssh $PiHost "cd ~/wire_robot && python3 tests/test_logic.py && python3 tests/test_link.py"
Write-Host "転送完了: ${PiHost}:~/wire_robot/"
