# Run in the same interactive user session as MT5. No broker credentials here.
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $appRoot
$logFolder = Join-Path $appRoot 'logs'
New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
$logPath = Join-Path $logFolder ('worker-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')
& (Join-Path $appRoot '.venv\Scripts\python.exe') -u (Join-Path $appRoot 'run.py') *>> $logPath
exit $LASTEXITCODE
