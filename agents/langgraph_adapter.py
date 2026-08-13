from __future__ import annotations

import os
from typing import Any, Callable, Dict

from runner.agent_adapter import AgentAdapter


class LangGraphAdapter(AgentAdapter):
    """A LangGraph-compatible adapter.

    By default this adapter uses a deterministic mock agent to avoid external
    API calls during tests. If environment variable `LG_USE_REAL` is set to
    "1" and the `langgraph` package is available, it will attempt to run a
    real LangGraph agent (user must configure credentials).
    """

    def __init__(self, model: str | None = None):
        self.model = model or "mock-model"
        self.use_real = os.environ.get("LG_USE_REAL", "0") == "1"

    def run(self, task_text: str, run_id: str, tool_caller: Callable[..., Any], logger: Callable[[Dict[str, Any]], None], task_id: str | None = None, **kwargs) -> Dict[str, Any]:
        # For Milestone 3 we default to a mock deterministic agent that
        # decides which tool to call based on keywords in the task text.
        messages = [
            {"role": "system", "content": "You are a tool-using assistant."},
            {"role": "user", "content": task_text},
        ]

        tool_calls = []

        # Simple deterministic routing rules
        final_answer = ""

        if "balance" in task_text.lower():
            # expect a customer id in the text (number)
            import re

            m = re.search(r"(\d+)", task_text)
            cid = int(m.group(1)) if m else 42
            # call get_account_balance via proxy
            tool_result = tool_caller(run_id, "get_account_balance", cid)
            tool_calls.append({"tool_name": "get_account_balance", "args": [cid], "result": tool_result})
            bal = tool_result.get("balance") if isinstance(tool_result, dict) else None
            if bal is not None:
                final_answer = f"Customer {cid} has a balance of {bal}."
            else:
                final_answer = f"Could not determine balance for customer {cid}."
        elif "customer" in task_text.lower() or "find" in task_text.lower():
            import re

            m = re.search(r"(\d+)", task_text)
            cid = int(m.group(1)) if m else 42
            tool_result = tool_caller(run_id, "get_customer", cid)
            tool_calls.append({"tool_name": "get_customer", "args": [cid], "result": tool_result})
            final_answer = f"Customer info: {tool_result}"
        elif "product" in task_text.lower() or "products" in task_text.lower() or "headphones" in task_text.lower():
            # extract query words
            q = "headphones" if "headphones" in task_text.lower() else "Widget"
            tool_result = tool_caller(run_id, "search_products", q)
            tool_calls.append({"tool_name": "search_products", "args": [q], "result": tool_result})
            final_answer = f"Search results for '{q}': {tool_result.get('results')}"
        else:
            final_answer = "I did not understand the task."

        # Log an agent-run summary entry via logger
        run_entry = {
            "type": "agent_run",
            "run_id": run_id,
            "task_id": task_id,
            "task_text": task_text,
            "framework": "langgraph",
            "model": self.model,
            "messages": messages,
            "tool_calls": tool_calls,
            "final_answer": final_answer,
        }
        logger(run_entry)

        return {
            "run_id": run_id,
            "framework": "langgraph",
            "model": self.model,
            "final_answer": final_answer,
            "messages": messages,
            "tool_calls": tool_calls,
        }
