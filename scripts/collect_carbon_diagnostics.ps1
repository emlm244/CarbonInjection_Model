param(
    [string]$CarbonRoot = "C:\CarbonBot"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $CarbonRoot)) {
    throw "Carbon root not found: $CarbonRoot"
}

$versions = Get-ChildItem -Path $CarbonRoot -Directory |
    Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
    Sort-Object { [version]$_.Name } -Descending

if (-not $versions) {
    throw "No Carbon runtime version directory found under: $CarbonRoot"
}

$runtimeDir = $versions[0].FullName
$logsDir = Join-Path $runtimeDir "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$diagDir = Join-Path $logsDir "diagnostics"
New-Item -ItemType Directory -Path $diagDir -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$reportPath = Join-Path $diagDir "carbon_diag_$stamp.txt"

function Add-Section {
    param([string]$Title)
    Add-Content -LiteralPath $reportPath -Value ""
    Add-Content -LiteralPath $reportPath -Value "===== $Title ====="
}

Set-Content -LiteralPath $reportPath -Value ("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"))
Add-Content -LiteralPath $reportPath -Value ("Carbon root: $CarbonRoot")
Add-Content -LiteralPath $reportPath -Value ("Runtime dir: $runtimeDir")

Add-Section "Python Launcher Versions"
try {
    Add-Content -LiteralPath $reportPath -Value (py -0p | Out-String)
}
catch {
    Add-Content -LiteralPath $reportPath -Value "py launcher query failed: $($_.Exception.Message)"
}

Add-Section "Carbon Processes"
try {
    $carbon = Get-CimInstance Win32_Process -Filter "Name LIKE 'Carbon%Premium%.exe'" |
        Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine
    if ($carbon) {
        Add-Content -LiteralPath $reportPath -Value ($carbon | Format-Table -AutoSize | Out-String)
    } else {
        Add-Content -LiteralPath $reportPath -Value "No Carbon*Premium*.exe process found."
    }
}
catch {
    Add-Content -LiteralPath $reportPath -Value "Carbon process query failed: $($_.Exception.Message)"
}

Add-Section "Python Processes"
try {
    $py = Get-CimInstance Win32_Process -Filter "name='python.exe'" |
        Select-Object ProcessId, ParentProcessId, ExecutablePath, CommandLine
    if ($py) {
        Add-Content -LiteralPath $reportPath -Value ($py | Format-Table -AutoSize | Out-String)
    } else {
        Add-Content -LiteralPath $reportPath -Value "No python.exe processes found."
    }
}
catch {
    Add-Content -LiteralPath $reportPath -Value "Python process query failed: $($_.Exception.Message)"
}

Add-Section "Plugin Footprint"
$pluginLoader = Join-Path $runtimeDir "plugins\plugin_botimus_prime.py"
$pluginLoaderTemplate = Join-Path $runtimeDir "plugins\templates\plugin_botimus_prime.template.py"
$pluginArchiveFlag = Join-Path $runtimeDir "plugins\botimus_integration_archived.flag"
$pluginDir = Join-Path $runtimeDir "plugins\botimus_prime"
$integrationArchived = -not (Test-Path -LiteralPath $pluginLoader)
Add-Content -LiteralPath $reportPath -Value "Botimus integration state: $(if ($integrationArchived) { 'archived' } else { 'active' })"
Add-Content -LiteralPath $reportPath -Value "Loader exists: $(Test-Path -LiteralPath $pluginLoader)"
Add-Content -LiteralPath $reportPath -Value "Loader template exists: $(Test-Path -LiteralPath $pluginLoaderTemplate)"
Add-Content -LiteralPath $reportPath -Value "Archive flag exists: $(Test-Path -LiteralPath $pluginArchiveFlag)"
Add-Content -LiteralPath $reportPath -Value "Runtime botimus dir exists: $(Test-Path -LiteralPath $pluginDir)"
if (Test-Path -LiteralPath $pluginDir) {
    $pluginFiles = Get-ChildItem -Path $pluginDir -Recurse -File |
        Select-Object FullName, Length, LastWriteTime
    Add-Content -LiteralPath $reportPath -Value ($pluginFiles | Format-Table -AutoSize | Out-String)
}

Add-Section "Runtime Config"
$configPath = Join-Path $runtimeDir "config.json"
if (Test-Path -LiteralPath $configPath) {
    Add-Content -LiteralPath $reportPath -Value (Get-Content -Path $configPath | Out-String)
} else {
    Add-Content -LiteralPath $reportPath -Value "Missing config: $configPath"
}

Add-Section "Recent Botimus Plugin Logs"
$pluginLog = Join-Path $logsDir "botimus_plugin_runtime.log"
if ($integrationArchived) {
    Add-Content -LiteralPath $reportPath -Value "Botimus integration archived; runtime log is expected to be absent or silent."
}
elseif (Test-Path -LiteralPath $pluginLog) {
    Add-Content -LiteralPath $reportPath -Value (Get-Content -Path $pluginLog -Tail 300 | Out-String)
} else {
    Add-Content -LiteralPath $reportPath -Value "Missing log: $pluginLog"
}

Add-Section "Pipeline Verification Snapshot"
$verifyScript = Join-Path $scriptDir "verify_carbon_pipeline.ps1"
if (Test-Path -LiteralPath $verifyScript) {
    try {
        $verifyOutput = & $verifyScript -CarbonRoot $CarbonRoot 2>&1 | Out-String
        Add-Content -LiteralPath $reportPath -Value $verifyOutput
    }
    catch {
        Add-Content -LiteralPath $reportPath -Value "Pipeline verification failed: $($_.Exception.Message)"
    }
} else {
    Add-Content -LiteralPath $reportPath -Value "Missing script: $verifyScript"
}

Add-Section "Recent Carbon Launch Logs"
$launchLog = Join-Path $logsDir "carbon_launch_py311.log"
if (Test-Path -LiteralPath $launchLog) {
    Add-Content -LiteralPath $reportPath -Value (Get-Content -Path $launchLog -Tail 120 | Out-String)
} else {
    Add-Content -LiteralPath $reportPath -Value "Missing log: $launchLog"
}

Write-Host "Carbon diagnostics report written:"
Write-Host $reportPath
