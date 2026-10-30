"""Tests run against the `ledger_test` database on the compose Postgres (`make db`)."""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://ledger:{}@localhost:{}/ledger_test".format(
    os.environ.get("POSTGRES_PASSWORD", "ledger"), os.environ.get("DB_PORT", "5433")))
os.environ["MARKET_MAX_AGE_DAYS"] = "0"  # no background refresh during tests

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import auth  # noqa: E402
from cli import bootstrap  # noqa: E402
from database import engine  # noqa: E402
from main import app  # noqa: E402
from models import Base  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def schema():
    """Fresh schema from the real migrations, so they're tested too."""
    with engine.begin() as conn:
        Base.metadata.drop_all(conn)
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.upgrade(Config(os.path.join(HERE, "alembic.ini")), "head")
    bootstrap()


@pytest.fixture(autouse=True)
def clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users CASCADE"))
        conn.execute(text("DELETE FROM market_snapshots WHERE source <> 'career-ops'"))
    auth.auth_limit.hits.clear()


def make_client() -> TestClient:
    return TestClient(app, headers={"X-Ledger": "1"})


STARTER = "starter-backend-python"


def signup(client: TestClient, email: str = "ada@example.com", template: str = STARTER) -> dict:
    r = client.post("/api/auth/signup", json={"email": email, "password": "correct horse battery",
                                              "display_name": "Ada", "template": template})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def client():
    with make_client() as c:
        signup(c)
        yield c
