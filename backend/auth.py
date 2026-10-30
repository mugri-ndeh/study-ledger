"""Accounts: sign up, log in, log out, and the `current_user` dependency.

A login creates a random token. The browser keeps it in an httpOnly cookie; the database keeps
only its SHA-256, so a leaked database can't be used to log in.
"""

import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, Dict, List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import settings
from database import get_session
from models import AuthSession, PlanTemplate, User
from templates import TemplateT, copy_template, find_template

COOKIE = "ledger_session"
CSRF_HEADER = "x-ledger"

hasher = PasswordHash.recommended()  # argon2id
# Verified when the email is unknown, so a wrong email takes as long as a wrong password.
DUMMY_HASH = hasher.hash("not-a-real-password")

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------- rate limit (per process; enough for one server) ----------

class RateLimit:
    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self.hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self.hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise HTTPException(429, "Too many attempts. Wait a minute and try again.")
        hits.append(now)


auth_limit = RateLimit(limit=10, window_seconds=60)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------- sessions ----------

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(session: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.SESSION_DAYS)
    session.add(AuthSession(token_hash=token_hash(token), user_id=user.id, expires_at=expires))
    response.set_cookie(COOKIE, token, max_age=settings.SESSION_DAYS * 86400, httponly=True,
                        secure=settings.COOKIE_SECURE, samesite="lax", path="/")


def optional_user(session: Session = Depends(get_session),
                  ledger_session: Optional[str] = Cookie(None)) -> Optional[User]:
    """The logged-in user, or None. For routes that work for everyone but show admins more."""
    if not ledger_session:
        return None
    row = session.get(AuthSession, token_hash(ledger_session))
    if row is None or row.expires_at <= datetime.now(timezone.utc):
        return None
    return session.get(User, row.user_id)


def current_user(session: Session = Depends(get_session),
                 ledger_session: Optional[str] = Cookie(None)) -> User:
    if not ledger_session:
        raise HTTPException(401, "Log in to continue.")
    user = optional_user(session, ledger_session)
    if user is None:
        raise HTTPException(401, "Your session has expired. Log in again.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "Only an admin can do this.")
    return user


# ---------- routes ----------

class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)
    # How the plan starts: a template slug, "blank", or "upload" with the plan JSON in `plan`.
    template: str = "blank"
    plan: Optional[TemplateT] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=200)


def user_out(user: User) -> Dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name,
            "plan_start": user.plan_start.isoformat(), "is_admin": user.is_admin}


def create_user(session: Session, email: str, password: str, display_name: str, is_admin: bool = False) -> User:
    email = email.strip().lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=email, password_hash=hasher.hash(password), display_name=display_name.strip(), is_admin=is_admin)
    session.add(user)
    session.flush()
    return user


@router.post("/signup", status_code=201)
def signup(body: SignupIn, request: Request, response: Response, session: Session = Depends(get_session)):
    if not settings.SIGNUP_ENABLED:
        raise HTTPException(403, "Sign-up is closed.")
    auth_limit.check(client_ip(request))
    data = None
    if body.template == "upload":
        if body.plan is None:
            raise HTTPException(422, "Choose a plan file to upload.")
        data = body.plan.model_dump()
    elif body.template != "blank":
        template = find_template(session, body.template, None)
        if template is None:
            raise HTTPException(422, "Unknown plan template.")
        data = template.data
    user = create_user(session, body.email, body.password, body.display_name)
    if data:
        copy_template(session, user, data)
    start_session(session, user, response)
    return user_out(user)


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, session: Session = Depends(get_session)):
    auth_limit.check(client_ip(request))
    user = session.scalar(select(User).where(User.email == body.email.strip().lower()))
    valid, new_hash = hasher.verify_and_update(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Wrong email or password.")
    if new_hash:
        user.password_hash = new_hash
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.id,
                                              AuthSession.expires_at <= datetime.now(timezone.utc)))
    start_session(session, user, response)
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(response: Response, session: Session = Depends(get_session), ledger_session: Optional[str] = Cookie(None)):
    if ledger_session:
        session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(ledger_session)))
    response.delete_cookie(COOKIE, path="/")


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)


@router.get("/templates")
def templates(session: Session = Depends(get_session), user: Optional[User] = Depends(optional_user)) -> List[Dict]:
    """Public templates for everyone (the sign-up form lists these); admins also see private ones."""
    stmt = select(PlanTemplate).order_by(PlanTemplate.is_public.desc(), PlanTemplate.id)
    if not (user and user.is_admin):
        stmt = stmt.where(PlanTemplate.is_public)
    rows = session.scalars(stmt).all()
    return [{"slug": t.slug, "name": t.name, "description": t.description,
             "tracks": len(t.data.get("tracks", [])),
             "units": sum(len(tr["units"]) for tr in t.data.get("tracks", []))} for t in rows]
