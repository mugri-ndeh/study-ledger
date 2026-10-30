"""Configuration from environment variables (see .env.example)."""

import os


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# Default: the compose Postgres from your machine (`make db`), password from .env.
DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql+psycopg://ledger:{os.environ.get('POSTGRES_PASSWORD', 'ledger')}"
    f"@localhost:{os.environ.get('DB_PORT', '5433')}/ledger")
# Send the session cookie only over HTTPS. Turn on when deployed behind TLS.
COOKIE_SECURE = _bool("COOKIE_SECURE", False)
SESSION_DAYS = int(os.environ.get("SESSION_DAYS", "30"))
SIGNUP_ENABLED = _bool("SIGNUP_ENABLED", True)
# Refresh market data when the latest snapshot is older than this. 0 turns the background refresh off.
MARKET_MAX_AGE_DAYS = int(os.environ.get("MARKET_MAX_AGE_DAYS", "7"))
