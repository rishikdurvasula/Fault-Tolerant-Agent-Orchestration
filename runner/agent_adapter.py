from __future__ import annotations

from typing import Any, Callable, Dict


class AgentAdapter:
    """Framework-independent agent adapter abstraction.

    Implementations should provide `run` which executes the given task
    and returns a structured run summary.
    """

    def run(
        self,
        task_text: str,
        run_id: str,
        tool_caller: Callable[..., Any],
        logger: Callable[[Dict[str, Any]], None],
        task_id: str | None = None,
        **kwargs,
    ) -> Dict[str, Any]:
        raise NotImplementedError()
