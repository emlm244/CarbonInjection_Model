# CarbonInjection_Model Session Memory

Last updated: 2026-02-22

## Purpose

Persistent memory for this repository so future sessions stay aligned.

## Operating Defaults

- Repository scope is Botimus integration pipeline only.
- Stable runtime root should remain archived by default.
- Dev runtime root should be isolated at `C:\CarbonBot_IntegrationDev`.

## Active Facts

- Main integration loader class is `plugin_BotimusPrime`.
- Primary callback contract is `game_tick_packet_set(packet, local_player_index, playername, process_id)`.
- Verification source of truth is `scripts/verify_carbon_pipeline.ps1`.
- Dev workflow helper scripts are part of the contract.

## Known Risks

- Native rlutilities compatibility can vary across Carbon environments.
- Guard-blocked core import can appear in active mode and may require experimental launch mode for investigation.
- Running install/archive/restore/sync while Carbon is open can cause inconsistent runtime state.

## Update Rules

- Keep entries factual and operational.
- Use absolute dates.
- Remove stale risks when resolved.
