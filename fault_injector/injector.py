"""Fault injection implementations and dispatcher."""
from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional

from tools import tools as tools_module


def inject(result: Any, spec: "object", context: Dict[str, Any]) -> Any:
    """Dispatch to specific fault injectors based on spec.fault_type.

    `spec` is expected to have attributes: fault_type, seed, parameters, fault_id.
    """
    fault_type = getattr(spec, "fault_type", None)
    if fault_type == "wrong_value":
        return _inject_wrong_value(result, spec, context)
    if fault_type == "wrong_entity":
        return _inject_wrong_entity(result, spec, context)
    if fault_type == "truncated_result":
        return _inject_truncated_result(result, spec, context)
    if fault_type == "stale_value":
        return _inject_stale_value(result, spec, context)
    # Unknown fault -> return original
    return result


def _inject_wrong_value(result: Any, spec: object, context: Dict[str, Any]) -> Any:
    # Replace a field's value with a deterministic replacement preserving type
    params = spec.parameters
    field = params.get("field")
    replacement = params.get("replacement", None)
    out = copy.deepcopy(result)
    if not field:
        return result
    # Support dot-separated path
    parts = field.split(".")
    node = out
    for p in parts[:-1]:
        if isinstance(node, dict):
            node = node.get(p, None)
        else:
            return result
    key = parts[-1]
    if not isinstance(node, dict) or key not in node:
        return result
    orig = node[key]
    rnd = random.Random(spec.seed)
    # If replacement provided, use it (type-preserving cast)
    if replacement is not None:
        node[key] = _coerce_type(orig, replacement)
        return out
    # Otherwise generate deterministic replacement
    if isinstance(orig, int):
        node[key] = orig + rnd.randint(1, 100)
    elif isinstance(orig, float):
        node[key] = orig + rnd.uniform(-1000.0, 1000.0)
    elif isinstance(orig, str):
        node[key] = f"{orig}_fault{rnd.randint(1,100)}"
    else:
        node[key] = orig
    return out


def _coerce_type(orig: Any, replacement: Any) -> Any:
    try:
        if isinstance(orig, int):
            return int(replacement)
        if isinstance(orig, float):
            return float(replacement)
        if isinstance(orig, str):
            return str(replacement)
    except Exception:
        return replacement
    return replacement


def _inject_wrong_entity(result: Any, spec: object, context: Dict[str, Any]) -> Any:
    # Replace an entity with another entity of same schema by calling the tool generator
    tool_name = spec.tool_name
    rnd = random.Random(spec.seed)
    out = copy.deepcopy(result)
    # Try to find an id-like field to alter
    if isinstance(out, dict) and "customer_id" in out:
        orig_id = out["customer_id"]
        # choose another id deterministically
        new_id = orig_id + 1 + (rnd.randint(0, 10))
        try:
            if tool_name == "get_customer":
                return tools_module.get_customer(new_id)
            if tool_name == "get_account_balance":
                return tools_module.get_account_balance(new_id)
        except Exception:
            return out
    return out


def _inject_truncated_result(result: Any, spec: object, context: Dict[str, Any]) -> Any:
    params = spec.parameters
    max_items = params.get("max_items")
    rnd = random.Random(spec.seed)
    out = copy.deepcopy(result)
    # Expect collection under 'results' key
    if isinstance(out, dict) and "results" in out and isinstance(out["results"], list):
        total = len(out["results"])
        if max_items is None:
            # choose deterministic value between 1 and total
            max_items = 1 + (rnd.randint(0, max(0, total - 1)))
        else:
            max_items = min(int(max_items), total)
        out["results"] = out["results"][:max_items]
    return out


def _inject_stale_value(result: Any, spec: object, context: Dict[str, Any]) -> Any:
    # For account balances, pick an older version from tools.get_account_balance_history
    out = copy.deepcopy(result)
    if isinstance(out, dict) and out.get("customer_id") is not None:
        cid = out.get("customer_id")
        history = tools_module.get_account_balance_history(cid)
        if not history:
            return out
        rnd = random.Random(spec.seed)
        idx = rnd.randint(0, len(history) - 1)
        return history[idx]
    return out
