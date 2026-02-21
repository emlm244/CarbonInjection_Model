# Contributing and Release

## Branching

Use focused branches for docs, scripts, or runtime changes.

## Validation

Run before publishing:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quality_first_party.ps1 -ProjectRoot .
powershell -ExecutionPolicy Bypass -File .\scripts\dev_install_and_verify.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -CarbonVersion 2.3.5
```

## Stable Root Safety Check

Before release, confirm stable root is archived:

```powershell
powershell -ExecutionPolicy Bypass -File C:\CarbonBot\scripts\verify_carbon_pipeline.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

Expected: `integration_state: archived`.

## Publishing Rule

Keep repository focused on Botimus integration pipeline and remove unrelated plugin content.

## History Policy

If you want clean public history snapshots, squash and force-push intentionally.
