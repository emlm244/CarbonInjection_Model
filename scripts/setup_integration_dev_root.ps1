param(
    [string]$StableRoot = "C:\CarbonBot",
    [string]$DevRoot = "C:\CarbonBot_IntegrationDev"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $StableRoot)) {
    throw "Stable root not found: $StableRoot"
}

$runningCarbon = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like "Carbon*" }
if ($runningCarbon) {
    $pids = ($runningCarbon | Select-Object -ExpandProperty Id) -join ", "
    throw "Carbon appears to be running (PID(s): $pids). Close Carbon completely before syncing dev root."
}

New-Item -ItemType Directory -Path $DevRoot -Force | Out-Null

$stableResolved = (Resolve-Path -LiteralPath $StableRoot).Path
$devResolved = (Resolve-Path -LiteralPath $DevRoot).Path

$rc = robocopy $stableResolved $devResolved /E /R:1 /W:1 /NFL /NDL /NP /NJH /NJS /XD "logs" "diagnostics"
$code = $LASTEXITCODE
if ($code -ge 8) {
    throw "robocopy failed with exit code $code"
}

$marker = Join-Path $devResolved "INTEGRATION_DEV_ROOT.flag"
Set-Content -LiteralPath $marker -Value "Dev runtime root for CarbonInjection_Model integration testing." -Encoding UTF8

Write-Host "Dev root synchronized."
Write-Host "Stable Root: $stableResolved"
Write-Host "Dev Root   : $devResolved"
Write-Host "Marker     : $marker"
