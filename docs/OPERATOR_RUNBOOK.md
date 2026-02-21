# Operator Runbook

## Core Paths

- Stable root: `C:\CarbonBot`
- Dev root: `C:\CarbonBot_IntegrationDev`

## Bootstrap Dev Root

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_integration_dev_root.ps1 -StableRoot C:\CarbonBot -DevRoot C:\CarbonBot_IntegrationDev
```

## Activate Integration in Dev Root

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev_install_and_verify.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -CarbonVersion 2.3.5
```

## Launch Dev Root

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -EnableBotimusIntegration -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## Stable Root Temporary Test

Activate:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\activate_stable_for_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

Revert:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\revert_stable_after_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

## Diagnostics

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\collect_carbon_diagnostics.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev
```
