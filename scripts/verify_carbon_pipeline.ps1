param(
    [string]$CarbonRoot = "C:\CarbonBot",
    [string]$CarbonVersion = "",
    [switch]$RequireCoreReady,
    [switch]$RequireActiveIntegration
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
} else {
    $runtimeDir = Join-Path $CarbonRoot $CarbonVersion
    if (-not (Test-Path -LiteralPath $runtimeDir)) {
        throw "Requested Carbon version folder not found: $runtimeDir"
    }
}

$logsDir = Join-Path $runtimeDir "logs"
$runtimeLog = Join-Path $logsDir "botimus_plugin_runtime.log"
$launchLog = Join-Path $logsDir "carbon_launch_py311.log"
$pluginsDir = Join-Path $runtimeDir "plugins"
$botimusLoader = Join-Path $pluginsDir "plugin_botimus_prime.py"
$botimusTemplate = Join-Path $pluginsDir "templates\plugin_botimus_prime.template.py"
$botimusArchiveFlag = Join-Path $pluginsDir "botimus_integration_archived.flag"

$integrationArchived = -not (Test-Path -LiteralPath $botimusLoader)
$integrationState = if ($integrationArchived) { "archived" } else { "active" }

if ($integrationArchived) {
    Write-Output "Botimus Carbon Pipeline Verification"
    Write-Output "RuntimeDir: $runtimeDir"
    Write-Output "RuntimeLog: $runtimeLog"
    if (Test-Path -LiteralPath $launchLog) {
        Write-Output "LaunchLog: $launchLog"
    } else {
        Write-Output "LaunchLog: missing"
    }
    Write-Output ""
    Write-Output "Status:"
    Write-Output "  integration_state: archived"
    Write-Output "  plugin_loaded: False"
    Write-Output "  core_state: archived_disabled"
    Write-Output "  packet_stream_active: False"
    Write-Output "  botimus_loader_present: $(Test-Path -LiteralPath $botimusLoader)"
    Write-Output "  botimus_template_present: $(Test-Path -LiteralPath $botimusTemplate)"
    Write-Output "  botimus_archive_flag_present: $(Test-Path -LiteralPath $botimusArchiveFlag)"
    Write-Output ""
    Write-Output "Next step:"
    Write-Output "  Botimus integration is intentionally archived and silent in this runtime."
    Write-Output "  Re-enable with scripts\restore_botimus_carbon_integration.ps1"
    Write-Output "  Then relaunch with -EnableBotimusIntegration if you need Botimus controls again."
    if ($RequireActiveIntegration) {
        exit 3
    }
    if ($RequireCoreReady) {
        exit 2
    }
    return
}

if (-not (Test-Path -LiteralPath $runtimeLog)) {
    Write-Output "Botimus Carbon Pipeline Verification"
    Write-Output "RuntimeDir: $runtimeDir"
    Write-Output "RuntimeLog: missing"
    if (Test-Path -LiteralPath $launchLog) {
        Write-Output "LaunchLog: $launchLog"
    } else {
        Write-Output "LaunchLog: missing"
    }
    Write-Output ""
    Write-Output "Status:"
    Write-Output "  integration_state: active"
    Write-Output "  plugin_loaded: unknown"
    Write-Output "  core_state: unknown_no_runtime_log"
    Write-Output "  packet_stream_active: unknown"
    Write-Output "  botimus_loader_present: $(Test-Path -LiteralPath $botimusLoader)"
    Write-Output "  botimus_template_present: $(Test-Path -LiteralPath $botimusTemplate)"
    Write-Output "  botimus_archive_flag_present: $(Test-Path -LiteralPath $botimusArchiveFlag)"
    Write-Output ""
    Write-Output "Next step:"
    Write-Output "  Launch Carbon once to generate runtime logs, then re-run verification for live control state."
    if ($RequireCoreReady) {
        exit 2
    }
    return
}

function Test-IsCarbonAppCrashMessage {
    param([string]$Message)
    if ([string]::IsNullOrWhiteSpace($Message)) {
        return $false
    }
    return $Message -match 'Faulting application name:\s*Carbon(?:X)? Premium\.exe'
}

function New-EventList {
    return New-Object System.Collections.Generic.List[object]
}

