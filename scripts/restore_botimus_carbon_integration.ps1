param(
    [string]$CarbonRoot = "C:\CarbonBot",
    [string]$CarbonVersion = "",
    [string]$PluginFolderName = "botimus_prime",
    [string]$ArchiveRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CarbonRoot)) {
    throw "Carbon root not found: $CarbonRoot"
}

if ([string]::IsNullOrWhiteSpace($CarbonVersion)) {
    $versions = Get-ChildItem -Path $CarbonRoot -Directory |
        Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
        Sort-Object { [version]$_.Name } -Descending
    if (-not $versions) {
        throw "No Carbon runtime version directory found under: $CarbonRoot"
    }
    $runtimeDir = $versions[0].FullName
}
else {
    $runtimeDir = Join-Path $CarbonRoot $CarbonVersion
    if (-not (Test-Path -LiteralPath $runtimeDir)) {
        throw "Requested Carbon version folder not found: $runtimeDir"
    }
}

$pluginsDir = Join-Path $runtimeDir "plugins"
if (-not (Test-Path -LiteralPath $pluginsDir)) {
    throw "Plugins directory not found: $pluginsDir"
}

$resolvedArchiveRoot = if ([string]::IsNullOrWhiteSpace($ArchiveRoot)) {
    Join-Path $CarbonRoot "archives\botimus_prime_reference"
} else {
    $ArchiveRoot
}
$archivePluginDir = Join-Path $resolvedArchiveRoot "plugins\$PluginFolderName"
$archiveTemplatePath = Join-Path $resolvedArchiveRoot "plugins\templates\plugin_botimus_prime.template.py"
if (-not (Test-Path -LiteralPath $archivePluginDir)) {
    throw "Archived Botimus reference package not found: $archivePluginDir"
}

$runtimePluginDir = Join-Path $pluginsDir $PluginFolderName
if (Test-Path -LiteralPath $runtimePluginDir) {
    Remove-Item -LiteralPath $runtimePluginDir -Recurse -Force
}
Copy-Item -LiteralPath $archivePluginDir -Destination $runtimePluginDir -Recurse -Force

$loaderPath = Join-Path $pluginsDir "plugin_botimus_prime.py"
$archiveFlagPath = Join-Path $pluginsDir "botimus_integration_archived.flag"
$templatePath = $archiveTemplatePath

if (-not (Test-Path -LiteralPath $templatePath)) {
    $fallbackLoader = @"
import pathlib
import sys

_PLUGIN_DIR = pathlib.Path(__file__).resolve().parent / "$PluginFolderName"
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from plugin_botimus import plugin_BotimusPrime
"@
    Set-Content -LiteralPath $loaderPath -Value $fallbackLoader -Encoding UTF8
} else {
    Copy-Item -LiteralPath $templatePath -Destination $loaderPath -Force
}

if (Test-Path -LiteralPath $archiveFlagPath) {
    Remove-Item -LiteralPath $archiveFlagPath -Force
}

Write-Host "Botimus Carbon integration restored."
Write-Host "Runtime Dir : $runtimeDir"
Write-Host "Archive Dir : $archivePluginDir"
Write-Host "Plugin Dir  : $runtimePluginDir"
Write-Host "Loader File : $loaderPath"
Write-Host "Template    : $templatePath"
