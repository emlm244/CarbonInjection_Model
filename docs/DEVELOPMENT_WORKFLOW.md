# Development Workflow

## Goal

Develop integration features without breaking your personal Carbon runtime and injector workflow.

## Runtime Split

- Stable runtime root: `C:\CarbonBot`
- Dev runtime root: `C:\CarbonBot_IntegrationDev`

## Setup Once

1. Sync stable root into dev root while Carbon is closed.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_integration_dev_root.ps1 -StableRoot C:\CarbonBot -DevRoot C:\CarbonBot_IntegrationDev
```

2. Confirm stable root is archived.

```powershell
powershell -ExecutionPolicy Bypass -File C:\CarbonBot\scripts\verify_carbon_pipeline.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

Expected stable state: `integration_state: archived`.

## Daily Dev Loop

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev_install_and_verify.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -CarbonVersion 2.3.5
```

Then launch and test against the dev root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -EnableBotimusIntegration -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## Temporary Stable Test Loop

When you intentionally want to test on stable root:

1. Activate stable test mode.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\activate_stable_for_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

2. Run your test session.

3. Revert stable root immediately after test.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\revert_stable_after_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

## Safety Rules

- Keep Carbon closed during install/archive/restore/sync operations.
- Use stable root only for short validation passes.
- Do all integration iteration in dev root.
