param(
    [string]$CarbonExe = "",
    [string]$PythonExe = "",
    [string]$CarbonRoot = "C:\CarbonBot",
    [switch]$EnableBotimusIntegration,
    [switch]$UseNoCheckCandidate,
    [switch]$Wait
)

$ErrorActionPreference = "Stop"

function Resolve-CarbonExecutable {
    param([string]$RequestedCarbonExe)

    if (-not [string]::IsNullOrWhiteSpace($RequestedCarbonExe)) {
        if (-not (Test-Path -LiteralPath $RequestedCarbonExe)) {
            throw "Carbon executable not found: $RequestedCarbonExe"
        }
        return (Resolve-Path -LiteralPath $RequestedCarbonExe).Path
    }

    $userDownloads = Join-Path $env:USERPROFILE "Downloads"
    $candidates = @(
        (Join-Path $CarbonRoot "CarbonX Premium.exe"),
        (Join-Path $CarbonRoot "Carbon Premium.exe"),
        (Join-Path $userDownloads "CarbonX Premium.exe"),
        (Join-Path $userDownloads "Carbon Premium.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $tried = $candidates -join "; "
    throw "Carbon executable not found. Tried: $tried"
}

function Resolve-PythonExecutable {
    param([string]$RequestedPythonExe)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPythonExe)) {
        if (-not (Test-Path -LiteralPath $RequestedPythonExe)) {
            throw "Python executable not found: $RequestedPythonExe"
        }
        return (Resolve-Path -LiteralPath $RequestedPythonExe).Path
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source) {
        return $pythonCommand.Source
    }

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $candidates = @(
        (Join-Path $localAppData "RLBotGUIX\Python311\python.exe"),
        (Join-Path $localAppData "Programs\Python\Python311\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $tried = $candidates -join "; "
    throw "Python executable not found. Provide -PythonExe. Tried: $tried"
}

function Get-RunningCarbonProcesses {
    return @(
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -like "Carbon*" }
    )
}

$CarbonExe = Resolve-CarbonExecutable -RequestedCarbonExe $CarbonExe
$PythonExe = Resolve-PythonExecutable -RequestedPythonExe $PythonExe

if (-not (Test-Path -LiteralPath $CarbonExe)) {
    throw "Resolved Carbon executable not found: $CarbonExe"
}
if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Python 3.11 executable not found: $PythonExe"
}
if (-not (Test-Path -LiteralPath $CarbonRoot)) {
    throw "Carbon root not found: $CarbonRoot"
}
if ($UseNoCheckCandidate -and -not $EnableBotimusIntegration) {
    throw "-UseNoCheckCandidate requires -EnableBotimusIntegration."
}

$versions = Get-ChildItem -Path $CarbonRoot -Directory |
    Where-Object { $_.Name -match '^\d+(\.\d+)*$' } |
    Sort-Object { [version]$_.Name } -Descending

if (-not $versions) {
    throw "No Carbon runtime version directory found under: $CarbonRoot"
}

$runtimeDir = $versions[0].FullName
$botimusLoaderPath = Join-Path $runtimeDir "plugins\plugin_botimus_prime.py"
$botimusTemplatePath = Join-Path $CarbonRoot "archives\botimus_prime_reference\plugins\templates\plugin_botimus_prime.template.py"
if ($EnableBotimusIntegration -and -not (Test-Path -LiteralPath $botimusLoaderPath)) {
    throw "Botimus integration loader missing: $botimusLoaderPath. Run restore script first."
}
$logsDir = Join-Path $runtimeDir "logs"
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
$logFile = Join-Path $logsDir "carbon_launch_py311.log"
$launchSessionId = (Get-Date -Format "yyyyMMdd_HHmmss_fff")

function Write-LaunchLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"), $Message
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Format-ProcessDetails {
    param([object[]]$Processes)
    if (-not $Processes -or $Processes.Count -eq 0) {
        return ""
    }
    return (
        $Processes |
        Sort-Object ProcessName, Id |
        ForEach-Object { "$($_.ProcessName):$($_.Id)" }
    ) -join ", "
}

