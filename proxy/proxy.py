"""Transparent tool proxy implementation."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict

from trajlog.trajectory import TrajectoryLogger


class TransparentProxy:
    """A transparent proxy that forwards calls to underlying tools without modification.

    The proxy logs each invocation via a `TrajectoryLogger`.
    """

    def __init__(self, tool_registry: Dict[str, Callable[..., Any]], logger: TrajectoryLogger) -> None:
        self.tool_registry = tool_registry
        self.logger = logger

    def call(self, run_id: str, tool_name: str, *args, enable_proxy: bool = True, **kwargs) -> Any:
        start = time.perf_counter()
        tool = self.tool_registry[tool_name]
        # Call the real tool
        result = tool(*args, **kwargs)
        latency = time.perf_counter() - start

        entry = {
            "run_id": run_id,
            "tool_name": tool_name,
            "args": args,
            "kwargs": kwargs,
            "raw_tool_result": result,
            "returned_proxy_result": result,
            "proxy_enabled": enable_proxy,
            "latency": latency,
        }
        self.logger.log(entry)
        return result