function Add-Event {
    param(
        [System.Collections.Generic.List[object]]$List,
        [int]$Index,
        [string]$Line
    )
    $timestamp = ""
    if ($Line -match '^\[(?<ts>[^\]]+)\]') {
        $timestamp = $Matches.ts
    }
    $List.Add([pscustomobject]@{
            Index = $Index
            Time = $timestamp
            Line = $Line
        })
}

$events = @{
    plugin_init = New-EventList
    core_import_ok = New-EventList
    core_import_guard = New-EventList
    core_import_guard_block = New-EventList
    core_import_blocked_by_guard = New-EventList
    core_ready = New-EventList
    core_import_fail = New-EventList
    core_init_fail = New-EventList
    packet_stream = New-EventList
    tick_heartbeat = New-EventList
    passthrough = New-EventList
    passthrough_heartbeat = New-EventList
    fallback = New-EventList
    bot_enable = New-EventList
    watchdog_no_tick = New-EventList
}

$lines = Get-Content -LiteralPath $runtimeLog
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = [string]$lines[$i]
    if ($line -match '\] PLUGIN_INIT ') { Add-Event -List $events.plugin_init -Index $i -Line $line }
    if ($line -match '\] CORE_IMPORT_OK\b') { Add-Event -List $events.core_import_ok -Index $i -Line $line }
    if ($line -match '\] CORE_IMPORT_GUARD ') { Add-Event -List $events.core_import_guard -Index $i -Line $line }
    if ($line -match '\] CORE_IMPORT_GUARD_BLOCK\b') { Add-Event -List $events.core_import_guard_block -Index $i -Line $line }
    if ($line -match '\] CORE_IMPORT_BLOCKED_BY_GUARD\b') { Add-Event -List $events.core_import_blocked_by_guard -Index $i -Line $line }
    if ($line -match '\] CORE_READY ') { Add-Event -List $events.core_ready -Index $i -Line $line }
    if ($line -match '\] CORE_IMPORT_FAIL') { Add-Event -List $events.core_import_fail -Index $i -Line $line }
    if ($line -match '\] CORE_INIT_FAIL') { Add-Event -List $events.core_init_fail -Index $i -Line $line }
    if ($line -match '\] PACKET_STREAM_ACTIVE ') { Add-Event -List $events.packet_stream -Index $i -Line $line }
    if ($line -match '\] TICK_HEARTBEAT ') { Add-Event -List $events.tick_heartbeat -Index $i -Line $line }
    if ($line -match '\] CONTROLLER_PASSTHROUGH ') { Add-Event -List $events.passthrough -Index $i -Line $line }
    if ($line -match '\] PASSTHROUGH_HEARTBEAT ') { Add-Event -List $events.passthrough_heartbeat -Index $i -Line $line }
    if ($line -match '\] FALLBACK_CONTROLLER_ACTIVE ') { Add-Event -List $events.fallback -Index $i -Line $line }
    if ($line -match '\] BOT_ENABLE_REQUESTED ') { Add-Event -List $events.bot_enable -Index $i -Line $line }
    if ($line -match '\] WATCHDOG_NO_TICK ') { Add-Event -List $events.watchdog_no_tick -Index $i -Line $line }
}

$latestInit = if ($events.plugin_init.Count -gt 0) { $events.plugin_init[$events.plugin_init.Count - 1] } else { $null }
$sessionStartIndex = if ($latestInit) { [int]$latestInit.Index } else { 0 }

function Filter-SessionEvents {
    param(
        [System.Collections.Generic.List[object]]$EventList,
        [int]$StartIndex
    )
    return @($EventList | Where-Object { $_.Index -ge $StartIndex })
}