$existingCarbon = Get-RunningCarbonProcesses
if ($existingCarbon.Count -gt 0) {
    $details = Format-ProcessDetails -Processes $existingCarbon
    Write-LaunchLog "LAUNCH_PREFLIGHT_BLOCKED session=$launchSessionId blockers=$details"
    Write-LaunchLog "Manual gate required: close all Carbon and RocketLeague-related processes, then relaunch once."
    throw "Carbon appears to be running ($details). Manual gate required: close all Carbon and Rocket League processes before launching."
}

$pythonDir = Split-Path -Parent $PythonExe
$pythonScriptsDir = Join-Path $pythonDir "Scripts"

$oldPath = $env:Path
$oldPyPython = $env:PY_PYTHON
$oldPyPython3 = $env:PY_PYTHON3
$oldExpected = $env:BOTIMUS_EXPECTED_PYTHON
$oldCoreFailMode = $env:BOTIMUS_CORE_FAIL_MODE
$oldRluCandidates = $env:BOTIMUS_RLUTILITIES_CANDIDATES
$oldAllowNoCheck = $env:BOTIMUS_ALLOW_NOCHECK_RLUTILITIES
$oldAutoNoCheck = $env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES
$oldForceUnsafeCoreImport = $env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT
$oldPacketReadMode = $env:BOTIMUS_PACKET_READ_MODE
$oldArchived = $env:BOTIMUS_CARBON_ARCHIVED
$oldSilentArchive = $env:BOTIMUS_CARBON_SILENT_ARCHIVE

