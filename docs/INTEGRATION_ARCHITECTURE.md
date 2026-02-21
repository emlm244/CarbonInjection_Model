# Integration Architecture

## High-Level Model

Carbon loads a plugin entrypoint. The loader imports `plugin_BotimusPrime` from the Botimus package. The plugin receives game packets and returns controller output.

## Control Flow

1. Carbon loads `plugin_botimus_prime.py` when integration is active.
2. Loader inserts package path and imports `plugin_BotimusPrime`.
3. Carbon invokes `game_tick_packet_set(packet, local_player_index, playername, process_id)`.
4. Plugin resolves integration mode and core import safety guard.
5. Plugin returns one of:
   - `SimpleControllerState` for active control output.
   - `None` for passthrough.

## Archived vs Active Modes

- Archived mode:
  - Loader absent.
  - Archive flag present.
  - Plugin defaults to silent archived semantics.
- Active mode:
  - Loader present.
  - Core import guard evaluated.
  - Runtime attempts core ticks and control output.

## Core Import Guard

The plugin protects the host runtime with a guard around core import.

- Safety mode keeps guard enforcement.
- Experimental mode allows nocheck candidate for reproduction-only scenarios.

## Runtime Assets

`plugin/botimus_prime/rlutilities/` includes native bindings and assets required for runtime behavior.

## Design Implication for Future Models

The loader + callback contract can host alternate model cores as long as they consume packet state and produce `SimpleControllerState` output.
