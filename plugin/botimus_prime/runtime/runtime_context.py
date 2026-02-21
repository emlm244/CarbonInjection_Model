from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol


class RuntimeContext(Protocol):
    def get_field_info(self) -> Any:
        ...

    def get_ball_prediction(self) -> Any:
        ...

    def log(self, message: str) -> None:
        ...


@dataclass
class CallbackRuntimeContext:
    get_field_info_fn: Optional[Callable[[], Any]] = None
    get_ball_prediction_fn: Optional[Callable[[], Any]] = None
    log_fn: Optional[Callable[[str], None]] = None

    def get_field_info(self) -> Any:
        if self.get_field_info_fn is None:
            return None
        try:
            return self.get_field_info_fn()
        except Exception:
            return None

    def get_ball_prediction(self) -> Any:
        if self.get_ball_prediction_fn is None:
            return None
        try:
            return self.get_ball_prediction_fn()
        except Exception:
            return None

    def log(self, message: str) -> None:
        if self.log_fn is None:
            return
        try:
            self.log_fn(message)
        except Exception:
            pass
