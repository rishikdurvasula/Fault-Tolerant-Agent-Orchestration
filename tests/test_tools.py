from tools.tools import get_customer, get_account_balance, search_products


def test_get_customer_deterministic():
    a = get_customer(1)
    b = get_customer(1)
    assert a == b
    assert a["customer_id"] == 1


def test_get_account_balance_deterministic():
    a = get_account_balance(2)
    assert a["balance"] == 212.34


def test_search_products():
    res = search_products("Widget")
    assert "results" in res
    assert isinstance(res["results"], list)
