"""Study Ledger API (FastAPI + Postgres).

Run from this folder:  uvicorn main:app --reload
Every route below works on the logged-in user's own rows only.
"""

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import case, select, text, update
from sqlalchemy.orm import Session

import market.api
import market.scheduler
import plan_editor
import state
from auth import CSRF_HEADER, current_user
from auth import router as auth_router
from database import get_session, owned
from models import Base, Project, Resource, Step, StudySession, Unit, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = market.scheduler.start()
    yield
    market.scheduler.stop(task)


app = FastAPI(title="Study Ledger", lifespan=lifespan)


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """Writes must carry a custom header. Other sites can't add one to a cross-site request
    without a CORS preflight, which this API never approves."""
    if (request.method not in ("GET", "HEAD", "OPTIONS") and request.url.path.startswith("/api/")
            and request.headers.get(CSRF_HEADER) != "1"):
        return JSONResponse({"detail": "Missing X-Ledger header."}, status_code=403)
    return await call_next(request)


app.include_router(auth_router)
app.include_router(plan_editor.router)
app.include_router(market.api.router)


# ---------- request models ----------

class SessionIn(BaseModel):
    day: date
    minutes: int = Field(gt=0, le=24 * 60)
    track_id: int
    note: str = ""
    finish_step: bool = False
    rating: Optional[int] = Field(None, ge=1, le=5)
    reflection: str = ""


class CompleteIn(BaseModel):
    day: Optional[date] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    reflection: str = ""


class ResourceIn(BaseModel):
    unit_id: int
    step_id: Optional[int] = None
    title: str = Field(min_length=1)
    url: str = ""
    kind: str = "article"


class ResourcePatch(BaseModel):
    done: Optional[bool] = None
    outcome: Optional[str] = Field(None, pattern="^(|solo|hint|solution)$")


class ProjectIn(BaseModel):
    title: str = Field(min_length=1)
    difficulty: str = Field("intermediate", pattern="^(beginner|intermediate|advanced)$")
    description: str = ""
    skills: List[str] = []
    features: List[str] = []
    est_hours: float = Field(10, ge=0)


class ProjectPatch(BaseModel):
    status: Optional[str] = Field(None, pattern="^(idea|building|shipped)$")
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    notes: Optional[str] = None


# ---------- helpers ----------

def apply_patch(row: Base, patch: BaseModel) -> None:
    """Set only the fields the client sent. Field names come from the model, never the client."""
    for field, value in patch.model_dump(exclude_unset=True).items():
        setattr(row, field, value)


def current_step(session: Session, user: User, track_id: int) -> dict:
    """The one step a track may log against. Raises 409 when the track is finished or waiting on another unit."""
    data = state.load(session, user)
    tp = state.progress(data)
    if track_id not in tp:
        raise HTTPException(404, "Unknown track")
    p = tp[track_id]
    if p["complete"]:
        raise HTTPException(409, "This track is finished.")
    if p["blocked_by"]:
        raise HTTPException(409, f"This track continues after you finish “{p['blocked_by']['title']}”.")
    return next(s for s in data["steps"] if s["id"] == p["current_step_id"])


def set_project_status(session: Session, user: User, unit_id: int, status: str, only_from: Optional[str] = None) -> None:
    unit = session.get(Unit, unit_id)
    if not unit or not unit.project_key:
        return
    stmt = update(Project).where(Project.user_id == user.id, Project.key == unit.project_key).values(status=status)
    if only_from:
        stmt = stmt.where(Project.status == only_from)
    session.execute(stmt)


def finish(session: Session, user: User, step: dict, day: date, rating: Optional[int], reflection: str) -> None:
    if step["kind"] == "recap" and rating is None:
        raise HTTPException(422, "Rate your confidence (1-5) to finish a recap.")
    row = session.get(Step, step["id"])
    row.status, row.completed_on, row.rating, row.reflection = "done", day, rating, reflection
    row.started_on = row.started_on or day
    if step["kind"] == "build":
        set_project_status(session, user, step["unit_id"], "shipped")


# ---------- health ----------

@app.get("/api/health", include_in_schema=False)
def health(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"ok": True}


# ---------- plan & progress ----------

@app.get("/api/plan")
def plan(user: User = Depends(current_user), session: Session = Depends(get_session)):
    data = state.load(session, user)
    tracks = state.progress(data)
    state.schedule(data)
    by_step, by_unit = {}, {}
    for res in session.scalars(select(Resource).where(Resource.user_id == user.id).order_by(Resource.id)):
        if res.step_id is None:
            by_unit.setdefault(res.unit_id, []).append(res.to_dict())
        else:
            by_step.setdefault(res.step_id, []).append(res.to_dict())
    for s in data["steps"]:
        s["resources"] = by_step.get(s["id"], [])
    units = data["units"]
    for u in units:
        u["steps"] = [s for s in data["steps"] if s["unit_id"] == u["id"]]
        u["resources"] = by_unit.get(u["id"], [])
    return {
        "plan_start": data["plan_start"].isoformat(),
        "tracks": [{**t, **tracks[t["id"]]} for t in data["tracks"]],
        "units": units,
    }


