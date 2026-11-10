from datetime import date

from app.services.dates import add_months, period_bounds
from tests.test_expenses import create

THIS_MONTH = date.today().replace(day=1).isoformat()


async def test_budget_crud_and_status(finance, employee, manager):
    res = await finance.put("/api/v1/budgets", json={"department": "Sales", "month": THIS_MONTH, "amount_limit": 1000})
    assert res.status_code == 200, res.text

    e1 = await create(employee, amount=600)
    await manager.post(f"/api/v1/expenses/{e1['id']}/approve")
    await create(employee, amount=300)          # pending

    items = (await employee.get("/api/v1/budgets")).json()["data"]["items"]
    sales = next(b for b in items if b["department"] == "Sales")
    assert sales["limit"] == 1000 and sales["spent"] == 600 and sales["pending"] == 300
    assert sales["remaining"] == 100 and sales["status"] == "near_limit"
    eng = next(b for b in items if b["department"] == "Engineering")
    assert eng["status"] == "no_budget"

    await create(employee, amount=200)
    sales = next(b for b in (await employee.get("/api/v1/budgets")).json()["data"]["items"]
                 if b["department"] == "Sales")
    assert sales["status"] == "over_budget"

    # Upsert updates rather than duplicating
    await finance.put("/api/v1/budgets", json={"department": "Sales", "month": THIS_MONTH, "amount_limit": 5000})
    items = (await finance.get("/api/v1/budgets?include_unbudgeted=false")).json()["data"]["items"]
    assert len(items) == 1 and items[0]["limit"] == 5000

    assert (await finance.delete(f"/api/v1/budgets/{items[0]['id']}")).status_code == 204


async def test_only_finance_can_manage_budgets(employee, manager):
    body = {"department": "Sales", "month": THIS_MONTH, "amount_limit": 1}
    assert (await employee.put("/api/v1/budgets", json=body)).status_code == 403
    assert (await manager.put("/api/v1/budgets", json=body)).status_code == 403


async def test_copy_budgets(finance):
    prev = add_months(date.today(), -1).isoformat()
    for dept in ("Sales", "Engineering"):
        await finance.put("/api/v1/budgets", json={"department": dept, "month": prev, "amount_limit": 500})
    await finance.put("/api/v1/budgets", json={"department": "Sales", "month": THIS_MONTH, "amount_limit": 900})

    res = await finance.post("/api/v1/budgets/copy", json={"from_month": prev, "to_month": THIS_MONTH})
    assert res.json()["data"] == {"created": 1, "updated": 0, "skipped": 1}


async def test_analytics_summary(finance, employee, manager):
    await finance.put("/api/v1/budgets", json={"department": "Sales", "month": THIS_MONTH, "amount_limit": 1000})
    a = await create(employee, amount=800, merchant="AWS", category="Software")
    await manager.post(f"/api/v1/expenses/{a['id']}/approve")
    await create(employee, amount=400, merchant="Uber")                     # pending, no receipt
    await create(employee, amount=50, merchant="Cafe", submit=False)        # draft: excluded

    data = (await finance.get("/api/v1/analytics/summary?period=30d")).json()["data"]
    k = data["kpis"]
    assert data["scope"] == "company"
    assert k["total_spend"] == 1200 and k["expense_count"] == 2
    assert k["pending_count"] == 1 and k["pending_total"] == 400
    assert k["missing_receipts"] == 2
    assert k["budget_limit"] == 1000 and k["budget_utilization"] == 120.0
    assert len(data["monthly"]) == 12 and data["monthly"][-1]["amount"] == 1200
    assert data["by_category"][0] == {"category": "Software", "amount": 800.0, "share": 66.7}
    assert data["top_merchants"][0]["merchant"] == "AWS"

    kinds = {i["kind"] for i in data["insights"]}
    assert "budget" in kinds and "receipts" in kinds
    assert data["insights"][0]["tone"] == "warning"


async def test_analytics_scoped_for_employees(employee, employee2):
    await create(employee, amount=100)
    await create(employee2, amount=999, department="Engineering")
    data = (await employee.get("/api/v1/analytics/summary")).json()["data"]
    assert data["scope"] == "personal"
    assert data["kpis"]["total_spend"] == 100


async def test_duplicate_insight(finance, employee):
    await create(employee, amount=75, merchant="Uber")
    await create(employee, amount=75, merchant="Uber")
    insights = (await finance.get("/api/v1/analytics/insights")).json()["data"]["insights"]
    assert any(i["kind"] == "duplicates" for i in insights)


def test_period_bounds():
    start, end, prev_start, prev_end = period_bounds("30d", date(2026, 3, 31))
    assert (end - start).days == 29
    assert (prev_end - prev_start).days == 29
    assert (start - prev_end).days == 1
    assert add_months(date(2026, 1, 31), -1) == date(2025, 12, 1)
    assert add_months(date(2026, 11, 15), 2) == date(2027, 1, 1)
