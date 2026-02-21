# Botimus Prime Carbon Setup

## Source Package Contents

This folder is the source package used by the installer script.

Required items:
- `data/`
- `maneuvers/`
- `runtime/`
- `strategy/`
- `tools/`
- `rlutilities/`
- `plugin_botimus.py`
- `botimus_settings.ini`

## Install Into Carbon

From repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_carbon_plugin.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5 -EnableBotimusIntegration
```

## Verify Wiring

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_carbon_pipeline.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5 -RequireActiveIntegration
```

## Launch

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot -EnableBotimusIntegration -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## Archive Mode

Archive integration:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\archive_botimus_carbon_integration.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

Restore integration:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\restore_botimus_carbon_integration.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```
