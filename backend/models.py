"""Tables. Everything a person owns carries user_id; market data is shared by everyone."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {Dict[str, Any]: JSONB, List[Any]: JSONB}

    def to_dict(self) -> Dict[str, Any]:
        """Column values, with dates as ISO strings (the shape the API and state.py use)."""
        out = {}
        for col in self.__table__.columns:
            value = getattr(self, col.key)
            out[col.key] = value.isoformat() if isinstance(value, (date, datetime)) else value
        return out


def owner() -> Mapped[int]:
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


# ---------- accounts ----------

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(String(80))
    plan_start: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    """A login. The cookie holds a random token; only its SHA-256 is stored."""
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = owner()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PlanTemplate(Base):
    """A starter plan new accounts can copy. `data` uses the same format as /api/plan/export."""
    __tablename__ = "plan_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    # Private templates (like the owner's own plan) are only offered to admins.
    is_public: Mapped[bool] = mapped_column(default=True, server_default="true")
    data: Mapped[Dict[str, Any]]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------- a person's plan ----------

class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("user_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    key: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(120))
    goal: Mapped[str] = mapped_column(Text, default="")
    weekly_target_hours: Mapped[float] = mapped_column(Float)
    color: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer)


class Unit(Base):
    """One chapter of a track: learn -> practice -> build -> recap."""
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("user_id", "key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    seq: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[List[Any]] = mapped_column(default=list)
    requires_key: Mapped[Optional[str]] = mapped_column(String(64))
    project_key: Mapped[Optional[str]] = mapped_column(String(64))


class Step(Base):
    """Steps run in order: by unit seq, then step seq within the unit."""
    __tablename__ = "steps"
    __table_args__ = (
        CheckConstraint("kind IN ('learn', 'practice', 'build', 'recap')", name="step_kind"),
        CheckConstraint("status IN ('todo', 'done')", name="step_status"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="step_rating"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(Text)
    tasks: Mapped[List[Any]] = mapped_column(default=list)
    prompts: Mapped[List[Any]] = mapped_column(default=list)
    done_when: Mapped[str] = mapped_column(Text, default="")
    est_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(8), default="todo")
    started_on: Mapped[Optional[date]] = mapped_column(Date)
    completed_on: Mapped[Optional[date]] = mapped_column(Date)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    reflection: Mapped[str] = mapped_column(Text, default="")


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("steps.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32), default="docs")
    done: Mapped[bool] = mapped_column(default=False)
    # For LeetCode problems: solo, hint or solution.
    outcome: Mapped[str] = mapped_column(String(16), default="")


class StudySession(Base):
    """Time logged against a track's current step."""
    __tablename__ = "sessions"
    __table_args__ = (CheckConstraint("minutes > 0", name="session_minutes"), Index("sessions_user_day", "user_id", "day"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    day: Mapped[date] = mapped_column(Date)
    minutes: Mapped[int] = mapped_column(Integer)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("steps.id", ondelete="SET NULL"), index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("user_id", "key"),
        CheckConstraint("difficulty IN ('beginner', 'intermediate', 'advanced')", name="project_difficulty"),
        CheckConstraint("status IN ('idea', 'building', 'shipped')", name="project_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = owner()
    key: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(16))
    est_hours: Mapped[float] = mapped_column(Float, default=0)
    skills: Mapped[List[Any]] = mapped_column(default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[List[Any]] = mapped_column(default=list)
    stretch: Mapped[List[Any]] = mapped_column(default=list)
    unit_key: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="idea")
    repo_url: Mapped[str] = mapped_column(Text, default="")
    demo_url: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")


# ---------- market demand ----------

class Skill(Base):
    """A skill tracked in job postings. `patterns` are regexes used to spot it in a posting."""
    __tablename__ = "skills"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    patterns: Mapped[List[Any]] = mapped_column(default=list)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    taken_on: Mapped[date] = mapped_column(Date)
    # Numbers are only comparable between snapshots from the same source.
    source: Mapped[str] = mapped_column(String(32))
    postings: Mapped[int] = mapped_column(Integer)
    open_postings: Mapped[int] = mapped_column(Integer)
    companies: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SkillStat(Base):
    __tablename__ = "skill_stats"
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("market_snapshots.id", ondelete="CASCADE"), primary_key=True)
    skill: Mapped[str] = mapped_column(ForeignKey("skills.name", ondelete="CASCADE"), primary_key=True)
    pct_all: Mapped[float] = mapped_column(Float)
    pct_open: Mapped[float] = mapped_column(Float)
    n_all: Mapped[int] = mapped_column(Integer, default=0)
    median_usd: Mapped[Optional[int]] = mapped_column(Integer)


class UserSkill(Base):
    """Self-rating: 0 none, 1 learning, 2 working knowledge, 3 production."""
    __tablename__ = "user_skills"
    __table_args__ = (CheckConstraint("my_level BETWEEN 0 AND 3", name="user_skill_level"),)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill: Mapped[str] = mapped_column(ForeignKey("skills.name", ondelete="CASCADE"), primary_key=True)
    my_level: Mapped[int] = mapped_column(Integer, default=0)
