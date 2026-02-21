param(
    [string]$CarbonRoot = "C:\CarbonBot",
    [string]$CarbonVersion = "",
    [string]$PluginFolderName = "botimus_prime",
    [string]$SourceRoot = "",
    [switch]$EnableBotimusIntegration
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$requiredSourceDirs = @(
    "data",
    "maneuvers",
    "runtime",
    "strategy",
    "tools",
    "rlutilities"
)
$requiredSourceFiles = @(
    "plugin_botimus.py",
    "botimus_settings.ini",
    "CARBONX_PLUGIN_SETUP.md"
)

function Test-BotimusSourceRoot {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    foreach ($dir in $requiredSourceDirs) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $dir))) {
            return $false
        }
    }
    foreach ($file in $requiredSourceFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $file))) {
            return $false
        }
    }
    return $true
}

function Resolve-BotimusSourceRoot {
    param(
        [string]$ExplicitSourceRoot,
        [string]$ScriptDir
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitSourceRoot)) {
        $resolved = Resolve-Path -LiteralPath $ExplicitSourceRoot -ErrorAction SilentlyContinue
        $candidate = if ($resolved) { $resolved.Path } else { $ExplicitSourceRoot }
        if (Test-BotimusSourceRoot -Path $candidate) {
            return $candidate
        }
        throw "Provided -SourceRoot is not a valid Botimus source root: $ExplicitSourceRoot"
    }

    $repoRoot = Split-Path -Parent $ScriptDir
    $candidates = @(
        $env:BOTIMUS_SOURCE_ROOT,
        (Join-Path $repoRoot "plugin\botimus_prime"),
        $repoRoot,
        (Get-Location).Path
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique

    foreach ($candidatePath in $candidates) {
        $resolved = Resolve-Path -LiteralPath $candidatePath -ErrorAction SilentlyContinue
        $candidate = if ($resolved) { $resolved.Path } else { $candidatePath }
        if (Test-BotimusSourceRoot -Path $candidate) {
            return $candidate
        }
    }

    $tried = $candidates -join "; "
    throw "Could not locate Botimus source root. Tried: $tried. Pass -SourceRoot <path-to-Botimus>."
}

$sourceRoot = Resolve-BotimusSourceRoot -ExplicitSourceRoot $SourceRoot -ScriptDir $scriptDir

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
} else {
    $runtimeDir = Join-Path $CarbonRoot $CarbonVersion
    if (-not (Test-Path -LiteralPath $runtimeDir)) {
        throw "Requested Carbon version folder not found: $runtimeDir"
    }
}

$runningCarbon = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ProcessName -like "Carbon*" }
if ($runningCarbon) {
    $pids = ($runningCarbon | Select-Object -ExpandProperty Id) -join ", "
    throw "Carbon appears to be running (PID(s): $pids). Close Carbon completely before installing the plugin."
}

$pluginsDir = Join-Path $runtimeDir "plugins"
New-Item -ItemType Directory -Path $pluginsDir -Force | Out-Null

$targetDir = Join-Path $pluginsDir $PluginFolderName
if (Test-Path -LiteralPath $targetDir) {
    Remove-Item -LiteralPath $targetDir -Recurse -Force
}
New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

$copyDirs = $requiredSourceDirs
foreach ($dir in $copyDirs) {
    $src = Join-Path $sourceRoot $dir
    if (-not (Test-Path -LiteralPath $src)) {
        throw "Missing required source directory: $src"
    }
    Copy-Item -LiteralPath $src -Destination (Join-Path $targetDir $dir) -Recurse -Force
}

$copyFiles = $requiredSourceFiles
foreach ($fileName in $copyFiles) {
    $src = Join-Path $sourceRoot $fileName
    if (-not (Test-Path -LiteralPath $src)) {
        throw "Missing required source file: $src"
    }
    Copy-Item -LiteralPath $src -Destination (Join-Path $targetDir $fileName) -Force
}

