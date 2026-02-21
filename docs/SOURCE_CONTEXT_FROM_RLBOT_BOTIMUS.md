# Source Context from RLBot Botimus

This repository documentation was aligned using local source context from the RLBot Botimus package documentation and memory files.

Reviewed source docs:

- `AGENTS.md`
- `CARBONX_PLUGIN_SETUP.md`
- `CARBON_BOTIMUS_AUDIT_20260219.md`

Key facts imported into this repo docs:

- archive-by-default pattern is critical for stability
- runtime scripts are the operational contract
- active integration can fail due native guard and ABI concerns
- diagnostics and verify logs are essential for triage

Adaptation decisions for this repo:

- removed unrelated Nexto-focused implementation details
- retained Botimus-centric install/verify/archive/restore/launch flows
- retained guard-blocked troubleshooting guidance
- retained focus on deterministic Botimus backend with extensible integration pattern
