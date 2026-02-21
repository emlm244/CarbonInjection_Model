# Upload and Test Guide

## Clone and install active integration

```powershell
git clone https://github.com/emlm244/CarbonInjection_Model
cd .\CarbonInjection_Model
powershell -ExecutionPolicy Bypass -File .\scripts\install_carbon_plugin.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5 -EnableBotimusIntegration
```

## Verify active integration

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_carbon_pipeline.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5 -RequireActiveIntegration
```

## Launch with active integration

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot -EnableBotimusIntegration -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## If core import is guard-blocked

Use the experimental nocheck candidate mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot -EnableBotimusIntegration -UseNoCheckCandidate -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## Optional: return to archived mode

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\archive_botimus_carbon_integration.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```
