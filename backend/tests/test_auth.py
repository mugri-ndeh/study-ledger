from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from conftest import make_client, signup
from database import SessionLocal
from models import AuthSession


def test_signup_login_logout_me():
    with make_client() as c:
        assert c.get("/api/auth/me").status_code == 401
        user = signup(c, "Ada@Example.com")
        assert user["email"] == "ada@example.com"
        assert c.get("/api/auth/me").json()["display_name"] == "Ada"
        assert c.post("/api/auth/logout").status_code == 204
        assert c.get("/api/auth/me").status_code == 401
        assert c.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong password!"}).status_code == 401
        assert c.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct horse battery"}).status_code == 200
        assert c.get("/api/plan").status_code == 200


def test_cookie_is_httponly():
    with make_client() as c:
        r = c.post("/api/auth/signup", json={"email": "b@example.com", "password": "correct horse battery",
                                             "display_name": "B", "template": "blank"})
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie


def test_duplicate_email_and_short_password():
    with make_client() as c:
        signup(c)
        assert c.post("/api/auth/signup", json={"email": "ada@example.com", "password": "correct horse battery",
                                                "display_name": "A"}).status_code == 409
        assert c.post("/api/auth/signup", json={"email": "x@example.com", "password": "short",
                                                "display_name": "X"}).status_code == 422


def test_expired_session(client):
    with SessionLocal.begin() as s:
        s.execute(update(AuthSession).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
    assert client.get("/api/plan").status_code == 401


def test_writes_need_csrf_header(client):
    r = client.post("/api/projects", json={"title": "x"}, headers={"X-Ledger": ""})
    assert r.status_code == 403


def test_rate_limit():
    with make_client() as c:
        codes = [c.post("/api/auth/login", json={"email": "n@example.com", "password": "nope"}).status_code
                 for _ in range(11)]
        assert codes[-1] == 429 and 429 not in codes[:10]


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["detail"] == "Not found"
