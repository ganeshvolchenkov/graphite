# Brings the backend up and puts it behind a public HTTPS URL for the frontend.
#
#   .\share.ps1              # port 8001
#   .\share.ps1 -Port 8000   # pick another port
#   .\share.ps1 -Stop        # shut both down
#
# The URL is random and changes on every start, so paste it into the frontend's
# "Backend URL" field rather than hardcoding it.

param([int]$Port = 8001, [switch]$Stop)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$log = Join-Path $root ".tunnel.log"
$python = Join-Path $root "venv\Scripts\python.exe"

$cloudflared = @(
    "C:\Program Files (x86)\cloudflared\cloudflared.exe",
    "C:\Program Files\cloudflared\cloudflared.exe",
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

function Stop-Shared {
    Get-CimInstance Win32_Process -Filter "Name = 'cloudflared.exe'" |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
    "stopped tunnel and any server on port $Port"
}

if ($Stop) { Stop-Shared; return }

if (-not $cloudflared) { throw "cloudflared not found. Run: winget install --id Cloudflare.cloudflared" }
if (-not (Test-Path $python)) { throw "venv not found at $python" }

# --- backend ---------------------------------------------------------------
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    "port $Port already serving (pid $($existing.OwningProcess)) - reusing it"
} else {
    Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$Port" `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $root ".uvicorn.log") `
        -RedirectStandardError (Join-Path $root ".uvicorn.err.log") | Out-Null

    $up = $false
    foreach ($i in 1..20) {
        try { Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2 | Out-Null; $up = $true; break }
        catch { Start-Sleep -Milliseconds 800 }
    }
    if (-not $up) { throw "backend did not come up - check .uvicorn.err.log" }
    "backend listening on 127.0.0.1:$Port"
}

# --- tunnel ----------------------------------------------------------------
Remove-Item $log -ErrorAction SilentlyContinue
Start-Process -FilePath $cloudflared `
    -ArgumentList "tunnel", "--url", "http://127.0.0.1:$Port", "--no-autoupdate" `
    -WindowStyle Hidden -RedirectStandardError $log `
    -RedirectStandardOutput (Join-Path $root ".tunnel.out.log") | Out-Null

$url = $null
foreach ($i in 1..30) {
    if (Test-Path $log) {
        $match = Select-String -Path $log -Pattern 'https://[-a-z0-9]+\.trycloudflare\.com' `
            -AllMatches -ErrorAction SilentlyContinue
        if ($match) { $url = $match.Matches[0].Value; break }
    }
    Start-Sleep -Milliseconds 800
}
if (-not $url) { throw "tunnel did not report a URL - check $log" }

# --- confirm it actually serves from the outside ---------------------------
# cloudflared prints the hostname before DNS resolves for it, so poll.
$health = $null
foreach ($i in 1..20) {
    try { $health = Invoke-RestMethod "$url/health" -TimeoutSec 10; break }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $health) { throw "$url never answered - the tunnel is up but not resolving yet" }

""
"  Backend URL : $url"
"  health      : $($health.status) / $($health.engine)"
"  dashboard   : $url/dashboard"
"  fixtures    : $url/fixtures.json"
"  api docs    : $url/docs"
""
"Send the Backend URL to the frontend. Stop with: .\share.ps1 -Stop"
"Note: this server executes strategy code that is posted to it, so keep the"
"tunnel up only while you are testing or demoing."
