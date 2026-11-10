from tests.conftest import create_user, login_as


async def test_admin_can_change_roles_and_department(admin):
    u = await create_user("promote@test.io", ["EMPLOYEE"])
    res = await admin.patch(f"/api/v1/users/{u.id}", json={"roles": ["manager", "EMPLOYEE"], "department": "Sales"})
    assert res.status_code == 200, res.text
    user = res.json()["data"]["user"]
    assert user["roles"] == ["EMPLOYEE", "MANAGER"] and user["department"] == "Sales"

    # Role change applies immediately without re-login
    c = await login_as("promote@test.io")
    await admin.patch(f"/api/v1/users/{u.id}", json={"roles": ["EMPLOYEE"]})
    assert (await c.post("/api/v1/expenses/bulk-decision", json={"ids": [1], "action": "approve"})).status_code == 403


async def test_admin_guards(admin):
    me = (await admin.get("/api/v1/auth/me")).json()["data"]["user"]
    res = await admin.patch(f"/api/v1/users/{me['id']}", json={"is_active": False})
    assert res.json()["error"]["code"] == "SELF_LOCKOUT"
    res = await admin.patch(f"/api/v1/users/{me['id']}", json={"roles": ["EMPLOYEE"]})
    assert res.json()["error"]["code"] == "SELF_LOCKOUT"
    res = await admin.patch(f"/api/v1/users/{me['id']}", json={"roles": ["WIZARD"]})
    assert res.json()["error"]["code"] == "UNKNOWN_ROLE"


async def test_non_admin_cannot_manage_users(finance):
    assert (await finance.get("/api/v1/users")).status_code == 403


async def test_list_users_search(admin):
    await create_user("findme@test.io", ["EMPLOYEE"], name="Findable Person")
    data = (await admin.get("/api/v1/users?search=findable")).json()["data"]
    assert data["total"] == 1 and data["items"][0]["email"] == "findme@test.io"
