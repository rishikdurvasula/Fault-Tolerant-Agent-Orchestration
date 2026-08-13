from runner.agent_run import run_agent_task
import json


def test_agent_routes_through_proxy(tmp_path):
    # Clean run (no manifest) should return correct account balance
    log = str(tmp_path / "agent_clean.jsonl")
    task = "What is the current balance for customer 42?"
    res = run_agent_task("r-clean", task, log, task_id="balance_lookup", fault_manifest=None)
    assert res["framework"] == "langgraph"
    assert "final_answer" in res

    # Faulted run: inject wrong_value
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps([
        {
            "fault_id": "f1",
            "task_id": "balance_lookup",
            "tool_name": "get_account_balance",
            "call_index": 1,
            "fault_type": "wrong_value",
            "seed": 99,
            "parameters": {"field": "balance", "replacement": 1234}
        }
    ]))
    log2 = str(tmp_path / "agent_fault.jsonl")
    res2 = run_agent_task("r-fault", task, log2, task_id="balance_lookup", fault_manifest=str(manifest))
    # Ensure final answer changed (includes 1234)
    assert "1234" in res2["final_answer"] or "1234.0" in res2["final_answer"]
