"""Deterministic benchmark tasks that call tools in a fixed order."""
from typing import Any, Callable, Dict, List, Tuple

def run_benchmark_task(tool_caller: Callable[..., Any], run_id: str, customer_id: int = 42) -> Dict[str, Any]:
    """A small deterministic workflow that calls multiple tools.

    The `tool_caller` callable is expected to have signature
    `tool_caller(run_id, tool_name, *args, **kwargs)`.
    """
    # 1. Get customer
    customer = tool_caller(run_id, "get_customer", customer_id)

    # 2. Get account balance
    balance = tool_caller(run_id, "get_account_balance", customer_id)

    # 3. Search products for the customer name (deterministic string)
    query = customer["name"].split("Customer")[-1]
    products = tool_caller(run_id, "search_products", f"Widget")

    final = {
        "customer": customer,
        "balance": balance,
        "products": products,
    }
    return final
