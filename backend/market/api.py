"""Market demand routes: skills with your level, history, and a manual refresh for admins."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

import state
from auth import admin_user, current_user
from database import get_session
from market import refresh as market_refresh
from models import MarketSnapshot, Skill, SkillStat, User, UserSkill
from templates import set_skill_level

router = APIRouter(prefix="/api", tags=["market"])

REFRESH_COOLDOWN = timedelta(hours=24)


class SkillPatch(BaseModel):
    my_level: int = Field(ge=0, le=3)


def snapshots(session: Session):
    return session.scalars(select(MarketSnapshot).order_by(MarketSnapshot.taken_on.desc(), MarketSnapshot.id.desc())).all()


def stats_for(session: Session, snapshot_id: int) -> Dict[str, SkillStat]:
    return {s.skill: s for s in session.scalars(select(SkillStat).where(SkillStat.snapshot_id == snapshot_id))}


@router.get("/skills")
def list_skills(user: User = Depends(current_user), session: Session = Depends(get_session)):
    snaps = snapshots(session)
    if not snaps:
        return {"snapshot_date": None, "source": None, "previous_date": None, "postings": 0, "open_postings": 0,
                "companies": 0, "skills": []}
    latest = snaps[0]
    # Deltas only against the same source: numbers from different sources aren't comparable.
    previous = next((s for s in snaps[1:] if s.source == latest.source), None)
    now, before = stats_for(session, latest.id), stats_for(session, previous.id) if previous else {}
    levels = dict(session.execute(select(UserSkill.skill, UserSkill.my_level).where(UserSkill.user_id == user.id)).all())
    data = state.load(session, user)
    state.progress(data)
    skills = []
    for name, st in sorted(now.items(), key=lambda kv: -kv[1].pct_all):
        linked = [u for u in data["units"] if name in u["skills"]]
        prev = before.get(name)
        skills.append({
            "name": name, "pct_all": st.pct_all, "pct_open": st.pct_open, "median_usd": st.median_usd,
            "my_level": levels.get(name, 0), "units_total": len(linked), "units_done": sum(u["complete"] for u in linked),
            "delta_all": round(st.pct_all - prev.pct_all, 1) if prev else None,
            "delta_open": round(st.pct_open - prev.pct_open, 1) if prev else None,
        })
    return {"snapshot_date": latest.taken_on.isoformat(), "source": latest.source,
            "previous_date": previous.taken_on.isoformat() if previous else None,
            "postings": latest.postings, "open_postings": latest.open_postings, "companies": latest.companies,
            "skills": skills}


@router.patch("/skills/{name}")
def patch_skill(name: str, patch: SkillPatch, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if session.get(Skill, name) is None:
        raise HTTPException(404, "Not found")
    set_skill_level(session, user, name, patch.my_level)
    return {"name": name, "my_level": patch.my_level}


@router.get("/market/history")
def history(skill: Optional[str] = None, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Every snapshot, oldest first; with ?skill= also that skill's numbers in each."""
    snaps = list(reversed(snapshots(session)))
    stats = {}
    if skill:
        stats = {s.snapshot_id: s for s in session.scalars(select(SkillStat).where(SkillStat.skill == skill))}
    out = []
    for s in snaps:
        row = {"taken_on": s.taken_on.isoformat(), "source": s.source, "postings": s.postings,
               "open_postings": s.open_postings}
        if skill:
            st = stats.get(s.id)
            row.update(pct_all=st.pct_all if st else None, pct_open=st.pct_open if st else None,
                       median_usd=st.median_usd if st else None)
        out.append(row)
    return out


def last_board_refresh(session: Session) -> Optional[datetime]:
    return session.scalar(select(MarketSnapshot.created_at).where(MarketSnapshot.source == "boards")
                          .order_by(MarketSnapshot.created_at.desc()).limit(1))


@router.get("/market/status")
def market_status(user: User = Depends(current_user), session: Session = Depends(get_session)):
    last = last_board_refresh(session)
    return {**market_refresh.status, "last_refresh": last.isoformat() if last else None,
            "can_refresh": user.is_admin and market_refresh.status["running"] is None
            and (last is None or datetime.now(timezone.utc) - last >= REFRESH_COOLDOWN)}


def _run_refresh() -> None:
    try:
        market_refresh.refresh()
    except Exception:
        pass  # the error is kept in market_refresh.status for /market/status


@router.post("/market/refresh", status_code=202)
def start_refresh(background: BackgroundTasks, user: User = Depends(admin_user), session: Session = Depends(get_session)):
    if market_refresh.status["running"]:
        raise HTTPException(409, "A refresh is already running.")
    last = last_board_refresh(session)
    if last and datetime.now(timezone.utc) - last < REFRESH_COOLDOWN:
        raise HTTPException(429, "Market data was refreshed in the last 24 hours.")
    background.add_task(_run_refresh)
    return {"started": True}
