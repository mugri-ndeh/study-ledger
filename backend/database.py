"""Postgres connection: one SQLAlchemy session per request."""

from typing import Iterator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: commits on success, rolls back on error."""
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def owned(session: Session, model, ident: int, user):
    """The row with this id if the user owns it; 404 otherwise (never reveal other people's ids)."""
    row = session.get(model, ident)
    if row is None or row.user_id != user.id:
        raise HTTPException(404, "Not found")
    return row
