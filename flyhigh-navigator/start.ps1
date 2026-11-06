# Start FlyHigh Navigator (Windows PowerShell). Usage: ./start.ps1   ·   stop: docker compose down
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host "Install Docker Desktop first."; exit 1 }
docker info *> $null; if ($LASTEXITCODE -ne 0) { Write-Host "Start Docker Desktop and retry."; exit 1 }
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env (add LLM_API_KEY to enable LLM drafting)." }
docker compose up -d --build
$port = ((Get-Content .env | Where-Object { $_ -match '^FLYHIGH_PORT=' }) -replace 'FLYHIGH_PORT=','')
if (-not $port) { $port = 8080 }
for ($i = 0; $i -lt 90; $i++) {
  try { Invoke-WebRequest -UseBasicParsing "http://localhost:$port/api/health" | Out-Null; Write-Host "Ready: http://localhost:$port"; Start-Process "http://localhost:$port"; exit 0 } catch { Start-Sleep 2 }
}
Write-Host "Not ready yet. Check: docker compose logs app"; exit 1
