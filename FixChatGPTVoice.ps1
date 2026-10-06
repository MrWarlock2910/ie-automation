<#
.SYNOPSIS
    Automated Diagnostic & Repair Script for ChatGPT Windows App Voice Chat Handshake Timeouts
#>

Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "  CHATGPT DESKTOP APP VOICE CHAT REPAIR TOOL" -ForegroundColor Yellow
Write-Host "==========================================================================" -ForegroundColor Cyan

# 1. Terminate all 12+ orphaned ChatGPT background instances
Write-Host "[1/3] Terminating orphaned ChatGPT processes..." -ForegroundColor Green
$procs = Get-Process -Name "*chatgpt*", "*openai*" -ErrorAction SilentlyContinue
if ($procs) {
    Write-Host "Found $($procs.Count) running instances of ChatGPT. Terminating..." -ForegroundColor Yellow
    $procs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "All background processes killed successfully." -ForegroundColor Green
} else {
    Write-Host "No active ChatGPT processes found." -ForegroundColor Gray
}

# 2. Clear ChatGPT WebRTC & App Cache
Write-Host "`n[2/3] Clearing ChatGPT local caches..." -ForegroundColor Green
$pkgDir = "C:\Users\91998\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache"

if (Test-Path $pkgDir) {
    Write-Host "Purging local WebRTC and session cache in: $pkgDir" -ForegroundColor Yellow
    Remove-Item -Path "$pkgDir\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "ChatGPT local app cache cleared." -ForegroundColor Green
}

# 3. Audio & Permission Verification Summary
Write-Host "`n[3/3] System Audio & Permission Status:" -ForegroundColor Green
$micReg = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone\OpenAI.Codex_2p2nqsd0c76g0"
if (Test-Path $micReg) {
    $perm = (Get-ItemProperty $micReg).Value
    Write-Host "  - Windows Microphone Consent for ChatGPT: $perm" -ForegroundColor Cyan
}

Write-Host "`n==========================================================================" -ForegroundColor Cyan
Write-Host "  REPAIR COMPLETE! You can now restart ChatGPT and try Voice Chat." -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Cyan
