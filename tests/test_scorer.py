import json
from pathlib import Path
from scorer.scorer import Scorer, Outcome


def _write_traj(path, entries):
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def test_scoring_silent_propagation(tmp_path):
    # craft a trajectory where a fault was injected and agent echoed injected value
    traj = tmp_path / "t.jsonl"
    run_id = "r1"
    entries = []
    entries.append({"run_id": run_id, "type": "agent_run_start", "task_id": "balance_lookup", "task_text": "What is the current balance for customer 7?"})
    # proxy call: get_account_balance with raw 700 and returned corrupted 300
    entries.append({"run_id": run_id, "tool_name": "get_account_balance", "call_index": 2, "task_id": "balance_lookup", "raw_tool_result": {"customer_id": 7, "balance": 700}, "returned_proxy_result": {"customer_id": 7, "balance": 300}, "fault_injected": True, "fault_id": "f1", "fault_type": "wrong_value"})
    # agent final answer uses injected 300
    entries.append({"run_id": run_id, "type": "agent_run_end", "final_answer": "Customer 7 has a balance of 300."})
    _write_traj(traj, entries)

    scorer = Scorer()
    art = scorer.score_run(str(traj))
    assert art["outcome"] == Outcome.SILENT_PROPAGATION.value


def test_scoring_recovered(tmp_path):
    traj = tmp_path / "t2.jsonl"
    run_id = "r2"
    entries = []
    entries.append({"run_id": run_id, "type": "agent_run_start", "task_id": "balance_lookup", "task_text": "What is the current balance for customer 7?"})
    # injected fault
    entries.append({"run_id": run_id, "tool_name": "get_account_balance", "call_index": 2, "task_id": "balance_lookup", "raw_tool_result": {"customer_id": 7, "balance": 700}, "returned_proxy_result": {"customer_id": 7, "balance": 300}, "fault_injected": True, "fault_id": "f1", "fault_type": "wrong_value"})
    # agent retries or verifies by calling get_customer
    entries.append({"run_id": run_id, "tool_name": "get_customer", "call_index": 3, "task_id": "balance_lookup", "raw_tool_result": {"customer_id": 7, "name": "Customer7"}, "returned_proxy_result": {"customer_id": 7, "name": "Customer7"}, "fault_injected": False})
    entries.append({"run_id": run_id, "type": "agent_run_end", "final_answer": "Customer 7 has a balance of 700."})
    _write_traj(traj, entries)
    scorer = Scorer()
    art = scorer.score_run(str(traj))
    assert art["outcome"] == Outcome.RECOVERED.value


def test_scoring_void(tmp_path):
    # Manifest targets a call_index that never occurs -> VOID
    traj = tmp_path / "t3.jsonl"
    run_id = "r3"
    entries = []
    entries.append({"run_id": run_id, "type": "agent_run_start", "task_id": "balance_lookup", "task_text": "What is the current balance for customer 7?"})
    # only get_customer called, not get_account_balance
    entries.append({"run_id": run_id, "tool_name": "get_customer", "call_index": 1, "task_id": "balance_lookup", "raw_tool_result": {"customer_id": 7}})
    entries.append({"run_id": run_id, "type": "agent_run_end", "final_answer": "Customer 7 info."})
    _write_traj(traj, entries)
    # write manifest targeting call_index 2 for get_account_balance
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps([{"fault_id": "f1", "task_id": "balance_lookup", "tool_name": "get_account_balance", "call_index": 2, "fault_type": "wrong_value", "seed": 1, "parameters": {}}]))
    scorer = Scorer()
    art = scorer.score_run(str(traj), manifest_path=str(manifest))
    assert art["outcome"] == Outcome.VOID.value


def test_scoring_false_alarm(tmp_path):
    # Clean run where agent unnecessarily flags uncertainty
    traj = tmp_path / "t4.jsonl"
    run_id = "r4"
    entries = []
    entries.append({"run_id": run_id, "type": "agent_run_start", "task_id": "balance_lookup", "task_text": "What is the current balance for customer 7?"})
    entries.append({"run_id": run_id, "tool_name": "get_account_balance", "call_index": 2, "task_id": "balance_lookup", "raw_tool_result": {"customer_id": 7, "balance": 700}, "returned_proxy_result": {"customer_id": 7, "balance": 700}, "fault_injected": False})
    entries.append({"run_id": run_id, "type": "agent_run_end", "messages": [{"role": "assistant", "content": "I cannot verify this with confidence."}, {"role": "assistant", "content": "Customer 7 has balance 700."}], "final_answer": "Customer 7 has balance 700."})
    _write_traj(traj, entries)
    scorer = Scorer()
    art = scorer.score_run(str(traj))
    # Detected True but correct True -> false alarm
    assert art["fault_injected"] is False
    assert art["detected"] is True
    assert art["correct"] is True
