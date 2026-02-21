# Concept Overview

## Goal

Provide a clean integration pipeline so Carbon can run custom model logic from an external package.

## Current Prototype Scope

- Deterministic Botimus Prime integration is included.
- Tick packet to controller output flow is implemented.
- Active and archived integration modes are script-controlled.

## Integration Model

- Carbon handles process injection and plugin lifecycle.
- Plugin callback receives live game packet state.
- Model/runtime code computes controls.
- Plugin returns controller output or passthrough.

## Direction

This concept is for integrating custom models and RLBot-style bot logic through Carbon hooks, not for shipping unrelated runtime plugins.
