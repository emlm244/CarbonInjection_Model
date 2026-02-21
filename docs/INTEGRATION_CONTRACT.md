# Integration Contract

## Loader Contract

Template file: `plugin/templates/plugin_botimus_prime.template.py`

Behavior:

- Add package directory to `sys.path`.
- Import `plugin_BotimusPrime` from `plugin_botimus.py`.

## Plugin Class Contract

Class name:

- `plugin_BotimusPrime`

Tick callback:

- `game_tick_packet_set(packet, local_player_index, playername, process_id)`

Expected return:

- `SimpleControllerState` for explicit controls.
- `None` for passthrough.

## Environment Controls

Primary integration env keys used by launch/runtime flow:

- `BOTIMUS_CARBON_ARCHIVED`
- `BOTIMUS_CARBON_SILENT_ARCHIVE`
- `BOTIMUS_PACKET_READ_MODE`
- `BOTIMUS_CORE_FAIL_MODE`
- `BOTIMUS_RLUTILITIES_CANDIDATES`
- `BOTIMUS_AUTO_NOCHECK_RLUTILITIES`
- `BOTIMUS_FORCE_UNSAFE_CORE_IMPORT`

## Runtime Logging Contract

Log files:

- Launch script log: `carbon_launch_py311.log`
- Plugin runtime log: `botimus_plugin_runtime.log`

Verification script parses these logs to determine:

- integration state
- core state
- packet stream presence
- safety guard outcomes
