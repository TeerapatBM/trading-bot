# Fresh install on the target Windows VPS only. Never run on the development PC.
[CmdletBinding()]
param(
    [string]$InstallRoot = 'C:\Trading-bot',
    [string]$Domain = 'btxm.sysplatsec.dev',
    [string]$PythonVersion = '3.13.17',
    [string]$Mt5Root = 'C:\Program Files\TradingDesk MT5'
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-Exit([string]$Operation) {
    if ($LASTEXITCODE -ne 0) { throw "$Operation failed (exit $LASTEXITCODE)" }
}

function Wait-ProcessExit([string]$Path, [string]$Arguments, [int]$Seconds = 600) {
    $process = Start-Process -FilePath $Path -ArgumentList $Arguments -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit($Seconds * 1000)) {
        throw "Installer is still running after $Seconds seconds. Inspect the target desktop before retrying."
    }
    if ($process.ExitCode -notin @(0, 3010)) { throw "Installer failed: $Path (exit $($process.ExitCode))" }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $argsText = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -InstallRoot "{1}" -Domain "{2}" -PythonVersion "{3}" -Mt5Root "{4}"' -f $PSCommandPath, $InstallRoot, $Domain, $PythonVersion, $Mt5Root
    $elevated = Start-Process powershell.exe -Verb RunAs -ArgumentList $argsText -Wait -PassThru
    exit $elevated.ExitCode
}
if ($Domain.Length -gt 253 -or $Domain -notmatch '^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$') {
    throw 'Domain must be a plain lowercase hostname, without scheme or port.'
}
if ($PythonVersion -ne '3.13.17') { throw 'This verified bundle is built for Python 3.13.17 x64.' }
foreach ($pathValue in @($InstallRoot, $Mt5Root)) {
    if ($pathValue -match '["\r\n]' -or -not [IO.Path]::IsPathRooted($pathValue)) {
        throw 'Installation paths must be absolute and cannot contain quotes or newlines.'
    }
}
$sourceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot)).TrimEnd('\')
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
if ($InstallRoot -eq [IO.Path]::GetPathRoot($InstallRoot).TrimEnd('\')) { throw 'Installation cannot target a drive root.' }
if (Test-Path -LiteralPath (Join-Path $InstallRoot '.env')) {
    throw 'An existing Trading Desk installation was found. No files or trading state were changed. Use an explicit update procedure.'
}
if (Get-Service -Name TradingDeskProxy -ErrorAction SilentlyContinue) { throw 'TradingDeskProxy service already exists; no existing service was changed.' }
if (Get-ScheduledTask -TaskName TradingDesk-Worker -ErrorAction SilentlyContinue) { throw 'TradingDesk-Worker task already exists; existing task was not changed.' }
foreach ($port in @(80, 443, 8899)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already used on the VPS. Existing applications were not stopped."
    }
}

Write-Host '[1/8] Verifying release files ...'
$manifestFile = Join-Path $PSScriptRoot 'SHA256.json'
$packageFile = Join-Path $PSScriptRoot 'package.json'
if (-not (Test-Path -LiteralPath $manifestFile)) { throw 'SHA256 manifest is missing. Use the complete release ZIP.' }
$metadata = Get-Content -LiteralPath $packageFile -Raw | ConvertFrom-Json
if (-not $metadata.offline_vendor_files) { throw 'Source-only bundle cannot install. Use the full vendor bundle.' }
$manifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
foreach ($item in $manifest.PSObject.Properties) {
    $candidate = [IO.Path]::GetFullPath((Join-Path $sourceRoot $item.Name))
    if (-not $candidate.StartsWith($sourceRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid manifest path.' }
    if (-not (Test-Path -LiteralPath $candidate)) { throw "Missing package file: $($item.Name)" }
    $actualHash = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $item.Value) { throw "Release checksum mismatch: $($item.Name)" }
}
$pythonInstaller = Join-Path $sourceRoot 'vendor\python-amd64.exe'
$mt5Installer = Join-Path $sourceRoot 'vendor\mt5setup.exe'
foreach ($binary in @($pythonInstaller, $mt5Installer)) {
    $signature = Get-AuthenticodeSignature -LiteralPath $binary
    if ($signature.Status -ne 'Valid') { throw "Installer signature is not valid: $binary" }
    $publisher = $signature.SignerCertificate.Subject
    if ($binary -eq $pythonInstaller -and $publisher -notmatch 'Python Software Foundation') { throw 'Unexpected Python publisher.' }
    if ($binary -eq $mt5Installer -and $publisher -notmatch 'MetaQuotes') { throw 'Unexpected MT5 publisher.' }
}

Write-Host '[2/8] Preparing application directory ...'
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
if ($sourceRoot -ne $InstallRoot) {
    foreach ($relative in @('bot', 'web', 'docs', 'deploy', 'run.py', '.env.example', 'start.ps1', 'install-mt5.ps1', 'README.md')) {
        $src = Join-Path $sourceRoot $relative
        if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination $InstallRoot -Recurse -Force }
    }
}
$runtime = Join-Path $InstallRoot 'runtime'
$logs = Join-Path $InstallRoot 'logs'
$data = Join-Path $InstallRoot 'data'
foreach ($directory in @($runtime, $logs, $data)) { New-Item -ItemType Directory -Path $directory -Force | Out-Null }
# Targeted permissions only: SYSTEM and local Administrators, no password stored.
& icacls.exe $InstallRoot '/inheritance:r' '/grant:r' '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' | Out-Null
Assert-Exit 'Application directory ACL'

Write-Host '[3/8] Installing dedicated Python runtime and MT5 connector ...'
$pythonHome = Join-Path $runtime 'Python313'
$python = Join-Path $pythonHome 'python.exe'
Wait-ProcessExit $pythonInstaller ('/quiet InstallAllUsers=1 Include_launcher=0 Include_test=0 Include_doc=0 Include_tcltk=0 Include_pip=1 PrependPath=0 TargetDir="' + $pythonHome + '"')
if (-not (Test-Path -LiteralPath $python)) { throw 'Python installer did not create the expected runtime.' }
& $python -m venv (Join-Path $InstallRoot '.venv')
Assert-Exit 'Virtual environment creation'
$venvPython = Join-Path $InstallRoot '.venv\Scripts\python.exe'
$wheelDirectory = Join-Path $sourceRoot 'vendor\wheels'
& $venvPython -m pip install --disable-pip-version-check --no-index --find-links $wheelDirectory ('MetaTrader5==' + $metadata.metatrader5)
Assert-Exit 'Offline MT5 package installation'
& $venvPython -c 'import sys, sqlite3, MetaTrader5; assert sys.maxsize > 2**32; print("Python x64 and MT5 connector ready")'
Assert-Exit 'Python connector verification'

Write-Host '[4/8] Installing MetaTrader 5 ...'
$terminal = Join-Path $Mt5Root 'terminal64.exe'
if (-not (Test-Path -LiteralPath $terminal)) {
    Wait-ProcessExit $mt5Installer ('/auto /path:"' + $Mt5Root + '"') 900
}
if (-not (Test-Path -LiteralPath $terminal)) { throw 'MT5 terminal was not found after installation.' }

Write-Host '[5/8] Writing application and HTTPS configuration ...'
@"
BIND_HOST=127.0.0.1
PORT=8899
MT5_PATH=$terminal
ALLOW_LIVE_TRADING=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
"@ | Set-Content -LiteralPath (Join-Path $InstallRoot '.env') -Encoding UTF8
Copy-Item -LiteralPath (Join-Path $sourceRoot 'vendor\caddy.exe') -Destination (Join-Path $runtime 'caddy.exe') -Force
Copy-Item -LiteralPath (Join-Path $sourceRoot 'vendor\caddy-LICENSE') -Destination (Join-Path $runtime 'caddy-LICENSE') -Force
$caddy = Join-Path $runtime 'caddy.exe'
$normalizedRoot = $InstallRoot.Replace('\', '/')
$caddyConfig = Join-Path $InstallRoot 'Caddyfile'
@"
{
    admin off
    storage file_system {
        root "$normalizedRoot/runtime/caddy-data"
    }
    log {
        output file "$normalizedRoot/logs/caddy-runtime.log" {
            roll_size 10MiB
            roll_keep 5
        }
    }
}

$Domain {
    encode zstd gzip
    header -Server
    header Strict-Transport-Security "max-age=31536000"
    request_body {
        max_size 32KB
    }
    reverse_proxy 127.0.0.1:8899 {
        transport http {
            dial_timeout 5s
            response_header_timeout 30s
        }
    }
}
"@ | Set-Content -LiteralPath $caddyConfig -Encoding UTF8
& $caddy validate --config $caddyConfig --adapter caddyfile
Assert-Exit 'Caddy configuration validation'

Write-Host '[6/8] Registering interactive tasks and HTTPS service ...'
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$workerScript = Join-Path $InstallRoot 'deploy\run-worker.ps1'
$workerArguments = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $workerScript + '"'
$workerAction = New-ScheduledTaskAction -Execute $powershell -Argument $workerArguments -WorkingDirectory $InstallRoot
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest
$workerTrigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$workerTrigger.Delay = 'PT30S'
$taskSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'TradingDesk-Worker' -Action $workerAction -Trigger $workerTrigger -Principal $taskPrincipal -Settings $taskSettings -Description 'Trading Desk worker; same interactive user session as MT5; no stored Windows password.' | Out-Null
$mt5Action = New-ScheduledTaskAction -Execute $terminal -WorkingDirectory $Mt5Root
$mt5Trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
Register-ScheduledTask -TaskName 'TradingDesk-MT5' -Action $mt5Action -Trigger $mt5Trigger -Principal $taskPrincipal -Settings $taskSettings -Description 'Open MT5 in the trading user session; XM login is configured by the owner.' | Out-Null
$serviceCommand = '"' + $caddy + '" run --config "' + $caddyConfig + '" --adapter caddyfile'
New-Service -Name 'TradingDeskProxy' -DisplayName 'Trading Desk HTTPS Proxy' -BinaryPathName $serviceCommand -StartupType Automatic -Description 'Caddy TLS reverse proxy for Trading Desk on localhost:8899.' | Out-Null
& sc.exe failure TradingDeskProxy reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null
Assert-Exit 'HTTPS service recovery configuration'
foreach ($port in @(80, 443)) {
    $rule = 'TradingDesk-HTTP-' + $port
    if (-not (Get-NetFirewallRule -Name $rule -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Program $caddy -Profile Any | Out-Null
    }
}
Start-ScheduledTask -TaskName 'TradingDesk-MT5'
Start-ScheduledTask -TaskName 'TradingDesk-Worker'
Start-Service -Name 'TradingDeskProxy'

Write-Host '[7/8] Verifying local dashboard and authenticated API ...'
$healthy = $false
for ($attempt = 0; $attempt -lt 45; $attempt++) {
    try {
        $page = Invoke-WebRequest -Uri 'http://127.0.0.1:8899/' -UseBasicParsing -TimeoutSec 3
        if ($page.StatusCode -eq 200) { $healthy = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $healthy) { throw "Worker did not become healthy. Inspect $logs and Task Scheduler." }
$keyFile = Join-Path $data 'dashboard-token.txt'
$dashboardKey = (Get-Content -LiteralPath $keyFile -Raw).Trim()
$apiState = Invoke-RestMethod -Uri 'http://127.0.0.1:8899/api/state' -Headers @{ Authorization = 'Bearer ' + $dashboardKey } -TimeoutSec 10
if ($apiState.config.mode -ne 'paper' -or $apiState.running -or $null -ne $apiState.position) {
    throw 'Unexpected initial state. Installer did not start trading; inspect the app.'
}
$dashboardKey = $null
$httpsReady = $false
try {
    $securePage = Invoke-WebRequest -Uri ('https://' + $Domain + '/') -UseBasicParsing -TimeoutSec 15
    $httpsReady = $securePage.StatusCode -eq 200
} catch { Write-Host 'HTTPS certificate is pending. Check DNS and upstream firewall TCP 80/443. Caddy will retry automatically.' }

Write-Host '[8/8] Creating owner handoff shortcuts and deployment report ...'
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Trading Desk.url'))
$shortcut.TargetPath = 'https://' + $Domain
$shortcut.Save()
$keyShortcut = $shell.CreateShortcut((Join-Path $desktop 'Trading Desk - dashboard key.lnk'))
$keyShortcut.TargetPath = Join-Path $env:SystemRoot 'System32\notepad.exe'
$keyShortcut.Arguments = '"' + $keyFile + '"'
$keyShortcut.Save()
$report = [ordered]@{
    installedAtUtc = [DateTime]::UtcNow.ToString('o')
    domain = $Domain
    installRoot = $InstallRoot
    localDashboardHealthy = $healthy
    httpsVerified = $httpsReady
    python = $PythonVersion
    connector = $metadata.metatrader5
    mt5Path = $terminal
    mode = 'paper'
    running = $false
    xmAccountConfigured = $false
    requiresUserLoginAfterReboot = $true
    dashboardKeyFile = $keyFile
}
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $InstallRoot 'deployment-report.json') -Encoding UTF8
Write-Host ''
Write-Host 'Installed: Python, Trading Desk, MT5, interactive startup tasks and HTTPS proxy.'
Write-Host ('Dashboard: https://' + $Domain)
Write-Host ('Dashboard key file: ' + $keyFile)
Write-Host 'Initial state: PAPER / PAUSED. Owner must log in to XM in MT5.'
Write-Host 'After reboot, log in to Windows to restore the interactive MT5 session.'
Write-Host ('Report: ' + (Join-Path $InstallRoot 'deployment-report.json'))