$sessionEvents = @{
    core_import_ok = Filter-SessionEvents -EventList $events.core_import_ok -StartIndex $sessionStartIndex
    core_import_guard = Filter-SessionEvents -EventList $events.core_import_guard -StartIndex $sessionStartIndex
    core_import_guard_block = Filter-SessionEvents -EventList $events.core_import_guard_block -StartIndex $sessionStartIndex
    core_import_blocked_by_guard = Filter-SessionEvents -EventList $events.core_import_blocked_by_guard -StartIndex $sessionStartIndex
    core_ready = Filter-SessionEvents -EventList $events.core_ready -StartIndex $sessionStartIndex
    core_import_fail = Filter-SessionEvents -EventList $events.core_import_fail -StartIndex $sessionStartIndex
    core_init_fail = Filter-SessionEvents -EventList $events.core_init_fail -StartIndex $sessionStartIndex
    packet_stream = Filter-SessionEvents -EventList $events.packet_stream -StartIndex $sessionStartIndex
    tick_heartbeat = Filter-SessionEvents -EventList $events.tick_heartbeat -StartIndex $sessionStartIndex
    passthrough = Filter-SessionEvents -EventList $events.passthrough -StartIndex $sessionStartIndex
    passthrough_heartbeat = Filter-SessionEvents -EventList $events.passthrough_heartbeat -StartIndex $sessionStartIndex
    fallback = Filter-SessionEvents -EventList $events.fallback -StartIndex $sessionStartIndex
    bot_enable = Filter-SessionEvents -EventList $events.bot_enable -StartIndex $sessionStartIndex
    watchdog_no_tick = Filter-SessionEvents -EventList $events.watchdog_no_tick -StartIndex $sessionStartIndex
}

function Get-EventCount {
    param(
        [hashtable]$Map,
        [string]$Key
    )
    $value = $Map[$Key]
    if ($null -eq $value) {
        return 0
    }
    return @($value).Count
}

$pluginLoaded = $latestInit -ne $null
$coreImported = (Get-EventCount -Map $sessionEvents -Key "core_import_ok") -gt 0
$coreReady = (Get-EventCount -Map $sessionEvents -Key "core_ready") -gt 0
$coreGuardBlocked = ((Get-EventCount -Map $sessionEvents -Key "core_import_guard_block") -gt 0) -or ((Get-EventCount -Map $sessionEvents -Key "core_import_blocked_by_guard") -gt 0)
$coreImportFailed = (Get-EventCount -Map $sessionEvents -Key "core_import_fail") -gt 0
$coreInitFailed = (Get-EventCount -Map $sessionEvents -Key "core_init_fail") -gt 0
$coreFailed = $coreGuardBlocked -or $coreImportFailed -or $coreInitFailed
$packetActive = (Get-EventCount -Map $sessionEvents -Key "packet_stream") -gt 0
$heartbeatActive = (Get-EventCount -Map $sessionEvents -Key "tick_heartbeat") -gt 0
$passthroughActive = (Get-EventCount -Map $sessionEvents -Key "passthrough") -gt 0
$passthroughHeartbeatActive = (Get-EventCount -Map $sessionEvents -Key "passthrough_heartbeat") -gt 0
$packetAndPassthroughHeartbeat = $packetActive -and $passthroughHeartbeatActive
$fallbackActive = (Get-EventCount -Map $sessionEvents -Key "fallback") -gt 0

$coreState = "unknown"
if ($coreReady) {
    $coreState = "ready"
} elseif ($coreGuardBlocked) {
    $coreState = "guard_blocked"
} elseif ($coreInitFailed) {
    $coreState = "init_failed"
} elseif ($coreImportFailed) {
    $coreState = "import_failed"
} elseif ($coreImported) {
    $coreState = "import_ok_waiting_for_packets"
}

$coreFailureBucket = "none"
if (-not $coreReady) {
    if ($coreGuardBlocked) {
        $coreFailureBucket = "guard_blocked"
    } elseif ($coreInitFailed) {
        $coreFailureBucket = "init_failed"
    } elseif ($coreImportFailed) {
        $coreFailureBucket = "import_failed"
    } elseif ($coreImported) {
        $coreFailureBucket = "waiting_for_packets"
    } else {
        $coreFailureBucket = "unknown"
    }
}

$controlState = "unknown"
if ($coreReady) {
    $controlState = "botimus_controls"
} elseif ($passthroughActive) {
    $controlState = "passthrough_selected_model"
} elseif ($fallbackActive) {
    $controlState = "fallback_controller"
}

$candidateLine = $null
$launchSessionLine = $null
$launchModeLine = $null
$latestLaunch = $null
if (Test-Path -LiteralPath $launchLog) {
    $launchLines = Get-Content -LiteralPath $launchLog
    $launchSessionLine = $launchLines |
        Where-Object { $_ -match "LAUNCH_SESSION_START " } |
        Select-Object -Last 1
    $launchModeLine = $launchLines |
        Where-Object { $_ -match "LAUNCH_MODE " } |
        Select-Object -Last 1
    $candidateLine = $launchLines |
        Where-Object { $_ -match "Using RLUtilities candidate:" } |
        Select-Object -Last 1

    $latestLaunchLine = $launchLines |
        Where-Object { $_ -match "Carbon process started pid=" } |
        Select-Object -Last 1
    if ($latestLaunchLine -and $latestLaunchLine -match '^\[(?<ts>[^\]]+)\].*pid=(?<pid>\d+)') {
        $launchTs = $null
        try {
            $launchTs = [datetime]::Parse($Matches.ts)
        } catch {
            $launchTs = $null
        }
        $latestLaunch = [pscustomobject]@{
            Time = $launchTs
            Pid = [int]$Matches.pid
            Line = $latestLaunchLine
        }
    }
}

