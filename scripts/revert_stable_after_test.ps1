param(
    [string]$CarbonRoot = "C:\CarbonBot",
    [string]$CarbonVersion = "2.3.5"
)

$ErrorActionPreference = "Stop"

$runningCarbon = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like "Carbon*" }
if ($runningCarbon) {
    $pids = ($runningCarbon | Select-Object -ExpandProperty Id) -join ", "
    throw "Carbon appears to be running (PID(s): $pids). Close Carbon completely before reverting stable runtime."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$archiveScript = Join-Path $scriptDir "archive_botimus_carbon_integration.ps1"
$verifyScript = Join-Path $scriptDir "verify_carbon_pipeline.ps1"

& $archiveScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion
& $verifyScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion
