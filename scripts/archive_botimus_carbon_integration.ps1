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

$loaderPath = Join-Path $pluginsDir "plugin_botimus_prime.py"
$archiveFlagPath = Join-Path $pluginsDir "botimus_integration_archived.flag"
$runtimePluginDir = Join-Path $pluginsDir $PluginFolderName

$resolvedArchiveRoot = if ([string]::IsNullOrWhiteSpace($ArchiveRoot)) {
    Join-Path $CarbonRoot "archives\botimus_prime_reference"
} else {
    $ArchiveRoot
}
$archivePluginDir = Join-Path $resolvedArchiveRoot "plugins\$PluginFolderName"
New-Item -ItemType Directory -Path (Split-Path -Parent $archivePluginDir) -Force | Out-Null

if (Test-Path -LiteralPath $loaderPath) {
    Remove-Item -LiteralPath $loaderPath -Force
}

if (Test-Path -LiteralPath $runtimePluginDir) {
    if (Test-Path -LiteralPath $archivePluginDir) {
        Remove-Item -LiteralPath $archivePluginDir -Recurse -Force
    }
    Move-Item -LiteralPath $runtimePluginDir -Destination $archivePluginDir
}

Set-Content -LiteralPath $archiveFlagPath -Value "Botimus Carbon integration archived by default. Use restore script to re-enable." -Encoding UTF8

Write-Host "Botimus Carbon integration archived."
Write-Host "Runtime Dir : $runtimeDir"
Write-Host "Loader File : $loaderPath (removed)"
Write-Host "Runtime plugin dir moved: $runtimePluginDir -> $archivePluginDir"
Write-Host "Archive flag: $archiveFlagPath"
