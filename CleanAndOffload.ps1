<#
.SYNOPSIS
    Safe C: Drive Storage Cleaner & Offloader with Live Terminal Streaming Progress
.DESCRIPTION
    Safely cleans temporary caches and offloads large user folders (.gemini, .cache)
    to D: drive via Windows Directory Junctions with live file-by-file progress streaming.
#>

[CmdletBinding()]
param (
    [string]$TargetOffloadDir = "D:\StorageOffload",
    [switch]$OffloadGemini = $true,
    [switch]$OffloadCache = $true,
    [switch]$CleanChromeCache = $true,
    [switch]$CleanDevCaches = $true,
    [switch]$CleanTempFiles = $true
)

# Force immediate output flushing
$stdout = [System.Console]::Out

function Write-Header ($text) {
    Write-Host ""
    Write-Host "==========================================================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Yellow
    Write-Host "==========================================================================" -ForegroundColor Cyan
    $stdout.Flush()
}

function Write-Step ($step, $message) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [$step] $message" -ForegroundColor Green
    $stdout.Flush()
}

function Write-Info ($message) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [INFO] $message" -ForegroundColor Gray
    $stdout.Flush()
}

function Write-Warn ($message) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [WARN] $message" -ForegroundColor DarkYellow
    $stdout.Flush()
}

function Write-Success ($message) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [SUCCESS] $message" -ForegroundColor Green
    $stdout.Flush()
}

# ============================================================================
# PRE-FLIGHT PROCESS SAFETY CHECK
# ============================================================================
Write-Header "SAFETY CHECK: SCANNING RUNNING PROCESSES"

$runningProcesses = @()
$checkApps = @("Antigravity IDE", "Antigravity", "chrome", "code", "cursor", "python")

foreach ($app in $checkApps) {
    $procs = Get-Process -Name $app -ErrorAction SilentlyContinue
    if ($procs) {
        $runningProcesses += "$app (PIDs: $($procs.Id -join ', '))"
    }
}

