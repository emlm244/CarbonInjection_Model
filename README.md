# CarbonInjection_Model

CarbonInjection_Model is a Botimus-focused integration project for Carbon.

The current implementation demonstrates a deterministic Botimus Prime runtime connected through Carbon's plugin loader and tick callback contract. The same integration pattern can be reused for additional deterministic or non-deterministic model backends.

## Project Intent

- Keep integration logic in a clean, reusable package.
- Keep runtime safety defaults explicit.
- Make local testing repeatable for contributors.
- Avoid conflicts with an existing personal Carbon runtime.

## Recommended Runtime Topology

- Stable runtime root: `C:\CarbonBot`
- Development runtime root: `C:\CarbonBot_IntegrationDev`

Use the stable root for normal play and personal workflow. Use the dev root for active integration work.

## Initial Dev Root Setup

```powershell
git clone https://github.com/emlm244/CarbonInjection_Model
cd .\CarbonInjection_Model
powershell -ExecutionPolicy Bypass -File .\scripts\setup_integration_dev_root.ps1 -StableRoot C:\CarbonBot -DevRoot C:\CarbonBot_IntegrationDev
```

## Daily Dev Cycle

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev_install_and_verify.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -CarbonVersion 2.3.5
```

## Stable Root Test Cycle and Revert

Activate temporary stable test mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\activate_stable_for_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

After testing, revert stable root to archived mode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\revert_stable_after_test.ps1 -CarbonRoot C:\CarbonBot -CarbonVersion 2.3.5
```

## Launch in Dev Root

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -EnableBotimusIntegration -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

If verification reports `core_state: guard_blocked`, use experimental mode for investigation:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\launch_carbon_premium_py311.ps1 -CarbonRoot C:\CarbonBot_IntegrationDev -EnableBotimusIntegration -UseNoCheckCandidate -CarbonExe "C:\Path\To\CarbonX Premium.exe"
```

## Documentation Map

- `docs/DOCUMENTATION_INDEX.md`
- `docs/DEVELOPMENT_WORKFLOW.md`
- `docs/INTEGRATION_ARCHITECTURE.md`
- `docs/INTEGRATION_CONTRACT.md`
- `docs/SCRIPTS_REFERENCE.md`
- `docs/OPERATOR_RUNBOOK.md`
- `docs/TROUBLESHOOTING.md`
- `docs/CONTRIBUTING_AND_RELEASE.md`
- `docs/SOURCE_CONTEXT_FROM_RLBOT_BOTIMUS.md`

## Repository Layout

- `plugin/botimus_prime/`: runtime package
- `plugin/templates/`: loader template reference
- `scripts/`: install, archive, restore, launch, verify, diagnostics, quality, workflow helpers
- `docs/`: developer and operator documentation
- `AGENTS.md`: persistent project memory for future sessions
