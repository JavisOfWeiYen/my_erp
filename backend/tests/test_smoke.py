def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_login_and_me(auth):
    c = auth("admin")
    r = c.get("/api/v1/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "admin"
    assert body["role"]["name"] == "admin"


def test_wrong_password_rejected(client):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert r.status_code == 401
