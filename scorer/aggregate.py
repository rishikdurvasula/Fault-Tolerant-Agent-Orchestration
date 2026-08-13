from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def aggregate_scored(folder: str) -> Dict[str, Dict]:
    p = Path(folder)
    files = list(p.glob("*.json"))
    stats = {
        "total_runs": 0,
        "faulted_runs": 0,
        "clean_runs": 0,
        "void_runs": 0,
    }
    by_fault = defaultdict(lambda: {"runs": 0, "silent_prop": 0, "detected": 0, "recovered": 0})
    total_runs = 0
    for f in files:
        with f.open("r", encoding="utf-8") as fh:
            art = json.load(fh)
        total_runs += 1
        outcome = art.get("outcome")
        if outcome == "VOID":
            stats["void_runs"] += 1
        elif outcome == "CLEAN":
            stats["clean_runs"] += 1
        else:
            stats["faulted_runs"] += 1
            ft = art.get("fault_type") or "unknown"
            by_fault[ft]["runs"] += 1
            if outcome == "SILENT_PROPAGATION":
                by_fault[ft]["silent_prop"] += 1
            if art.get("detected"):
                by_fault[ft]["detected"] += 1
            if outcome == "RECOVERED":
                by_fault[ft]["recovered"] += 1

    stats["total_runs"] = total_runs
    return {"stats": stats, "by_fault": dict(by_fault)}
