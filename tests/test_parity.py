import json
from runner.runner import run_direct, run_proxied


def test_parity(tmp_path):
    direct_log = str(tmp_path / "direct.jsonl")
    proxied_log = str(tmp_path / "proxied.jsonl")

    run_id_direct = "run-direct"
    run_id_proxied = "run-proxied"

    out_direct, direct_entries = run_direct(run_id_direct, direct_log, customer_id=7)
    out_proxied, proxied_entries = run_proxied(run_id_proxied, proxied_log, customer_id=7)

    # Final outputs equal
    assert out_direct == out_proxied

    # Number of tool calls equal
    assert len(direct_entries) == len(proxied_entries)

    # Compare call order and raw results
    for d, p in zip(direct_entries, proxied_entries):
        assert d["tool_name"] == p["tool_name"]
        assert d["raw_tool_result"] == p["raw_tool_result"]

    # Ensure proxied entries report proxy_enabled True and returned_proxy_result equal raw
    for p in proxied_entries:
        assert p["proxy_enabled"] is True
        assert p["returned_proxy_result"] == p["raw_tool_result"]