@app.get("/api/dashboard")
def dashboard(today: Optional[date] = None, user: User = Depends(current_user),
              session: Session = Depends(get_session)):
    return state.dashboard(session, user, today or date.today())


@app.get("/api/strengths")
def strengths(user: User = Depends(current_user), session: Session = Depends(get_session)):
    return state.strengths(session, user)


# ---------- sessions: always logged against the track's current step ----------

@app.get("/api/sessions")
def list_sessions(limit: int = Query(200, ge=1, le=1000), user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    rows = session.execute(
        select(StudySession, Step.title, Step.kind, Unit.title)
        .outerjoin(Step, Step.id == StudySession.step_id).outerjoin(Unit, Unit.id == Step.unit_id)
        .where(StudySession.user_id == user.id)
        .order_by(StudySession.day.desc(), StudySession.id.desc()).limit(limit)).all()
    return [{**s.to_dict(), "step_title": st, "step_kind": sk, "unit_title": ut} for s, st, sk, ut in rows]


@app.post("/api/sessions", status_code=201)
def create_session(body: SessionIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    step = current_step(session, user, body.track_id)
    session.add(StudySession(user_id=user.id, day=body.day, minutes=body.minutes, track_id=body.track_id,
                             step_id=step["id"], note=body.note))
    row = session.get(Step, step["id"])
    row.started_on = row.started_on or body.day
    if step["kind"] == "build":
        set_project_status(session, user, step["unit_id"], "building", only_from="idea")
    if body.finish_step:
        finish(session, user, step, body.day, body.rating, body.reflection)
    return {"step_id": step["id"], "finished": body.finish_step}


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    session.delete(owned(session, StudySession, session_id, user))


@app.post("/api/steps/{step_id}/complete")
def complete_step(step_id: int, body: CompleteIn, user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    """Finish the current step without logging time, for things you already know."""
    row = owned(session, Step, step_id, user)
    step = current_step(session, user, row.track_id)
    if step["id"] != step_id:
        raise HTTPException(409, "Only a track's current step can be finished.")
    finish(session, user, step, body.day or date.today(), body.rating, body.reflection)
    return {"ok": True}


@app.post("/api/steps/{step_id}/reopen")
def reopen_step(step_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Undo the most recent completion in a track."""
    row = owned(session, Step, step_id, user)
    tp = state.progress(state.load(session, user))
    if tp[row.track_id]["last_done_step_id"] != step_id:
        raise HTTPException(409, "Only the most recently finished step of a track can be reopened.")
    row.status, row.completed_on, row.rating = "todo", None, None
    if row.kind == "build":
        set_project_status(session, user, row.unit_id, "building")
    return {"ok": True}


# ---------- resources ----------

@app.post("/api/resources", status_code=201)
def create_resource(body: ResourceIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    owned(session, Unit, body.unit_id, user)
    if body.step_id is not None and owned(session, Step, body.step_id, user).unit_id != body.unit_id:
        raise HTTPException(422, "That step isn't in that unit.")
    res = Resource(user_id=user.id, **body.model_dump())
    session.add(res)
    session.flush()
    return res.to_dict()


@app.patch("/api/resources/{resource_id}")
def patch_resource(resource_id: int, patch: ResourcePatch, user: User = Depends(current_user),
                   session: Session = Depends(get_session)):
    res = owned(session, Resource, resource_id, user)
    if patch.outcome is not None and "done" not in patch.model_fields_set:
        patch.done = patch.outcome != ""
    apply_patch(res, patch)
    return res.to_dict()


@app.delete("/api/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    session.delete(owned(session, Resource, resource_id, user))


# ---------- projects ----------

@app.get("/api/projects")
def list_projects(user: User = Depends(current_user), session: Session = Depends(get_session)):
    difficulty_order = case({"beginner": 0, "intermediate": 1}, value=Project.difficulty, else_=2)
    rows = session.execute(
        select(Project, Unit.title, Unit.track_id)
        .outerjoin(Unit, (Unit.key == Project.unit_key) & (Unit.user_id == Project.user_id))
        .where(Project.user_id == user.id).order_by(difficulty_order, Project.id)).all()
    return [{**p.to_dict(), "unit_title": ut, "unit_track": utr} for p, ut, utr in rows]


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    proj = Project(user_id=user.id, key="pending", **body.model_dump())
    session.add(proj)
    session.flush()
    proj.key = f"custom-{proj.id}"
    return proj.to_dict()


@app.patch("/api/projects/{project_id}")
def patch_project(project_id: int, patch: ProjectPatch, user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    proj = owned(session, Project, project_id, user)
    apply_patch(proj, patch)
    return proj.to_dict()


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    proj = owned(session, Project, project_id, user)
    if proj.unit_key and session.scalar(select(Unit.id).where(Unit.user_id == user.id, Unit.key == proj.unit_key)):
        raise HTTPException(409, "This project is part of the plan and can't be deleted.")
    session.delete(proj)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PATCH", "PUT", "DELETE"], include_in_schema=False)
def api_not_found(path: str):
    """Unknown /api paths get a JSON 404 instead of the UI's index.html."""
    raise HTTPException(404, "Not found")


# Serve the built frontend (npm run build) from the same server.
DIST = Path(__file__).parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(DIST / "index.html")