if ($runningProcesses.Count -gt 0) {
    Write-Warn "CRITICAL SAFETY NOTICE:"
    Write-Warn "The following applications are currently RUNNING:"
    foreach ($rp in $runningProcesses) {
        Write-Host "   - $rp" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "To prevent file locking, data corruption, or interrupted updates, please:" -ForegroundColor Yellow
    Write-Host "   1. Save your work." -ForegroundColor Yellow
    Write-Host "   2. Close Antigravity IDE, Chrome, and Python applications." -ForegroundColor Yellow
    Write-Host ""
    $answer = Read-Host "Do you want to proceed anyway? (y/N)"
    if ($answer -notmatch '^[Yy]') {
        Write-Warn "Operation cancelled by user for safety. Please close the applications and re-run."
        exit
    }
} else {
    Write-Success "Pre-flight check passed! No conflicting applications detected."
}


# ============================================================================
# STAGE 0: INITIAL AUDIT
# ============================================================================
Write-Header "STAGE 0: STORAGE AUDIT"

$cVol = Get-Volume -DriveLetter C
$initialFreeGB = [math]::Round($cVol.SizeRemaining / 1GB, 2)
$initialTotalGB = [math]::Round($cVol.Size / 1GB, 2)

Write-Host "Drive C: Free Space : " -NoNewline
Write-Host "$initialFreeGB GB" -ForegroundColor Cyan -NoNewline
Write-Host " out of $initialTotalGB GB"

# Create Offload Directory on D:
if (-not (Test-Path $TargetOffloadDir)) {
    New-Item -ItemType Directory -Path $TargetOffloadDir -Force | Out-Null
    Write-Info "Created base offload directory on D: drive -> $TargetOffloadDir"
}


# ============================================================================
# STAGE 1: TEMP & RECYCLE BIN CLEANUP (LIVE FILE-BY-FILE STREAMING)
# ============================================================================
if ($CleanTempFiles) {
    Write-Header "STAGE 1: CLEANING TEMP FILES & RECYCLE BIN"
    
    $tempPaths = @(
        "$env:LOCALAPPDATA\Temp",
        "C:\Windows\Temp"
    )

    foreach ($tPath in $tempPaths) {
        if (Test-Path $tPath) {
            Write-Step "TEMP" "Scanning files in: $tPath"
            $items = Get-ChildItem -Path $tPath -ErrorAction SilentlyContinue
            $count = 0
            foreach ($item in $items) {
                try {
                    Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
                    $count++
                    Write-Host "`r[LIVE] Cleared $count items from $tPath..." -NoNewline -ForegroundColor Gray
                } catch {}
            }
            Write-Host ""
            Write-Success "Finished cleaning $tPath ($count items removed)."
        }
    }

    # Empty Recycle Bin
    Write-Step "RECYCLE-BIN" "Emptying Recycle Bin..."
    try {
        Clear-RecycleBin -DriveLetter C -Force -ErrorAction SilentlyContinue
        Write-Success "Recycle Bin cleared."
    } catch {
        Write-Info "Recycle Bin was already empty."
    }
}


# ============================================================================
# STAGE 2: CHROME & WEB BROWSER CACHE PURGE
# ============================================================================
if ($CleanChromeCache) {
    Write-Header "STAGE 2: CLEANING BROWSER CACHES"
    
    $chromeCacheDirs = @(
        "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache",
        "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Code Cache",
        "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\GPUCache",
        "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Service Worker\CacheStorage"
    )

    foreach ($cDir in $chromeCacheDirs) {
        if (Test-Path $cDir) {
            Write-Step "CHROME" "Purging browser cache: $cDir"
            $items = Get-ChildItem -Path $cDir -ErrorAction SilentlyContinue
            $cCount = 0
            foreach ($item in $items) {
                Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
                $cCount++
                Write-Host "`r[LIVE] Deleted $cCount cache files..." -NoNewline -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    Write-Success "Chrome web caches cleared safely (user profile & logins untouched)."
}


# ============================================================================
# STAGE 3: DEVELOPER PACKAGE CACHES
# ============================================================================
if ($CleanDevCaches) {
    Write-Header "STAGE 3: PURGING DEVELOPER TOOL CACHES"
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Step "NPM" "Purging npm cache..."
        cmd /c "npm cache clean --force" 2>&1 | Out-Null
        Write-Success "NPM cache cleared."
    }

    if (Get-Command pip -ErrorAction SilentlyContinue) {
        Write-Step "PIP" "Purging pip cache..."
        cmd /c "pip cache purge" 2>&1 | Out-Null
        Write-Success "Pip cache cleared."
    }
    
    if (Get-Command conda -ErrorAction SilentlyContinue) {
        Write-Step "CONDA" "Purging conda cache..."
        cmd /c "conda clean --all -y" 2>&1 | Out-Null
        Write-Success "Conda cache cleared."
    }
}


# ============================================================================
# STAGE 4: OFFLOADING DIRS TO DRIVE D (LIVE ROBOCOPY STREAMING)
# ============================================================================
Write-Header "STAGE 4: OFFLOADING HEAVY FOLDERS TO DRIVE D VIA JUNCTIONS"

function Safe-Move-And-Junction ([string]$src, [string]$targetSubdir) {
    if (-not (Test-Path $src)) {
        Write-Info "Source path $src does not exist. Skipping."
        return
    }

    $srcItem = Get-Item $src
    if ($srcItem.Attributes -match "ReparsePoint") {
        Write-Success "$src is ALREADY a Junction point. Skipping offload."
        return
    }

    $dst = Join-Path $TargetOffloadDir $targetSubdir
    Write-Step "ROBOCOPY" "Streaming Live Move: $src ===> $dst"

    if (-not (Test-Path $dst)) {
        New-Item -ItemType Directory -Path $dst -Force | Out-Null
    }

    # Run Robocopy directly for live streaming stdout
    robocopy.exe "$src" "$dst" /E /MOVE /BYTES /ETA /V /R:1 /W:1

    # Verify Move Succeeded
    if (Test-Path $src) {
        $remainingFiles = (Get-ChildItem -Path $src -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
        if ($remainingFiles -eq 0) {
            Remove-Item -Path $src -Force -Recurse -ErrorAction SilentlyContinue
        } else {
            Write-Warn "Robocopy left $remainingFiles locked files in $src. Junction creation postponed."
            return
        }
    }

    # Create Junction Link
    Write-Step "JUNCTION" "Creating Windows Directory Junction: $src -> $dst"
    $jResult = cmd /c "mklink /J `"$src`" `"$dst`""
    Write-Success "Junction Result: $jResult"
}

if ($OffloadGemini) {
    Safe-Move-And-Junction "C:\Users\91998\.gemini" ".gemini"
}

if ($OffloadCache) {
    Safe-Move-And-Junction "C:\Users\91998\.cache" ".cache"
}


# ============================================================================
# STAGE 5: FINAL AUDIT & SUMMARY
# ============================================================================
Write-Header "FINAL SUMMARY: RECLAIMED SPACE AUDIT"

$cVolFinal = Get-Volume -DriveLetter C
$finalFreeGB = [math]::Round($cVolFinal.SizeRemaining / 1GB, 2)
$savedGB = [math]::Round($finalFreeGB - $initialFreeGB, 2)

Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  CLEANUP & OFFLOAD COMPLETE!" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Green
Write-Host "  Initial Free Space on C: : $initialFreeGB GB"
Write-Host "  Current Free Space on C: : " -NoNewline
Write-Host "$finalFreeGB GB" -ForegroundColor Green
Write-Host "  TOTAL SPACE RECLAIMED    : " -NoNewline
Write-Host "+$savedGB GB" -ForegroundColor Yellow -NoNewline
Write-Host " 🎉"
Write-Host "==========================================================================" -ForegroundColor Green