$latestInitTime = $null
if ($latestInit -and -not [string]::IsNullOrWhiteSpace($latestInit.Time)) {
    try {
        $latestInitTime = [datetime]::Parse($latestInit.Time)
    } catch {
        $latestInitTime = $null
    }
}

$latestLaunchAfterInit = $false
if ($latestLaunch -and $latestLaunch.Time -and $latestInitTime) {
    $latestLaunchAfterInit = $latestLaunch.Time -gt $latestInitTime
}

$latestRlCrash = $null
try {
    $rlCrashFilter = @{
        LogName = "Application"
        ProviderName = "Application Error"
    }
    if ($latestLaunch -and $latestLaunch.Time) {
        $rlCrashFilter.StartTime = $latestLaunch.Time
    }
    $latestRlCrash = Get-WinEvent -FilterHashtable $rlCrashFilter -ErrorAction Stop |
        Where-Object { $_.Message -like "*Faulting application name: RocketLeague.exe*" } |
        Select-Object -First 1
} catch {
    $latestRlCrash = $null
}

$latestCrashAny = $null
try {
    $crashFilter = @{
        LogName = "Application"
        ProviderName = "Application Error"
    }
    if ($latestInit -and -not [string]::IsNullOrWhiteSpace($latestInit.Time)) {
        try {
            $crashFilter.StartTime = [datetime]::Parse($latestInit.Time)
        } catch {
        }
    }

    $latestCrashAny = Get-WinEvent -FilterHashtable $crashFilter -ErrorAction Stop |
        Where-Object { Test-IsCarbonAppCrashMessage -Message $_.Message } |
        Select-Object -First 1
} catch {
    $latestCrashAny = $null
}

$latestCrashSinceLaunch = $null
try {
    $crashFilterSinceLaunch = @{
        LogName = "Application"
        ProviderName = "Application Error"
    }
    if ($latestLaunch -and $latestLaunch.Time) {
        $crashFilterSinceLaunch.StartTime = $latestLaunch.Time
    }
    $latestCrashSinceLaunch = Get-WinEvent -FilterHashtable $crashFilterSinceLaunch -ErrorAction Stop |
        Where-Object { Test-IsCarbonAppCrashMessage -Message $_.Message } |
        Select-Object -First 1
} catch {
    $latestCrashSinceLaunch = $null
}

$latestLaunchPidAlive = $false
$latestLaunchChildPid = $null
if ($latestLaunch -and $latestLaunch.Pid) {
    try {
        $proc = Get-Process -Id $latestLaunch.Pid -ErrorAction Stop
        $latestLaunchPidAlive = $null -ne $proc
    } catch {
        $latestLaunchPidAlive = $false
    }
}

$latestLaunchTreeAlive = $latestLaunchPidAlive
if (-not $latestLaunchTreeAlive -and $latestLaunch -and $latestLaunch.Pid) {
    try {
        $child = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($latestLaunch.Pid) AND (Name = 'Carbon Premium.exe' OR Name = 'CarbonX Premium.exe')" -ErrorAction Stop |
            Select-Object -First 1
        if ($child) {
            $latestLaunchTreeAlive = $true
            $latestLaunchChildPid = [int]$child.ProcessId
        }
    } catch {
        $latestLaunchTreeAlive = $false
    }
}

