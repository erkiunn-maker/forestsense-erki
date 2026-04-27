# setup.ps1 - One-command Mini-NAS setup for Windows
# Author: Erki Unn + Eirik (Cowork agent)
# Run: pwsh ./setup.ps1   (or right-click -> "Run with PowerShell")

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host " Mini-NAS Setup - Forestsense" -ForegroundColor Cyan
Write-Host " Local Postgres + Supabase mirror + memory backup" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker Desktop
Write-Host "[1/6] Checking Docker Desktop..." -ForegroundColor Yellow
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "  Docker not found. Install Docker Desktop first:" -ForegroundColor Red
    Write-Host "    winget install -e --id Docker.DockerDesktop" -ForegroundColor White
    Write-Host "  Then restart this script." -ForegroundColor Red
    exit 1
}
try {
    docker --version | Out-Null
    Write-Host "  Docker OK: $(docker --version)" -ForegroundColor Green
} catch {
    Write-Host "  Docker installed but not running. Start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Step 2: Check .env file
Write-Host "[2/6] Checking .env file..." -ForegroundColor Yellow
$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  Created .env from .env.example" -ForegroundColor Green
        Write-Host "  EDIT .env now: set EIRIK_PATH, SUPABASE_URL, SUPABASE_KEY" -ForegroundColor Yellow
        Write-Host "  Then run this script again." -ForegroundColor Yellow
        notepad $envFile
        exit 0
    } else {
        Write-Host "  .env.example missing. Did you clone the full repo?" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  .env exists" -ForegroundColor Green

# Step 3: Validate required env values
Write-Host "[3/6] Validating .env..." -ForegroundColor Yellow
$envContent = Get-Content $envFile
$eirikPath = ($envContent | Where-Object { $_ -match "^EIRIK_PATH=" }) -replace "^EIRIK_PATH=", ""
$supabaseUrl = ($envContent | Where-Object { $_ -match "^SUPABASE_URL=" }) -replace "^SUPABASE_URL=", ""
$supabaseKey = ($envContent | Where-Object { $_ -match "^SUPABASE_KEY=" }) -replace "^SUPABASE_KEY=", ""

if (-not $eirikPath) {
    Write-Host "  EIRIK_PATH not set in .env" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $eirikPath)) {
    Write-Host "  EIRIK_PATH does not exist: $eirikPath" -ForegroundColor Red
    exit 1
}
Write-Host "  EIRIK_PATH OK: $eirikPath" -ForegroundColor Green

if (-not $supabaseUrl -or $supabaseUrl -match "YOUR_PROJECT_REF") {
    Write-Host "  SUPABASE_URL not set (still placeholder)" -ForegroundColor Red
    exit 1
}
Write-Host "  SUPABASE_URL OK" -ForegroundColor Green

# Step 4: Create data + backups + scripts dirs
Write-Host "[4/6] Creating data/backups directories..." -ForegroundColor Yellow
@("data", "data/postgres", "backups") | ForEach-Object {
    $d = Join-Path $PSScriptRoot $_
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Force -Path $d | Out-Null }
}
Write-Host "  Directories ready" -ForegroundColor Green

# Step 5: docker compose up
Write-Host "[5/6] Starting Docker containers..." -ForegroundColor Yellow
Push-Location $PSScriptRoot
docker compose up -d
$composeOk = ($LASTEXITCODE -eq 0)
Pop-Location

if (-not $composeOk) {
    Write-Host "  docker compose failed" -ForegroundColor Red
    exit 1
}
Write-Host "  Containers started" -ForegroundColor Green

# Step 6: Schedule ZIP backup task (every 6h)
Write-Host "[6/6] Registering Task Scheduler entry (every 6h ZIP backup)..." -ForegroundColor Yellow
$scriptPath = Join-Path $PSScriptRoot "scripts/sync_eirik.ps1"
try {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File $scriptPath"
    $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddHours(3) -RepetitionInterval (New-TimeSpan -Hours 6)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 15)
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
    Register-ScheduledTask -TaskName "Forestsense_MiniNAS_Sync" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Mini-NAS ZIP backup every 6h" -Force | Out-Null
    Write-Host "  Task Scheduler registered: Forestsense_MiniNAS_Sync" -ForegroundColor Green
} catch {
    Write-Host "  Task Scheduler registration failed (may need Admin): $_" -ForegroundColor Yellow
    Write-Host "  Re-run this script as Administrator if you want auto-backup" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""
Write-Host "pgAdmin GUI:    http://localhost:5050" -ForegroundColor White
Write-Host "Postgres port:  5432" -ForegroundColor White
Write-Host ""
Write-Host "Check status:   docker compose ps" -ForegroundColor White
Write-Host "View logs:      docker logs forestsense-sync-supabase --tail 20" -ForegroundColor White
Write-Host ""
Write-Host "First sync may take 30-60s for Postgres to be ready." -ForegroundColor Cyan
