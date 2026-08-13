"""Load fault manifests (JSON) and represent as FaultSpec objects."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FaultSpec:
    fault_id: str
    task_id: str
    tool_name: str
    call_index: int
    fault_type: str
    seed: int
    parameters: Dict[str, Any]


def load_manifest(path: str) -> List[FaultSpec]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    specs: List[FaultSpec] = []
    for item in data:
        specs.append(FaultSpec(
            fault_id=item["fault_id"],
            task_id=item.get("task_id", ""),
            tool_name=item["tool_name"],
            call_index=int(item.get("call_index", 0)),
            fault_type=item["fault_type"],
            seed=int(item.get("seed", 0)),
            parameters=item.get("parameters", {}),
        ))
    return specs
