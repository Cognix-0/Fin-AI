from datetime import date, timedelta

from tests.conftest import login_as

TODAY = date.today().isoformat()


def expense(**overrides) -> dict:
    return {
        "merchant": "Delta Air Lines",
        "amount": 1248.40,
        "expense_date": TODAY,
        "category": "Travel",
        "department": "Sales",
        "notes": "Client visit",
        **overrides,
    }


async def create(client, submit=True, **overrides) -> dict:
    res = await client.post("/api/v1/expenses", json={**expense(**overrides), "submit": submit})
    assert res.status_code == 201, res.text
    return res.json()["data"]["expense"]


async def test_create_draft_and_submit(employee):
    e = await create(employee, submit=False)
    assert e["status"] == "draft"
    assert e["reference"] == f"EXP-{e['id']}"
    assert e["amount"] == 1248.4
    assert e["can_edit"] is True

    res = await employee.post(f"/api/v1/expenses/{e['id']}/submit")
    assert res.json()["data"]["expense"]["status"] == "pending"


async def test_create_validation(employee):
    future = (date.today() + timedelta(days=2)).isoformat()
    res = await employee.post("/api/v1/expenses", json=expense(expense_date=future))
    assert res.status_code == 422
    assert "future" in res.json()["error"]["message"]

    res = await employee.post("/api/v1/expenses", json=expense(category="Yachts"))
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UNKNOWN_CATEGORY"

    res = await employee.post("/api/v1/expenses", json=expense(amount=-5))
    assert res.status_code == 422


async def test_category_lookup_is_case_insensitive(employee):
    e = await create(employee, category="travel", department="sales")
    assert e["category"] == "Travel" and e["department"] == "Sales"


async def test_visibility_rules(employee, employee2, manager, finance):
    mine = await create(employee)
    draft = await create(employee, submit=False)
    other = await create(employee2, department="Engineering")

    # Employees see only their own
    ids = {e["id"] for e in (await employee.get("/api/v1/expenses")).json()["data"]["items"]}
    assert ids == {mine["id"], draft["id"]}
    assert (await employee.get(f"/api/v1/expenses/{other['id']}")).status_code == 404

    # Sales manager sees non-draft Sales expenses only
    ids = {e["id"] for e in (await manager.get("/api/v1/expenses")).json()["data"]["items"]}
    assert ids == {mine["id"]}

    # Finance sees every non-draft expense
    ids = {e["id"] for e in (await finance.get("/api/v1/expenses")).json()["data"]["items"]}
    assert ids == {mine["id"], other["id"]}


async def test_approval_flow_and_history(employee, manager):
    e = await create(employee)
    listed = (await manager.get("/api/v1/expenses?status=pending")).json()["data"]["items"]
    assert listed[0]["can_review"] is True

    res = await manager.post(f"/api/v1/expenses/{e['id']}/approve", json={"comment": "OK"})
    assert res.status_code == 200, res.text
    approved = res.json()["data"]["expense"]
    assert approved["status"] == "approved"
    assert approved["reviewed_by"] == "Mgr"

    # Can't approve twice
    res = await manager.post(f"/api/v1/expenses/{e['id']}/approve")
    assert res.status_code == 409

    history = (await employee.get(f"/api/v1/expenses/{e['id']}/history")).json()["data"]["events"]
    assert [h["action"] for h in history] == ["submitted", "approved"]
    assert history[1]["comment"] == "OK"


async def test_reject_requires_reason_then_resubmit(employee, manager):
    e = await create(employee)
    assert (await manager.post(f"/api/v1/expenses/{e['id']}/reject", json={"reason": ""})).status_code == 422
    res = await manager.post(f"/api/v1/expenses/{e['id']}/reject", json={"reason": "Missing receipt"})
    assert res.json()["data"]["expense"]["rejection_reason"] == "Missing receipt"

    # Submitter edits -> back to draft -> resubmits
    res = await employee.patch(f"/api/v1/expenses/{e['id']}", json={"amount": 99.5})
    edited = res.json()["data"]["expense"]
    assert edited["status"] == "draft" and edited["amount"] == 99.5 and edited["rejection_reason"] is None
    res = await employee.post(f"/api/v1/expenses/{e['id']}/submit")
    assert res.json()["data"]["expense"]["status"] == "pending"


async def test_segregation_of_duties(manager, finance):
    # A manager can't approve their own expense
    own = await create(manager)
    res = await manager.post(f"/api/v1/expenses/{own['id']}/approve")
    assert res.status_code == 403
    # ...but finance can
    assert (await finance.post(f"/api/v1/expenses/{own['id']}/approve")).status_code == 200


async def test_department_manager_cannot_review_other_departments(employee2, manager):
    eng = await create(employee2, department="Engineering")
    # Not even visible to the Sales manager
    assert (await manager.post(f"/api/v1/expenses/{eng['id']}/approve")).status_code == 404


async def test_employee_cannot_approve(employee, employee2):
    e = await create(employee2)
    res = await employee.post(f"/api/v1/expenses/{e['id']}/approve")
    assert res.status_code == 403


