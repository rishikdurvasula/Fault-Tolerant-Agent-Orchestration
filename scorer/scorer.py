"""Scoring and aggregation for experiment trajectories."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fault_injector.manifest import load_manifest, FaultSpec


class Outcome(str, Enum):
    RECOVERED = "RECOVERED"
    FLAGGED_GAVE_UP = "FLAGGED_GAVE_UP"
    DIDNT_MATTER = "DIDNT_MATTER"
    SILENT_PROPAGATION = "SILENT_PROPAGATION"
    VOID = "VOID"


@dataclass
class DetectionEvidence:
    retried_tool: bool = False
    verification_call: bool = False
    explicit_uncertainty: bool = False
    matched_language_rule: Optional[str] = None


class Scorer:
    """Score a saved trajectory JSONL file.

    The scorer is deterministic and uses conservative rule-based detection.
    """

    LANGUAGE_RULES = [
        "could not",
        "cannot",
        "unable to verify",
        "not confident",
        "inconsistent",
        "couldn't",
    ]

    def __init__(self) -> None:
        pass

    def read_trajectory(self, path: str) -> List[Dict[str, Any]]:
        p = Path(path)
        items: List[Dict[str, Any]] = []
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
        return items

    def score_run(self, traj_path: str, manifest_path: Optional[str] = None) -> Dict[str, Any]:
        entries = self.read_trajectory(traj_path)
        # collect proxy tool calls and agent runs
        proxy_calls = [e for e in entries if e.get("tool_name")]
        agent_runs = [e for e in entries if e.get("type") and e.get("type").startswith("agent") or e.get("framework")]

        run_id = None
        task_id = None
        framework = None
        model = None
        final_answer = None

        for a in agent_runs:
            run_id = run_id or a.get("run_id")
            task_id = task_id or a.get("task_id")
            framework = framework or a.get("framework")
            model = model or a.get("model")
            if a.get("type") == "agent_run_end":
                final_answer = a.get("final_answer")
            if a.get("final_answer") and not final_answer:
                final_answer = a.get("final_answer")

        # Identify faulted calls
        faulted_calls = [c for c in proxy_calls if c.get("fault_injected")]

        # If manifest specified, check reachability (VOID)
        void_info = None
        if manifest_path:
            specs = load_manifest(manifest_path)
            for spec in specs:
                # check if any proxy call matches tool+call_index+task_id
                found = any((c.get("tool_name") == spec.tool_name and int(c.get("call_index", 0)) == spec.call_index and (spec.task_id == c.get("task_id"))) for c in proxy_calls)
                if not found:
                    return self._void_run_artifact(run_id, task_id, framework, model, spec)

        # If no fault injected at all -> clean run
        fault_injected = len(faulted_calls) > 0

        # For scoring, consider the first faulted call only (simple per-run outcome)
        if not fault_injected:
            # Clean run scoring: detect false alarms
            detected, evidence = self._detect_from_trajectory(entries)
            correct = self._determine_correctness(entries, final_answer)
            false_alarm = detected and correct
            artifact = {
                "run_id": run_id,
                "task_id": task_id,
                "framework": framework,
                "model": model,
                "fault_injected": False,
                "detected": detected,
                "detection_evidence": evidence.__dict__,
                "correct": correct,
                "outcome": "CLEAN",
            }
            return artifact

        fc = faulted_calls[0]
        fault_id = fc.get("fault_id")
        fault_type = fc.get("fault_type")
        injected_value = fc.get("returned_proxy_result")
        raw_value = fc.get("raw_tool_result")

        # Did agent encounter the targeted call? presence in proxy_calls implies yes
        encountered = True

        detected, evidence = self._detect_from_trajectory(entries)
        correct = self._determine_correctness(entries, final_answer, raw_value)

        # Map detection + correctness to outcome
        if not encountered:
            outcome = Outcome.VOID
        else:
            if detected:
                if correct:
                    outcome = Outcome.RECOVERED
                else:
                    outcome = Outcome.FLAGGED_GAVE_UP
            else:
                if correct:
                    outcome = Outcome.DIDNT_MATTER
                else:
                    outcome = Outcome.SILENT_PROPAGATION

        artifact = {
            "run_id": run_id,
            "task_id": task_id,
            "framework": framework,
            "model": model,
            "fault_injected": True,
            "fault_id": fault_id,
            "fault_type": fault_type,
            "ground_truth": raw_value,
            "injected_value": injected_value,
            "final_answer": final_answer,
            "correct": correct,
            "detected": detected,
            "detection_evidence": evidence.__dict__,
            "outcome": outcome.value,
        }
        return artifact

    def _void_run_artifact(self, run_id, task_id, framework, model, spec: FaultSpec) -> Dict[str, Any]:
        return {
            "run_id": run_id,
            "task_id": task_id,
            "framework": framework,
            "model": model,
            "fault_injected": True,
            "outcome": Outcome.VOID.value,
            "void_reason": f"Targeted call {spec.tool_name} index {spec.call_index} not reached",
        }

    def _detect_from_trajectory(self, entries: List[Dict[str, Any]]) -> Tuple[bool, DetectionEvidence]:
        # Layer 1 signals
        evidence = DetectionEvidence()
        # retried_tool: same tool_name appears more than once
        tool_counts = defaultdict(int)
        for e in entries:
            if e.get("tool_name"):
                tool_counts[e["tool_name"]] += 1
        evidence.retried_tool = any(v > 1 for v in tool_counts.values())

        # verification_call: calls to both get_customer and get_account_balance
        names = set(c.get("tool_name") for c in entries if c.get("tool_name"))
        evidence.verification_call = ("get_customer" in names and "get_account_balance" in names)

        # explicit_uncertainty: agent_run entries with explicit refusal-like messages
        texts = []
        for a in entries:
            if a.get("type") and a.get("type").startswith("agent"):
                # messages or final_answer
                if a.get("messages"):
                    for m in a.get("messages", []):
                        texts.append(m.get("content", ""))
                if a.get("final_answer"):
                    texts.append(str(a.get("final_answer")))

        matched_rule = None
        for t in texts:
            low = t.lower()
            for rule in self.LANGUAGE_RULES:
                if rule in low:
                    evidence.explicit_uncertainty = True
                    matched_rule = rule
                    break
            if matched_rule:
                break

        evidence.matched_language_rule = matched_rule
        detected = evidence.retried_tool or evidence.verification_call or evidence.explicit_uncertainty
        return detected, evidence

    def _determine_correctness(self, entries: List[Dict[str, Any]], final_answer: Optional[str], ground_truth: Optional[Any] = None) -> bool:
        # Task-specific heuristic: if ground_truth is a dict with 'balance'
        if ground_truth and isinstance(ground_truth, dict) and "balance" in ground_truth:
            expected = ground_truth.get("balance")
            if final_answer is None:
                return False
            # extract number from final_answer
            import re

            mlist = re.findall(r"(\d+[\,\d]*\.?\d*)", str(final_answer))
            if not mlist:
                return False
            # prefer the last numeric occurrence (often the answer, not ids)
            val = float(mlist[-1].replace(",", ""))
            # allow small float tolerance
            return math.isclose(val, float(expected), rel_tol=1e-3, abs_tol=1e-2)

        # customer info: check if final_answer contains expected customer_id
        if ground_truth and isinstance(ground_truth, dict) and "customer_id" in ground_truth:
            cid = ground_truth.get("customer_id")
            if final_answer is None:
                return False
            return str(cid) in str(final_answer)

        # search results: if ground_truth contains results, check overlap
        if ground_truth and isinstance(ground_truth, dict) and "results" in ground_truth:
            expected_ids = {r.get("id") for r in ground_truth.get("results", [])}
            # parse ids from final_answer
            found_ids = set()
            import re

            for m in re.finditer(r"\b(\d+)\b", str(final_answer or "")):
                found_ids.add(int(m.group(1)))
            return expected_ids.issubset(found_ids) or bool(expected_ids & found_ids)

        # Fallback: if final_answer present, consider possibly correct
        return final_answer is not None
