$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python virtual environment' }
& '.venv/Scripts/python.exe' -m pip install --upgrade pip
& '.venv/Scripts/python.exe' -m pip install MetaTrader5
if ($LASTEXITCODE -ne 0) { throw 'MetaTrader5 installation failed. Use 64-bit Python supported by the package.' }