$loaderPath = Join-Path $pluginsDir "plugin_botimus_prime.py"
$templatesDir = Join-Path $pluginsDir "templates"
New-Item -ItemType Directory -Path $templatesDir -Force | Out-Null
$loaderTemplatePath = Join-Path $templatesDir "plugin_botimus_prime.template.py"
$archiveFlagPath = Join-Path $pluginsDir "botimus_integration_archived.flag"
$loaderCode = @"
import pathlib
import sys

_PLUGIN_DIR = pathlib.Path(__file__).resolve().parent / "$PluginFolderName"
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from plugin_botimus import plugin_BotimusPrime
"@
Set-Content -LiteralPath $loaderTemplatePath -Value $loaderCode -Encoding UTF8

if ($EnableBotimusIntegration) {
    Set-Content -LiteralPath $loaderPath -Value $loaderCode -Encoding UTF8
    if (Test-Path -LiteralPath $archiveFlagPath) {
        Remove-Item -LiteralPath $archiveFlagPath -Force
    }
} else {
    if (Test-Path -LiteralPath $loaderPath) {
        Remove-Item -LiteralPath $loaderPath -Force
    }
    Set-Content -LiteralPath $archiveFlagPath -Value "Botimus Carbon integration archived by default. Use restore script or re-run installer with -EnableBotimusIntegration." -Encoding UTF8
}

$templateNotesPath = Join-Path $templatesDir "README_botimus_integration_template.md"
$templateNotes = @"
Botimus Carbon Loader Template

Use this loader as a reference when creating or re-enabling a Carbon plugin integration.

Required callback contract
- Class name: `plugin_BotimusPrime`
- Callback: `game_tick_packet_set(packet, local_player_index, playername, process_id)`
- Return: `SimpleControllerState` or `None` for passthrough

Re-enable from template
Copy `plugin_botimus_prime.template.py` to `plugins\plugin_botimus_prime.py`.
"@
Set-Content -LiteralPath $templateNotesPath -Value $templateNotes -Encoding UTF8

foreach ($dir in $copyDirs) {
    $requiredPath = Join-Path $targetDir $dir
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Post-install verification failed (missing directory): $requiredPath"
    }
}

$requiredFiles = @(
    "data\acceleration\boost.csv",
    "maneuvers\maneuver.py",
    "runtime\botimus_core.py",
    "strategy\solo_strategy.py",
    "tools\game_info.py",
    "rlutilities\__init__.py",
    "rlutilities\assets\soccar\soccar_corner_vertices.bin",
    "plugin_botimus.py",
    "botimus_settings.ini",
    "CARBONX_PLUGIN_SETUP.md"
)
foreach ($relativePath in $requiredFiles) {
    $requiredPath = Join-Path $targetDir $relativePath
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Post-install verification failed (missing runtime asset/file): $requiredPath"
    }
}

if (-not (Test-Path -LiteralPath $loaderTemplatePath)) {
    throw "Post-install verification failed (missing loader template): $loaderTemplatePath"
}
if ($EnableBotimusIntegration -and -not (Test-Path -LiteralPath $loaderPath)) {
    throw "Post-install verification failed (missing loader): $loaderPath"
}
if (-not $EnableBotimusIntegration -and (Test-Path -LiteralPath $loaderPath)) {
    throw "Post-install verification failed (loader should be archived): $loaderPath"
}

Write-Host "Installed Botimus Carbon plugin."
Write-Host "Runtime Dir : $runtimeDir"
Write-Host "Plugin Dir  : $targetDir"
Write-Host "Loader Tpl  : $loaderTemplatePath"
if ($EnableBotimusIntegration) {
    Write-Host "Botimus integration state : ACTIVE"
    Write-Host "Loader File : $loaderPath"
} else {
    Write-Host "Botimus integration state : ARCHIVED (default)"
    Write-Host "Archive flag : $archiveFlagPath"
}