Write-Output "Botimus Carbon Pipeline Verification"
Write-Output "RuntimeDir: $runtimeDir"
Write-Output "RuntimeLog: $runtimeLog"
if (Test-Path -LiteralPath $launchLog) {
    Write-Output "LaunchLog: $launchLog"
} else {
    Write-Output "LaunchLog: missing"
}
Write-Output ""
Write-Output "Session anchor:"
if ($latestInit) {
    Write-Output "  Latest PLUGIN_INIT: $($latestInit.Time)"
    Write-Output "  $($latestInit.Line)"
} else {
    Write-Output "  No PLUGIN_INIT marker found."
}
if ($candidateLine) {
    Write-Output "  Last candidate line: $candidateLine"
}
if ($launchSessionLine) {
    Write-Output "  Last launch session: $launchSessionLine"
}
if ($launchModeLine) {
    Write-Output "  Last launch mode: $launchModeLine"
}
Write-Output ""
Write-Output "Status:"
Write-Output "  integration_state: $integrationState"
Write-Output "  plugin_loaded: $pluginLoaded"
Write-Output "  core_state: $coreState"
Write-Output "  core_failure_bucket: $coreFailureBucket"
Write-Output "  packet_stream_active: $packetActive"
Write-Output "  tick_heartbeat_seen: $heartbeatActive"
Write-Output "  passthrough_heartbeat_seen: $passthroughHeartbeatActive"
Write-Output "  packet_and_passthrough_heartbeat_after_init: $packetAndPassthroughHeartbeat"
Write-Output "  control_mode: $controlState"
if ($latestCrashSinceLaunch) {
    $faultModule = ""
    $faultPidHex = ""
    if ($latestCrashSinceLaunch.Message -match 'Faulting module name:\s*(?<mod>[^,\r\n]+)') {
        $faultModule = $Matches.mod
    }
    if ($latestCrashSinceLaunch.Message -match 'Faulting process id:\s*0x(?<pid>[0-9a-fA-F]+)') {
        $faultPidHex = "0x$($Matches.pid)"
    }
    $faultPidDec = ""
    if (-not [string]::IsNullOrWhiteSpace($faultPidHex)) {
        try {
            $faultPidDec = [Convert]::ToInt32($faultPidHex, 16).ToString()
        } catch {
            $faultPidDec = ""
        }
    }
    Write-Output "  latest_app_crash_since_latest_launch: True"
    if (-not [string]::IsNullOrWhiteSpace($faultModule)) {
        Write-Output "  latest_app_crash_module: $faultModule"
    }
    if (-not [string]::IsNullOrWhiteSpace($faultPidHex)) {
        if (-not [string]::IsNullOrWhiteSpace($faultPidDec)) {
            Write-Output "  latest_app_crash_pid: $faultPidHex ($faultPidDec)"
        } else {
            Write-Output "  latest_app_crash_pid: $faultPidHex"
        }
    }
} else {
    Write-Output "  latest_app_crash_since_latest_launch: False"
}
if ($latestLaunchTreeAlive) {
    if ($latestLaunchPidAlive) {
        Write-Output "  latest_launch_tree_alive: True (parent pid=$($latestLaunch.Pid))"
    } elseif ($latestLaunchChildPid) {
        Write-Output "  latest_launch_tree_alive: True (child pid=$latestLaunchChildPid, parent pid=$($latestLaunch.Pid))"
    } else {
        Write-Output "  latest_launch_tree_alive: True"
    }
} else {
    Write-Output "  latest_launch_tree_alive: False"
}
if ($latestLaunchAfterInit) {
    Write-Output "  plugin_init_seen_for_latest_launch: False"
} else {
    Write-Output "  plugin_init_seen_for_latest_launch: True"
}
if ($latestRlCrash) {
    Write-Output "  rocketleague_crash_after_latest_launch: True"
} else {
    Write-Output "  rocketleague_crash_after_latest_launch: False"
}
Write-Output ""

function Write-LatestEvent {
    param(
        [string]$Title,
        [object[]]$List
    )
    if ($List.Count -eq 0) {
        return
    }
    $last = $List[$List.Count - 1]
    Write-Output "${Title}: $($last.Line)"
}

