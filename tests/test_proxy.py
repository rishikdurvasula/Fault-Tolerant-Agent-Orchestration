import tempfile
from trajlog.trajectory import TrajectoryLogger
from proxy.proxy import TransparentProxy
from tools.tools import TOOL_REGISTRY


def test_proxy_transparent(tmp_path):
    log_path = str(tmp_path / "proxy.jsonl")
    logger = TrajectoryLogger(log_path)
    proxy = TransparentProxy(TOOL_REGISTRY, logger)

    run_id = "test-run"
    res = proxy.call(run_id, "get_customer", 5)
    assert res == TOOL_REGISTRY["get_customer"](5)

    entries = logger.read_all()
    assert len(entries) == 1
    e = entries[0]
    assert e["proxy_enabled"] is True
    assert e["raw_tool_result"] == e["returned_proxy_result"]