async def test_withdraw_and_delete(employee):
    e = await create(employee)
    assert (await employee.delete(f"/api/v1/expenses/{e['id']}")).status_code == 409
    res = await employee.post(f"/api/v1/expenses/{e['id']}/withdraw")
    assert res.json()["data"]["expense"]["status"] == "draft"
    assert (await employee.delete(f"/api/v1/expenses/{e['id']}")).status_code == 204
    assert (await employee.get(f"/api/v1/expenses/{e['id']}")).status_code == 404


async def test_cannot_edit_approved(employee, manager):
    e = await create(employee)
    await manager.post(f"/api/v1/expenses/{e['id']}/approve")
    res = await employee.patch(f"/api/v1/expenses/{e['id']}", json={"amount": 1})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "INVALID_STATUS"


async def test_filters_search_sort_pagination(employee):
    await create(employee, merchant="Figma", category="Software", amount=540)
    await create(employee, merchant="AWS", category="Software", amount=4870.12)
    await create(employee, merchant="Uber", category="Travel", amount=38.9, submit=False)

    data = (await employee.get("/api/v1/expenses?category=Software&sort=-amount")).json()["data"]
    assert [e["merchant"] for e in data["items"]] == ["AWS", "Figma"]

    data = (await employee.get("/api/v1/expenses?search=fig")).json()["data"]
    assert data["total"] == 1

    data = (await employee.get("/api/v1/expenses?status=draft")).json()["data"]
    assert [e["merchant"] for e in data["items"]] == ["Uber"]

    data = (await employee.get("/api/v1/expenses?min_amount=100&max_amount=1000")).json()["data"]
    assert [e["merchant"] for e in data["items"]] == ["Figma"]

    data = (await employee.get("/api/v1/expenses?page_size=2&page=2&sort=amount")).json()["data"]
    assert data["total"] == 3 and data["pages"] == 2 and len(data["items"]) == 1

    # Search by reference
    ref = (await employee.get("/api/v1/expenses?search=uber")).json()["data"]["items"][0]["reference"]
    assert (await employee.get(f"/api/v1/expenses?search={ref}")).json()["data"]["total"] == 1


async def test_bulk_decision(employee, employee2, finance):
    a = await create(employee)
    b = await create(employee2, department="Engineering")
    c = await create(employee, submit=False)
    res = await finance.post("/api/v1/expenses/bulk-decision",
                             json={"ids": [a["id"], b["id"], c["id"]], "action": "approve"})
    data = res.json()["data"]
    assert sorted(data["succeeded"]) == sorted([a["id"], b["id"]])
    assert data["failed"][0]["id"] == c["id"]      # drafts are invisible to finance -> not found

    res = await finance.post("/api/v1/expenses/bulk-decision", json={"ids": [a["id"]], "action": "reject"})
    assert res.status_code == 400


async def test_csv_export_neutralises_formulas(employee):
    await create(employee, merchant="=HYPERLINK(\"evil\")")
    res = await employee.get("/api/v1/expenses/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in res.text
    assert res.text.count("\n") == 2   # header + one row


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def test_receipt_upload_download_replace(employee, manager):
    e = await create(employee)
    res = await employee.post(f"/api/v1/expenses/{e['id']}/receipt",
                              files={"file": ("taxi.png", PNG, "image/png")})
    assert res.status_code == 200, res.text
    assert res.json()["data"]["expense"]["has_receipt"] is True

    # Reviewer can view it
    res = await manager.get(f"/api/v1/expenses/{e['id']}/receipt")
    assert res.status_code == 200
    assert res.content == PNG
    assert res.headers["content-type"] == "image/png"

    # Only the submitter can change it
    res = await manager.post(f"/api/v1/expenses/{e['id']}/receipt", files={"file": ("x.png", PNG, "image/png")})
    assert res.status_code == 403


async def test_receipt_rejects_spoofed_type(employee):
    e = await create(employee)
    res = await employee.post(f"/api/v1/expenses/{e['id']}/receipt",
                              files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")})
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_receipt_size_limit(employee):
    e = await create(employee)
    big = b"%PDF-" + b"0" * (10 * 1024 * 1024 + 10)
    res = await employee.post(f"/api/v1/expenses/{e['id']}/receipt",
                              files={"file": ("big.pdf", big, "application/pdf")})
    assert res.status_code == 413


async def test_missing_receipt_filter(employee):
    e = await create(employee)
    await create(employee, merchant="Other")
    await employee.post(f"/api/v1/expenses/{e['id']}/receipt", files={"file": ("r.png", PNG, "image/png")})
    data = (await employee.get("/api/v1/expenses?missing_receipt=true")).json()["data"]
    assert [x["merchant"] for x in data["items"]] == ["Other"]


async def test_meta(employee):
    data = (await employee.get("/api/v1/meta")).json()["data"]
    assert "Travel" in data["categories"] and "Sales" in data["departments"]
    assert data["statuses"] == ["draft", "pending", "approved", "rejected"]


async def test_manager_without_department_sees_all():
    emp = await login_as("e@test.io", ["EMPLOYEE"], "Marketing")
    await create(emp, department="Marketing")
    mgr = await login_as("floating@test.io", ["MANAGER"])
    assert (await mgr.get("/api/v1/expenses")).json()["data"]["total"] == 1
