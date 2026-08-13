"""Deterministic test tools for benchmarking."""
from typing import Any, Callable, Dict, List

def get_customer(customer_id: int) -> Dict[str, Any]:
    """Return a deterministic customer record for a given id."""
    return {
        "customer_id": customer_id,
        "name": f"Customer{customer_id}",
        "tier": "gold" if customer_id % 2 == 0 else "silver",
    }

def get_account_balance(customer_id: int) -> Dict[str, Any]:
    """Return a deterministic account balance for a given customer id."""
    balance = float(customer_id * 100 + 12.34)
    return {"customer_id": customer_id, "balance": balance, "currency": "USD"}

def search_products(query: str) -> Dict[str, Any]:
    """Return deterministic product search results for simple queries."""
    catalog = [
        {"id": 1, "name": "Widget"},
        {"id": 2, "name": "Gadget"},
        {"id": 3, "name": "Thingamajig"},
    ]
    matches = [p for p in catalog if query.lower() in p["name"].lower()]
    return {"query": query, "results": matches}


TOOL_REGISTRY: Dict[str, Callable[..., Any]] = {
    "get_customer": get_customer,
    "get_account_balance": get_account_balance,
    "search_products": search_products,
}

def get_tool(name: str) -> Callable[..., Any]:
    return TOOL_REGISTRY[name]
