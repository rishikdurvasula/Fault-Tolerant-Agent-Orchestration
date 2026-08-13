"""Transparent tool proxy implementation."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict

from trajlog.trajectory import TrajectoryLogger
from fault_injector.manifest import FaultSpec, load_manifest
from fault_injector import injector
from typing import List, Optional


class TransparentProxy:
    """A transparent proxy that forwards calls to underlying tools without modification.

    The proxy logs each invocation via a `TrajectoryLogger`.
    """

    def __init__(
        self,
        tool_registry: Dict[str, Callable[..., Any]],
        logger: TrajectoryLogger,
        fault_specs: Optional[List[FaultSpec]] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.logger = logger
        self.fault_specs = fault_specs or []
        self.task_id = task_id or ""
        # track call index per run_id
        self._call_counters: Dict[str, int] = {}

    def call(self, run_id: str, tool_name: str, *args, enable_proxy: bool = True, **kwargs) -> Any:
        start = time.perf_counter()
        tool = self.tool_registry[tool_name]
        # increment call counter
        idx = self._call_counters.get(run_id, 0) + 1
        self._call_counters[run_id] = idx

        # Call the real tool
        result = tool(*args, **kwargs)
        latency = time.perf_counter() - start

        # Default: no fault injected
        fault_id = None
        fault_type = None
        seed = None
        corrupted = result
        injected = False

        # Check for matching fault spec
        for spec in self.fault_specs:
            if spec.task_id == self.task_id and spec.tool_name == tool_name and spec.call_index == idx:
                # apply fault
                corrupted = injector.inject(result, spec, {"run_id": run_id, "call_index": idx, "task_id": self.task_id})
                fault_id = spec.fault_id
                fault_type = spec.fault_type
                seed = spec.seed
                injected = True
                break

        entry = {
            "run_id": run_id,
            "task_id": self.task_id,
            "call_index": idx,
            "tool_name": tool_name,
            "args": args,
            "kwargs": kwargs,
            "raw_tool_result": result,
            "returned_proxy_result": corrupted,
            "proxy_enabled": enable_proxy,
            "latency": latency,
            "fault_id": fault_id,
            "fault_type": fault_type,
            "fault_injected": injected,
            "seed": seed,
        }
        self.logger.log(entry)
        return corrupted
