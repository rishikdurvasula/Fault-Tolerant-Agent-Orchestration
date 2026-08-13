fault-tolerant-agent-orchestration

Milestone 1: Transparent Proxy

What the proxy does
- A transparent tool proxy forwards tool invocation requests to real tools and returns their results without modification. It records structured trajectory logs (JSONL) for each invocation including run id, timestamp, tool name, arguments, raw tool result, returned proxy result, whether the proxy was enabled, and latency.

How to run
- Direct mode: run the benchmark task calling tools directly via `python -m runner.runner direct --log direct.jsonl`
- Proxied mode: run the benchmark task through the transparent proxy via `python -m runner.runner proxied --log proxied.jsonl`
- Parity test: run the parity integration test via `pytest tests/test_parity.py -q`

What successful parity means
- Final task outputs are identical between direct and proxied runs.
- Tool call orders are identical.
- Tool results are identical.
- The proxy returns exactly what the tool produced (no modifications).
