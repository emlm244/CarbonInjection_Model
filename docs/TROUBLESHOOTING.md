# Troubleshooting

## setup_integration_dev_root.ps1 fails because Carbon is running

Close all `Carbon*` processes, then rerun setup.

## dev_install_and_verify shows archived state

Ensure you are targeting the dev root and active mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev_install_and_verify.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -CarbonVersion 2.3.5
```

## verify reports guard_blocked

Relaunch in experimental mode for investigation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -EnableBotimusIntegration -UseNoCheckCandidate -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## stable root accidentally left active

Revert immediately:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\revert_stable_after_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

## install or archive fails due running process

All install/archive/restore operations require Carbon to be fully closed.

## runtime log missing

Launch Carbon once and enter a playable session before running verify again.
