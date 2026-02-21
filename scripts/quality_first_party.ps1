param(
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectRoot = Split-Path -Parent $scriptDir
}

$targets = @(
    (Join-Path $ProjectRoot "plugin\botimus_prime\plugin_botimus.py"),
    (Join-Path $ProjectRoot "plugin\botimus_prime\runtime\botimus_core.py"),
    (Join-Path $ProjectRoot "plugin\botimus_prime\rlutilities\__init__.py")
)

foreach ($target in $targets) {
    if (-not (Test-Path -LiteralPath $target)) {
        throw "Quality target not found: $target"
    }
}

Write-Output "Running syntax gate..."
python -m py_compile $targets
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Output "Syntax gate passed."
Write-Output "Optional strict lint/type checks are intentionally not enforced in this prototype package."
