# Start the main local run in an independent wsl.exe process.
#
# Usage (from Windows PowerShell, in the repo root):
#   powershell -ExecutionPolicy Bypass -File scripts/launch_main_local.ps1
#
# Unlike a one-shot `wsl -d Ubuntu -- bash ...` call, this keeps a wsl.exe
# process alive for the whole run, so closing PowerShell/OpenCode does not stop
# the experiment. The run logs to runs/logs/main-local-01.log.
$ErrorActionPreference = "Stop"

$repo = Split-Path $PSScriptRoot -Parent
$repoWsl = (wsl.exe -d Ubuntu -- wslpath -a "$repo").Trim()
$script = "`"$repoWsl/scripts/run_main_local.sh`""

$p = Start-Process -WindowStyle Hidden -PassThru -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu", "--", "bash", $script)

Write-Host "started wsl.exe pid $($p.Id)"
Write-Host "log: $repo\runs\logs\main-local-01.log"
