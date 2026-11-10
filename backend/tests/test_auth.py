from tests.conftest import PASSWORD, create_user, login_as, make_client

REGISTER = {
    "full_name": "Test User",
    "email": "new@test.io",
    "password": "Password1",
    "confirm_password": "Password1",
}


async def test_health_endpoints(client):
    assert (await client.get("/api/v1/health")).json()["status"] == "ok"
    assert (await client.get("/api/v1/health/live")).status_code == 200
    res = await client.get("/api/v1/health/ready")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Content-Type-Options"] == "nosniff"


async def test_register_sets_cookies_and_employee_role(client):
    res = await client.post("/api/v1/auth/register", json=REGISTER)
    assert res.status_code == 201, res.text
    user = res.json()["data"]["user"]
    assert user["roles"] == ["EMPLOYEE"]
    assert "access_token" in res.cookies and "refresh_token" in res.cookies

    me = await client.get("/api/v1/auth/me")
    assert me.json()["data"]["user"]["email"] == "new@test.io"


async def test_register_duplicate_email(client):
    await client.post("/api/v1/auth/register", json=REGISTER)
    res = await make_client().post("/api/v1/auth/register", json=REGISTER)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EMAIL_TAKEN"


async def test_validation_errors_use_envelope(client):
    res = await client.post("/api/v1/auth/register", json={**REGISTER, "password": "weak", "confirm_password": "weak"})
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "8 characters" in body["error"]["message"]


async def test_password_mismatch(client):
    res = await client.post("/api/v1/auth/register", json={**REGISTER, "confirm_password": "Password2"})
    assert res.status_code == 422
    assert res.json()["error"]["message"] == "Passwords do not match"


async def test_login_wrong_password_and_lockout(client):
    await create_user("lock@test.io", ["EMPLOYEE"])
    for _ in range(5):
        res = await client.post("/api/v1/auth/login", json={"email": "lock@test.io", "password": "Wrong1234"})
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"
    res = await client.post("/api/v1/auth/login", json={"email": "lock@test.io", "password": PASSWORD})
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


async def test_unauthenticated_requests_rejected(client):
    res = await client.get("/api/v1/expenses")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "NOT_AUTHENTICATED"


async def test_refresh_rotates_and_detects_reuse():
    c = await login_as("rot@test.io", ["EMPLOYEE"])
    old_refresh = c.cookies.get("refresh_token")

    res = await c.post("/api/v1/auth/refresh")
    assert res.status_code == 200, res.text
    new_refresh = c.cookies.get("refresh_token")
    assert new_refresh and new_refresh != old_refresh

    # Replaying the old (rotated) token revokes every session for the user
    attacker = make_client()
    attacker.cookies.set("refresh_token", old_refresh)
    assert (await attacker.post("/api/v1/auth/refresh")).status_code == 401

    # ...including the legitimate client's newer token
    victim = make_client()
    victim.cookies.set("refresh_token", new_refresh)
    assert (await victim.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_revokes_refresh_token():
    c = await login_as("out@test.io", ["EMPLOYEE"])
    token = c.cookies.get("refresh_token")
    assert (await c.post("/api/v1/auth/logout")).status_code == 200
    replay = make_client()
    replay.cookies.set("refresh_token", token)
    assert (await replay.post("/api/v1/auth/refresh")).status_code == 401


async def test_update_profile_and_change_password():
    c = await login_as("me@test.io", ["EMPLOYEE"])
    res = await c.patch("/api/v1/auth/me", json={"full_name": "  New   Name "})
    assert res.json()["data"]["user"]["full_name"] == "New Name"

    res = await c.post("/api/v1/auth/change-password", json={
        "current_password": "nope", "new_password": "Another123", "confirm_password": "Another123",
    })
    assert res.status_code == 400
    res = await c.post("/api/v1/auth/change-password", json={
        "current_password": PASSWORD, "new_password": "Another123", "confirm_password": "Another123",
    })
    assert res.status_code == 200, res.text

    fresh = make_client()
    assert (await fresh.post("/api/v1/auth/login", json={"email": "me@test.io", "password": "Another123"})).status_code == 200


async def test_deactivated_user_is_locked_out_immediately(admin):
    user = await create_user("gone@test.io", ["EMPLOYEE"])
    c = make_client()
    await c.post("/api/v1/auth/login", json={"email": "gone@test.io", "password": PASSWORD})
    assert (await c.get("/api/v1/expenses")).status_code == 200

    res = await admin.patch(f"/api/v1/users/{user.id}", json={"is_active": False})
    assert res.status_code == 200, res.text

    # Existing access token no longer works, and refresh is refused
    res = await c.get("/api/v1/expenses")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "ACCOUNT_INACTIVE"
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401
