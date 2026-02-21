# Botimus Carbon Loader Template

Use this loader as a reference when creating or re-enabling a Carbon plugin integration.

## Required callback contract
- Class name: plugin_BotimusPrime
- Callback: game_tick_packet_set(packet, local_player_index, playername, process_id)
- Return: SimpleControllerState or None for passthrough

## Re-enable from template
Copy plugin_botimus_prime.template.py to plugins\plugin_botimus_prime.py.
