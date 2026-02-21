param(
    [string]$CarbonRoot = "C:\CarbonBot",
    [string]$CarbonVersion = "2.3.5"
)

$ErrorActionPreference = "Stop"

$runningCarbon = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like "Carbon*" }
if ($runningCarbon) {
    $pids = ($runningCarbon | Select-Object -ExpandProperty Id) -join ", "
    throw "Carbon appears to be running (PID(s): $pids). Close Carbon completely before activating stable test mode."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installScript = Join-Path $scriptDir "install_carbon_plugin.ps1"
$verifyScript = Join-Path $scriptDir "verify_carbon_pipeline.ps1"

& $installScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion -EnableBotimusIntegration
& $verifyScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion -RequireActiveIntegration
