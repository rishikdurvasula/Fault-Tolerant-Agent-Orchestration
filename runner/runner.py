"""Execute benchmark tasks either directly or through the transparent proxy."""
from __future__ import annotations

import argparse
import time
from typing import Any, Dict, List, Tuple

from benchmark.tasks import run_benchmark_task
from trajlog.trajectory import TrajectoryLogger
from proxy.proxy import TransparentProxy
from tools.tools import TOOL_REGISTRY
from fault_injector.manifest import load_manifest


def _direct_tool_caller(logger: TrajectoryLogger, run_id: str, tool_name: str, *args, **kwargs):
    start = time.perf_counter()
    tool = TOOL_REGISTRY[tool_name]
    result = tool(*args, **kwargs)
    latency = time.perf_counter() - start
    entry = {
        "run_id": run_id,
        "tool_name": tool_name,
        "args": args,
        "kwargs": kwargs,
        "raw_tool_result": result,
        "returned_proxy_result": result,
        "proxy_enabled": False,
        "latency": latency,
    }
    logger.log(entry)
    return result


def run_direct(run_id: str, log_path: str, customer_id: int = 42) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    logger = TrajectoryLogger(log_path)
    result = run_benchmark_task(lambda rid, name, *a, **k: _direct_tool_caller(logger, rid, name, *a, **k), run_id, customer_id)
    return result, logger.read_all()


def run_proxied(run_id: str, log_path: str, customer_id: int = 42, fault_manifest: str | None = None, task_id: str | None = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    logger = TrajectoryLogger(log_path)
    specs = []
    if fault_manifest:
        specs = load_manifest(fault_manifest)
    proxy = TransparentProxy(TOOL_REGISTRY, logger, fault_specs=specs, task_id=task_id)
    result = run_benchmark_task(lambda rid, name, *a, **k: proxy.call(rid, name, *a, enable_proxy=True, **k), run_id, customer_id)
    return result, logger.read_all()


def _cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["direct", "proxied"]) 
    parser.add_argument("--log", required=True)
    parser.add_argument("--run-id", default=str(int(time.time())))
    parser.add_argument("--task-id", default="benchmark")
    parser.add_argument("--fault-manifest", default=None)
    args = parser.parse_args()
    if args.mode == "direct":
        out, _ = run_direct(args.run_id, args.log)
    else:
        out, _ = run_proxied(args.run_id, args.log, fault_manifest=args.fault_manifest, task_id=args.task_id)
    print(out)


if __name__ == "__main__":
    _cli()
