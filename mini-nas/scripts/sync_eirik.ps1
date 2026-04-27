# sync_eirik.ps1 - Memory folder ZIP backup + Postgres metadata
# Plug-and-play setup: reads paths from environment or .env file
# Author: Erki Unn + Eirik (Cowork agent)
# Run: pwsh ./sync_eirik.ps1   (or via Task Scheduler every 6h)

$ErrorActionPreference = "Stop"

# Load config from .env file in repo root (one level up from scripts/)
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([A-Z_]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

$source = $env:EIRIK_PATH
if (-not $source) {
    Write-Error "EIRIK_PATH not set. Edit .env file or set environment variable."
    exit 1
}

$backupDir = if ($env:BACKUP_PATH) { $env:BACKUP_PATH } else { Join-Path $PSScriptRoot "..\backups" }
if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Force -Path $backupDir | Out-Null }

$ts = Get-Date -Format "yyyy-MM-dd_HHmm"
$fileName = "Eirik_backup_" + $ts + ".zip"
$dest = Join-Path $backupDir $fileName

Write-Host "Source: $source"
Write-Host "Destination: $dest"

Compress-Archive -Path $source -DestinationPath $dest -CompressionLevel Optimal

$fileInfo = Get-Item $dest
$sizeBytes = $fileInfo.Length
$fileCount = (Get-ChildItem -Path $source -Recurse -File).Count
$hash = (Get-FileHash -Path $dest -Algorithm SHA256).Hash

# Insert metadata to local Postgres (via docker exec)
$dbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "forestsense" }
$dbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "forestsense" }

$sql = @"
CREATE TABLE IF NOT EXISTS memory_backups (
    id SERIAL PRIMARY KEY,
    backup_file TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    file_count INT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO memory_backups (backup_file, size_bytes, file_count, sha256)
VALUES ('$fileName', $sizeBytes, $fileCount, '$hash');

INSERT INTO agent_messages (from_agent, to_agent, message_type, priority, payload, status)
VALUES ('eirik', 'self', 'heartbeat', 5,
        json_build_object('subject', 'Memory backup created', 'file', '$fileName',
                          'size_bytes', $sizeBytes, 'file_count', $fileCount)::jsonb,
        'done');
"@

try {
    $sql | docker exec -i forestsense-postgres psql -U $dbUser -d $dbName 2>&1 | Out-Null
    Write-Host "Postgres metadata logged"
} catch {
    Write-Host "Postgres unavailable, ZIP saved but no metadata: $_"
}

# Keep last 30 backups
$keep = if ($env:KEEP_BACKUPS) { [int]$env:KEEP_BACKUPS } else { 30 }
Get-ChildItem -Path $backupDir -Filter "Eirik_backup_*.zip" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip $keep |
    Remove-Item -Force

Write-Host "Backup OK: $dest"
Write-Host "Size: $([math]::Round($sizeBytes/1KB,1)) KB, Files: $fileCount, Hash: $($hash.Substring(0,16))..."