try {
    $launchMode = if ($UseNoCheckCandidate) { "experimental" } else { "safety" }
    $integrationMode = if ($EnableBotimusIntegration) { "active" } else { "archived" }
    Write-LaunchLog "LAUNCH_SESSION_START id=$launchSessionId mode=$launchMode use_nocheck=$([bool]$UseNoCheckCandidate) botimus_integration=$integrationMode"

    $env:PY_PYTHON = "3.11"
    $env:PY_PYTHON3 = "3.11"
    $env:BOTIMUS_CARBON_SILENT_ARCHIVE = "1"
    if ($EnableBotimusIntegration) {
        $env:BOTIMUS_CARBON_ARCHIVED = "0"
        $env:BOTIMUS_EXPECTED_PYTHON = $PythonExe
        $env:BOTIMUS_CORE_FAIL_MODE = "passthrough"
        $env:BOTIMUS_PACKET_READ_MODE = "compat"
        if ($UseNoCheckCandidate) {
            $env:BOTIMUS_ALLOW_NOCHECK_RLUTILITIES = "1"
            $env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES = "1"
            $env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT = "1"
        } else {
            Remove-Item Env:BOTIMUS_ALLOW_NOCHECK_RLUTILITIES -ErrorAction SilentlyContinue
            $env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES = "0"
            Remove-Item Env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT -ErrorAction SilentlyContinue
        }

        $candidatePaths = @()
        if ($UseNoCheckCandidate) {
            $candidatePaths += (Join-Path $runtimeDir "plugins\botimus_prime\rlutilities\rlutilities.carb3110_nocheck.cp311-win_amd64.pyd")
        }
        $candidatePaths += @(
            (Join-Path $runtimeDir "plugins\botimus_prime\rlutilities\rlutilities.carb3110_nopyver2.cp311-win_amd64.pyd"),
            (Join-Path $runtimeDir "plugins\botimus_prime\rlutilities\rlutilities.carb3110_nopyver.cp311-win_amd64.pyd"),
            (Join-Path $runtimeDir "plugins\botimus_prime\rlutilities\rlutilities.carb3110.cp311-win_amd64.pyd")
        )

        if ($UseNoCheckCandidate) {
            Write-LaunchLog "Experimental mode enabled: nocheck RLUtilities candidate allowed."
        } else {
            Write-LaunchLog "Safety mode enabled: unsafe core import guard active; nocheck disabled."
        }
        $forceUnsafeValue = if ([string]::IsNullOrWhiteSpace($env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT)) { "<unset>" } else { $env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT }
        Write-LaunchLog "LAUNCH_MODE session=$launchSessionId mode=$launchMode auto_nocheck=$($env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES) force_unsafe_core_import=$forceUnsafeValue packet_read_mode=$($env:BOTIMUS_PACKET_READ_MODE) botimus_integration=active"

        $candidateRlu = $candidatePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if ($candidateRlu) {
            $env:BOTIMUS_RLUTILITIES_CANDIDATES = $candidateRlu
            Write-LaunchLog "Using RLUtilities candidate: $candidateRlu"
            Write-LaunchLog "LAUNCH_RLUTILITIES_CANDIDATE session=$launchSessionId resolved=true path=$candidateRlu"
        } else {
            $env:BOTIMUS_RLUTILITIES_CANDIDATES = ""
            Write-LaunchLog "No explicit RLUtilities candidate found; using default plugin discovery."
            Write-LaunchLog "LAUNCH_RLUTILITIES_CANDIDATE session=$launchSessionId resolved=false path=<default_discovery>"
        }
    } else {
        $env:BOTIMUS_CARBON_ARCHIVED = "1"
        Remove-Item Env:BOTIMUS_EXPECTED_PYTHON -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_CORE_FAIL_MODE -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_RLUTILITIES_CANDIDATES -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_ALLOW_NOCHECK_RLUTILITIES -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT -ErrorAction SilentlyContinue
        Remove-Item Env:BOTIMUS_PACKET_READ_MODE -ErrorAction SilentlyContinue
        Write-LaunchLog "LAUNCH_MODE session=$launchSessionId mode=$launchMode botimus_integration=archived template=$botimusTemplatePath"
    }

    $env:Path = "$pythonDir;$pythonScriptsDir;$oldPath"

    Write-LaunchLog "Launching Carbon with process-local Python 3.11 binding."
    Write-LaunchLog "CarbonExe=$CarbonExe"
    Write-LaunchLog "PythonExe=$PythonExe"
    Write-LaunchLog "RuntimeDir=$runtimeDir"
    Write-LaunchLog "BotimusLoaderPath=$botimusLoaderPath exists=$(Test-Path -LiteralPath $botimusLoaderPath)"

    $proc = Start-Process -FilePath $CarbonExe -WorkingDirectory (Split-Path -Parent $CarbonExe) -PassThru
    Write-LaunchLog "Carbon process started pid=$($proc.Id)"

    if ($Wait) {
        $proc.WaitForExit()
        Write-LaunchLog "Carbon process exited code=$($proc.ExitCode)"
    }
}
finally {
    $env:Path = $oldPath
    $env:PY_PYTHON = $oldPyPython
    $env:PY_PYTHON3 = $oldPyPython3
    $env:BOTIMUS_EXPECTED_PYTHON = $oldExpected
    $env:BOTIMUS_CORE_FAIL_MODE = $oldCoreFailMode
    $env:BOTIMUS_RLUTILITIES_CANDIDATES = $oldRluCandidates
    $env:BOTIMUS_ALLOW_NOCHECK_RLUTILITIES = $oldAllowNoCheck
    $env:BOTIMUS_AUTO_NOCHECK_RLUTILITIES = $oldAutoNoCheck
    $env:BOTIMUS_FORCE_UNSAFE_CORE_IMPORT = $oldForceUnsafeCoreImport
    $env:BOTIMUS_PACKET_READ_MODE = $oldPacketReadMode
    $env:BOTIMUS_CARBON_ARCHIVED = $oldArchived
    $env:BOTIMUS_CARBON_SILENT_ARCHIVE = $oldSilentArchive
}
