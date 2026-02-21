# Technical Architecture

## Runtime Flow

1. Carbon loads plugin loader.
2. Loader routes to `plugin_BotimusPrime`.
3. Tick callback receives packet and player context.
4. Runtime core computes controls.
5. Plugin returns `SimpleControllerState` or `None`.

## Contract

- Class: `plugin_BotimusPrime`
- Callback: `game_tick_packet_set(packet, local_player_index, playername, process_id)`
- Return: `SimpleControllerState` or `None`

## Package Layout

- `plugin/botimus_prime/plugin_botimus.py`
- `plugin/botimus_prime/runtime/*`
- `plugin/botimus_prime/strategy/*`
- `plugin/botimus_prime/maneuvers/*`
- `plugin/botimus_prime/tools/*`
- `plugin/botimus_prime/rlutilities/*`

## Script Entry Points

- Install: `scripts/install_carbon_plugin.ps1`
- Verify: `scripts/verify_carbon_pipeline.ps1`
- Launch: `scripts/launch_carbon_premium_py311.ps1`
- Restore active loader: `scripts/restore_botimus_carbon_integration.ps1`
- Archive loader: `scripts/archive_botimus_carbon_integration.ps1`
