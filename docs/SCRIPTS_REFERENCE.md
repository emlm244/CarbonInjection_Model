# Scripts Reference

## Workflow Helpers

### setup_integration_dev_root.ps1

Purpose: synchronize stable runtime root into isolated dev runtime root.

Parameters:

- `-StableRoot` default `C:\CarbonBot`
- `-DevRoot` default `C:\CarbonBot_IntegrationDev`

Behavior:

- blocks if Carbon process is running
- syncs files with `robocopy`
- writes `INTEGRATION_DEV_ROOT.flag` in dev root

### dev_install_and_verify.ps1

Purpose: one-command active install and verification for dev root.

Parameters:

- `-CarbonRoot` default `C:\CarbonBot_IntegrationDev`
- `-CarbonVersion` default `2.3.5`
- `-RequireCoreReady`

Behavior:

- runs install script with `-EnableBotimusIntegration`
- runs verify script with `-RequireActiveIntegration`

### activate_stable_for_test.ps1

Purpose: temporary activation of Botimus integration in stable root.

Behavior:

- blocks if Carbon process is running
- installs active integration in stable root
- verifies active state

### revert_stable_after_test.ps1

Purpose: revert stable root back to archived mode after temporary testing.

Behavior:

- blocks if Carbon process is running
- archives integration
- verifies archived state

## Runtime Scripts

### install_carbon_plugin.ps1

Deploy package into runtime plugins and optionally enable active loader.

### archive_botimus_carbon_integration.ps1

Remove active loader and move runtime package to archive location.

### restore_botimus_carbon_integration.ps1

Restore runtime package from archive and recreate active loader.

### launch_carbon_premium_py311.ps1

Launch Carbon with per-session integration environment.

### verify_carbon_pipeline.ps1

Summarize runtime state using launch and runtime logs.

### collect_carbon_diagnostics.ps1

Generate diagnostics report in runtime logs diagnostics folder.

### quality_first_party.ps1

Run syntax gate for selected first-party files.
