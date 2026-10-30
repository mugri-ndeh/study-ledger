"""Editing your own plan: tracks, units and steps, plus export / import / reset to a template."""

import re
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from auth import current_user
from database import get_session, owned
import builder
from models import Project, Step, Track, Unit, User
from templates import TemplateT, clear_plan, copy_template, export_plan, find_template

router = APIRouter(prefix="/api", tags=["plan editor"])

COLOR = r"^#[0-9a-fA-F]{6}$"


# ---------- request models ----------

class TrackIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = ""
    weekly_target_hours: float = Field(2, ge=0, le=80)
    color: str = Field("#3566d6", pattern=COLOR)


class TrackPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    goal: Optional[str] = None
    weekly_target_hours: Optional[float] = Field(None, ge=0, le=80)
    color: Optional[str] = Field(None, pattern=COLOR)


class UnitIn(BaseModel):
    track_id: int
    title: str = Field(min_length=1)
    why: str = ""
    outcome: str = ""
    skills: List[str] = []
    requires_key: Optional[str] = None
    with_recap: bool = True  # start the unit with a recap step, like the built-in plan


class UnitPatch(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    why: Optional[str] = None
    outcome: Optional[str] = None
    skills: Optional[List[str]] = None
    requires_key: Optional[str] = None


class StepIn(BaseModel):
    unit_id: int
    kind: Literal["learn", "practice", "build", "recap"] = "learn"
    title: str = Field(min_length=1)
    tasks: List[str] = []
    prompts: List[str] = []
    done_when: str = ""
    est_minutes: int = Field(60, ge=1, le=100 * 60)


class StepPatch(BaseModel):
    kind: Optional[Literal["learn", "practice", "build", "recap"]] = None
    title: Optional[str] = Field(None, min_length=1)
    tasks: Optional[List[str]] = None
    prompts: Optional[List[str]] = None
    done_when: Optional[str] = None
    est_minutes: Optional[int] = Field(None, ge=1, le=100 * 60)


class MoveIn(BaseModel):
    direction: Literal[-1, 1]


class ImportIn(BaseModel):
    plan: TemplateT
    confirm: bool = False


class ResetIn(BaseModel):
    template: str  # a template slug, or "blank"
    confirm: bool = False


class BuildIn(BaseModel):
    answers: builder.Answers
    confirm: bool = False


# ---------- helpers ----------

def patch_fields(row, patch: BaseModel) -> None:
    for field, value in patch.model_dump(exclude_unset=True).items():
        if value is None:
            raise HTTPException(422, f"{field} can't be empty.")
        setattr(row, field, value)


def unique_key(session: Session, model, user: User, text: str) -> str:
    """A short slug from the text, unique among this user's tracks or units."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "item"
    taken = set(session.scalars(select(model.key).where(model.user_id == user.id, model.key.like(f"{base}%"))))
    key, n = base, 2
    while key in taken:
        key, n = f"{base}-{n}", n + 1
    return key


def check_requires(session: Session, user: User, key: Optional[str], unit: Optional[Unit] = None) -> None:
    if key is None:
        return
    if unit is not None and key == unit.key:
        raise HTTPException(422, "A unit can't wait for itself.")
    if not session.scalar(select(Unit.id).where(Unit.user_id == user.id, Unit.key == key)):
        raise HTTPException(422, "The unit it waits for doesn't exist.")


def renumber(rows: List) -> None:
    """Make seq 0..n-1 in the current order (rows sorted by seq, id)."""
    for i, row in enumerate(sorted(rows, key=lambda r: (r.seq, r.id))):
        row.seq = i


def move(rows: List, row, direction: int) -> None:
    ordered = sorted(rows, key=lambda r: (r.seq, r.id))
    i = ordered.index(row)
    j = i + direction
    if 0 <= j < len(ordered):
        ordered[i], ordered[j] = ordered[j], ordered[i]
    for n, r in enumerate(ordered):
        r.seq = n


# ---------- tracks ----------

@router.post("/tracks", status_code=201)
def create_track(body: TrackIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    position = session.scalar(select(func.coalesce(func.max(Track.position) + 1, 0)).where(Track.user_id == user.id))
    track = Track(user_id=user.id, key=unique_key(session, Track, user, body.name), position=position, **body.model_dump())
    session.add(track)
    session.flush()
    return track.to_dict()


@router.patch("/tracks/{track_id}")
def patch_track(track_id: int, patch: TrackPatch, user: User = Depends(current_user),
                session: Session = Depends(get_session)):
    track = owned(session, Track, track_id, user)
    patch_fields(track, patch)
    return track.to_dict()


@router.post("/tracks/{track_id}/move")
def move_track(track_id: int, body: MoveIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    track = owned(session, Track, track_id, user)
    tracks = list(session.scalars(select(Track).where(Track.user_id == user.id)))
    ordered = sorted(tracks, key=lambda t: (t.position, t.id))
    i = ordered.index(track)
    j = i + body.direction
    if 0 <= j < len(ordered):
        ordered[i], ordered[j] = ordered[j], ordered[i]
    for n, t in enumerate(ordered):
        t.position = n
    return {"ok": True}


@router.delete("/tracks/{track_id}", status_code=204)
def delete_track(track_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Deletes the track with its units, steps and logged sessions."""
    track = owned(session, Track, track_id, user)
    unit_keys = list(session.scalars(select(Unit.key).where(Unit.track_id == track.id)))
    session.execute(update(Unit).where(Unit.user_id == user.id, Unit.requires_key.in_(unit_keys)).values(requires_key=None))
    session.execute(update(Project).where(Project.user_id == user.id, Project.unit_key.in_(unit_keys)).values(unit_key=None))
    session.delete(track)


# ---------- units ----------

@router.post("/units", status_code=201)
def create_unit(body: UnitIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    track = owned(session, Track, body.track_id, user)
    check_requires(session, user, body.requires_key)
    seq = session.scalar(select(func.coalesce(func.max(Unit.seq) + 1, 0)).where(Unit.track_id == track.id))
    unit = Unit(user_id=user.id, track_id=track.id, key=unique_key(session, Unit, user, body.title), seq=seq,
                title=body.title, why=body.why, outcome=body.outcome, skills=body.skills, requires_key=body.requires_key)
    session.add(unit)
    session.flush()
    if body.with_recap:
        session.add(Step(user_id=user.id, unit_id=unit.id, track_id=track.id, seq=0, kind="recap",
                         title=f"Recap: {unit.title}", tasks=[], prompts=[],
                         done_when="Recap questions answered from memory and confidence rated.", est_minutes=60))
        session.flush()
    return unit.to_dict()


@router.patch("/units/{unit_id}")
def patch_unit(unit_id: int, patch: UnitPatch, user: User = Depends(current_user), session: Session = Depends(get_session)):
    unit = owned(session, Unit, unit_id, user)
    fields = patch.model_dump(exclude_unset=True)
    if "requires_key" in fields:
        check_requires(session, user, fields["requires_key"], unit)
        unit.requires_key = fields.pop("requires_key")
    for field, value in fields.items():
        if value is None:
            raise HTTPException(422, f"{field} can't be empty.")
        setattr(unit, field, value)
    return unit.to_dict()


@router.post("/units/{unit_id}/move")
def move_unit(unit_id: int, body: MoveIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    unit = owned(session, Unit, unit_id, user)
    move(list(session.scalars(select(Unit).where(Unit.track_id == unit.track_id))), unit, body.direction)
    return {"ok": True}


@router.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Deletes the unit and its steps. Sessions logged against them stay, without a step."""
    unit = owned(session, Unit, unit_id, user)
    session.execute(update(Unit).where(Unit.user_id == user.id, Unit.requires_key == unit.key).values(requires_key=None))
    session.execute(update(Project).where(Project.user_id == user.id, Project.unit_key == unit.key).values(unit_key=None))
    track_id = unit.track_id
    session.delete(unit)
    session.flush()
    renumber(list(session.scalars(select(Unit).where(Unit.track_id == track_id))))


# ---------- steps ----------

@router.post("/steps", status_code=201)
def create_step(body: StepIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """New steps go before the unit's recap, if it has one; otherwise at the end."""
    unit = owned(session, Unit, body.unit_id, user)
    steps = sorted(session.scalars(select(Step).where(Step.unit_id == unit.id)), key=lambda s: (s.seq, s.id))
    recap_at = next((i for i, s in enumerate(steps) if s.kind == "recap"), len(steps))
    if body.kind == "recap":
        recap_at = len(steps)
    step = Step(user_id=user.id, unit_id=unit.id, track_id=unit.track_id, seq=recap_at, **body.model_dump(exclude={"unit_id"}))
    for s in steps[recap_at:]:
        s.seq += 1
    session.add(step)
    session.flush()
    return step.to_dict()


@router.patch("/steps/{step_id}")
def patch_step(step_id: int, patch: StepPatch, user: User = Depends(current_user), session: Session = Depends(get_session)):
    step = owned(session, Step, step_id, user)
    patch_fields(step, patch)
    return step.to_dict()


@router.post("/steps/{step_id}/move")
def move_step(step_id: int, body: MoveIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    step = owned(session, Step, step_id, user)
    move(list(session.scalars(select(Step).where(Step.unit_id == step.unit_id))), step, body.direction)
    return {"ok": True}


@router.delete("/steps/{step_id}", status_code=204)
def delete_step(step_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    step = owned(session, Step, step_id, user)
    unit_id = step.unit_id
    session.delete(step)
    session.flush()
    renumber(list(session.scalars(select(Step).where(Step.unit_id == unit_id))))


# ---------- whole plan ----------

@router.get("/plan/export")
def export(user: User = Depends(current_user), session: Session = Depends(get_session)) -> Dict[str, Any]:
    return export_plan(session, user)


def replace_plan(session: Session, user: User, data: Dict[str, Any]) -> None:
    clear_plan(session, user)
    copy_template(session, user, data)
    user.plan_start = date.today()


@router.post("/plan/import")
def import_plan(body: ImportIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Replace the whole plan. Progress and logged sessions are deleted."""
    if not body.confirm:
        raise HTTPException(422, "Importing replaces your plan and deletes your progress. Send confirm: true.")
    replace_plan(session, user, body.plan.model_dump())
    return {"ok": True}


@router.post("/plan/reset")
def reset_plan(body: ResetIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if not body.confirm:
        raise HTTPException(422, "Resetting deletes your progress. Send confirm: true.")
    data: Dict[str, Any] = {"tracks": [], "projects": []}
    if body.template != "blank":
        tpl = find_template(session, body.template, user)
        if tpl is None:
            raise HTTPException(422, "Unknown plan template.")
        data = tpl.data
    replace_plan(session, user, data)
    return {"ok": True}


# ---------- plan builder ----------

@router.get("/builder/options")
def builder_options():
    """Goals, experience levels, depths and topics for the builder form. Public."""
    return builder.options()


@router.post("/builder/preview")
def builder_preview(answers: builder.Answers):
    """What the answers would produce, without saving anything. Public."""
    return builder.summary(builder.generate(answers))


@router.post("/plan/build")
def build_plan(body: BuildIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Replace the plan with one generated from the answers. Needs confirm when the plan isn't empty."""
    has_plan = session.scalar(select(Track.id).where(Track.user_id == user.id).limit(1)) is not None
    if has_plan and not body.confirm:
        raise HTTPException(422, "Building a new plan replaces yours and deletes your progress. Send confirm: true.")
    plan = builder.generate(body.answers)
    if not plan["tracks"]:
        raise HTTPException(422, "Pick at least one topic.")
    replace_plan(session, user, plan)
    return builder.summary(plan)
