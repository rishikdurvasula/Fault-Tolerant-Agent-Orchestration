"""Run agent-driven tasks using adapters (LangGraph adapter implemented)."""
from __future__ import annotations

import argparse
import time
from typing import Any, Callable, Dict, List

from trajlog.trajectory import TrajectoryLogger
from proxy.proxy import TransparentProxy
from tools.tools import TOOL_REGISTRY
from agents.langgraph_adapter import LangGraphAdapter
from fault_injector.manifest import load_manifest


def _logger_log(logger: TrajectoryLogger, entry: Dict[str, Any]) -> None:
    logger.log(entry)


def run_agent_task(
    run_id: str,
    task_text: str,
    log_path: str,
    task_id: str = "agent_task",
    fault_manifest: str | None = None,
) -> Dict[str, Any]:
    logger = TrajectoryLogger(log_path)
    specs = []
    if fault_manifest:
        specs = load_manifest(fault_manifest)
    proxy = TransparentProxy(TOOL_REGISTRY, logger, fault_specs=specs, task_id=task_id)

    # tool_caller will be used by the agent and must route through proxy
    def tool_caller(rid: str, tool_name: str, *args, **kwargs):
        return proxy.call(rid, tool_name, *args, **kwargs)

    adapter = LangGraphAdapter()
    # Log run start
    logger.log({"type": "agent_run_start", "run_id": run_id, "task_id": task_id, "task_text": task_text, "timestamp": time.time()})
    result = adapter.run(task_text, run_id, tool_caller, lambda e: _logger_log(logger, e), task_id=task_id)
    # Log run end with final answer
    logger.log({"type": "agent_run_end", "run_id": run_id, "final_answer": result.get("final_answer"), "timestamp": time.time()})
    return result


def _cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--run-id", default=str(int(time.time())))
    parser.add_argument("--task-id", default="agent_task")
    parser.add_argument("--fault-manifest", default=None)
    args = parser.parse_args()
    out = run_agent_task(args.run_id, args.task, args.log, task_id=args.task_id, fault_manifest=args.fault_manifest)
    print(out)


if __name__ == "__main__":
    _cli()
