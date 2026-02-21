param(
    [string]$CarbonRoot = "C:\CarbonBot_IntegrationDev",
    [string]$CarbonVersion = "2.3.5",
    [switch]$RequireCoreReady
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installScript = Join-Path $scriptDir "install_carbon_plugin.ps1"
$verifyScript = Join-Path $scriptDir "verify_carbon_pipeline.ps1"

& $installScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion -EnableBotimusIntegration

if ($RequireCoreReady) {
    & $verifyScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion -RequireActiveIntegration -RequireCoreReady
} else {
    & $verifyScript -CarbonRoot $CarbonRoot -CarbonVersion $CarbonVersion -RequireActiveIntegration
}
