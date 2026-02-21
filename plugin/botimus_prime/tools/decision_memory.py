from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from rlutilities.linear_algebra import vec3


@dataclass
class DecisionMemory:
    locked_action_until: float = 0.0
    locked_role_until: float = 0.0
    last_action_tag: str = ""
    last_role: int = -1
    last_support_target: Optional[vec3] = None
    last_repath_time: float = -999.0
    last_teamplay_trace: Optional[dict[str, Any]] = None

    def reset(self):
        self.locked_action_until = 0.0
        self.locked_role_until = 0.0
        self.last_action_tag = ""
        self.last_role = -1
        self.last_support_target = None
        self.last_repath_time = -999.0
        self.last_teamplay_trace = None

    def is_action_locked(self, now: float) -> bool:
        return now < self.locked_action_until

    def is_role_locked(self, now: float) -> bool:
        return now < self.locked_role_until

    def can_replan(self, now: float, danger: float, hard_override_threshold: float = 0.86) -> bool:
        return danger >= hard_override_threshold or not self.is_action_locked(now)

    def lock_action(self, action_tag: str, now: float, duration: float):
        if action_tag:
            self.last_action_tag = action_tag
        duration = max(0.0, duration)
        if duration <= 0.0:
            return
        self.locked_action_until = max(self.locked_action_until, now + duration)

    def lock_role(self, role: int, now: float, duration: float):
        self.last_role = role
        duration = max(0.0, duration)
        if duration <= 0.0:
            return
        self.locked_role_until = max(self.locked_role_until, now + duration)

    def can_repath_support(self, now: float, cooldown: float) -> bool:
        return now >= self.last_repath_time + max(0.0, cooldown)

    def remember_support_target(self, target: vec3, now: float):
        self.last_support_target = vec3(target[0], target[1], target[2])
        self.last_repath_time = now

    def set_teamplay_trace(self, trace: Optional[dict[str, Any]]):
        self.last_teamplay_trace = trace