Write-LatestEvent -Title "Latest CORE_IMPORT_OK" -List $sessionEvents.core_import_ok
Write-LatestEvent -Title "Latest CORE_IMPORT_GUARD" -List $sessionEvents.core_import_guard
Write-LatestEvent -Title "Latest CORE_IMPORT_GUARD_BLOCK" -List $sessionEvents.core_import_guard_block
Write-LatestEvent -Title "Latest CORE_IMPORT_BLOCKED_BY_GUARD" -List $sessionEvents.core_import_blocked_by_guard
Write-LatestEvent -Title "Latest CORE_READY" -List $sessionEvents.core_ready
Write-LatestEvent -Title "Latest CORE_IMPORT_FAIL" -List $sessionEvents.core_import_fail
Write-LatestEvent -Title "Latest CORE_INIT_FAIL" -List $sessionEvents.core_init_fail
Write-LatestEvent -Title "Latest PACKET_STREAM_ACTIVE" -List $sessionEvents.packet_stream
Write-LatestEvent -Title "Latest TICK_HEARTBEAT" -List $sessionEvents.tick_heartbeat
Write-LatestEvent -Title "Latest CONTROLLER_PASSTHROUGH" -List $sessionEvents.passthrough
Write-LatestEvent -Title "Latest PASSTHROUGH_HEARTBEAT" -List $sessionEvents.passthrough_heartbeat
Write-LatestEvent -Title "Latest FALLBACK_CONTROLLER_ACTIVE" -List $sessionEvents.fallback
Write-LatestEvent -Title "Latest BOT_ENABLE_REQUESTED" -List $sessionEvents.bot_enable
Write-LatestEvent -Title "Latest WATCHDOG_NO_TICK" -List $sessionEvents.watchdog_no_tick
if ($latestCrashSinceLaunch) {
    Write-Output "Latest APP_CRASH_SINCE_LAUNCH: [$($latestCrashSinceLaunch.TimeCreated)] Application Error id=$($latestCrashSinceLaunch.Id)"
} elseif ($latestCrashAny) {
    Write-Output "Latest APP_CRASH_ANY: [$($latestCrashAny.TimeCreated)] Application Error id=$($latestCrashAny.Id)"
}
if ($latestLaunchAfterInit -and $latestLaunch) {
    Write-Output "Latest launch with no subsequent PLUGIN_INIT: $($latestLaunch.Line)"
}
if ($latestRlCrash) {
    $rlModule = ""
    if ($latestRlCrash.Message -match 'Faulting module name:\s*(?<mod>[^,\r\n]+)') {
        $rlModule = $Matches.mod
    }
    if (-not [string]::IsNullOrWhiteSpace($rlModule)) {
        Write-Output "Latest ROCKETLEAGUE_CRASH: [$($latestRlCrash.TimeCreated)] module=$rlModule id=$($latestRlCrash.Id)"
    } else {
        Write-Output "Latest ROCKETLEAGUE_CRASH: [$($latestRlCrash.TimeCreated)] id=$($latestRlCrash.Id)"
    }
}

if (-not $coreReady) {
    Write-Output ""
    Write-Output "Next step:"
    if ($coreImported -and -not $packetActive) {
        Write-Output "  Core import succeeded, but no gameplay packets were observed yet."
        Write-Output "  Enter Freeplay or a match, wait 5-10 seconds, then re-run this script."
    } elseif ($coreGuardBlocked) {
        Write-Output "  Core import was blocked by the safety guard in this session."
        Write-Output "  Keep safety mode for normal runs; only use unsafe mode when explicitly reproducing native crashes."
        Write-Output "  Relaunch Carbon once, then re-run this script and confirm whether CORE_READY appears."
    } elseif ($coreInitFailed) {
        Write-Output "  Core import succeeded but BotimusCore initialization failed in this session."
        Write-Output "  Relaunch Carbon once, enter Freeplay, and re-run this script to check for CORE_READY."
    } elseif ($coreImportFailed) {
        Write-Output "  Core import failed in this session (not classified as guard-blocked)."
        Write-Output "  Relaunch Carbon, then re-run this script and review CORE_IMPORT_FAIL details."
    } elseif ($coreFailed) {
        Write-Output "  Core failed in this session."
        Write-Output "  Relaunch Carbon, then re-run this script and check whether CORE_READY appears."
    } else {
        Write-Output "  Relaunch Carbon, then re-run this script and check whether CORE_READY appears."
    }
} elseif ($latestLaunchAfterInit) {
    Write-Output ""
    Write-Output "Next step:"
    Write-Output "  Latest Carbon launch did not reach plugin initialization."
    if ($latestLaunchTreeAlive) {
        Write-Output "  Carbon is running but SDK attach is stalled before plugin startup."
        Write-Output "  Close Carbon, relaunch once, then retry after Rocket League reaches main menu."
    } else {
        Write-Output "  Carbon launch process exited before plugin startup."
        Write-Output "  Relaunch once and re-check this script."
    }
}

if ($RequireCoreReady -and -not $coreReady) {
    exit 2
}
