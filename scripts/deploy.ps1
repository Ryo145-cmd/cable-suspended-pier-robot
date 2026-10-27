# PC(Windows) → ラズパイへ反映する（git push pi main → ラズパイでテスト）
#   .\scripts\deploy.ps1                         （PI_HOST を使う）
#   .\scripts\deploy.ps1 ryosuke@raspberrypi.local
# 前提：ラズパイで setup_pi.sh 済み、PC に remote "pi" がある
#   git remote add pi ryosuke@raspberrypi.local:cable-suspended-pier-robot
# ラズパイ側に未コミットの変更（現場で書き換えた config.py など）があると push は拒否される。
# そのときは表示される git diff を確認してから対処する（勝手に捨てない）
param(
    [string]$PiHost = $env:PI_HOST
)
$ErrorActionPreference = "Stop"
if (-not $PiHost) { Write-Error "接続先を指定してください（例: ryosuke@raspberrypi.local）" }

$repo = "~/cable-suspended-pier-robot"
git -C (Join-Path $PSScriptRoot "..") push pi main
if ($LASTEXITCODE -ne 0) {
    Write-Host "push が拒否されました。ラズパイ側の変更："
    ssh $PiHost "cd $repo && git status --short && git diff"
    exit 1
}
ssh $PiHost "cd $repo/src/wire_robot && python3 tests/test_logic.py && python3 tests/test_link.py"
if ($LASTEXITCODE -ne 0) { Write-Error "ラズパイでのテストが失敗しました" }
Write-Host "反映完了: ${PiHost}:$repo（~/wire_robot はここの src/wire_robot へのリンク）"
