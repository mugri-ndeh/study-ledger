"""Plan templates: the starter plan built from curriculum.py and projects.py, copying a template into
an account, and exporting an account's plan back to the same format.

Template format (also used by /api/plan/export and /api/plan/import):
  {"tracks": [{key, name, goal, weekly_target_hours, color,
               "units": [{key, title, why, outcome, skills, requires, project, resources,
                          "steps": [{kind, title, tasks, prompts, done_when, est_minutes, resources}]}]}],
   "projects": [{key, title, difficulty, est_hours, skills, description, features, stretch, unit}],
   "skill_levels": {skill name: 0-3}}
Resources are {title, url, kind}. Only the plan is in a template, never progress.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from curriculum import RECAP_TASKS, TRACKS, UNITS
from models import PlanTemplate, Project, Resource, Skill, Step, Track, Unit, User, UserSkill
from projects import PROJECTS

DEFAULT_SLUG = "python-ai-ml"

BUILD_DONE_WHEN = "Every feature above works, the code is on GitHub, and the README says what it does and how to run it."
RECAP_DONE_WHEN = "Recap questions answered from memory and confidence rated."


# ---------- validation (used for imports) ----------

class ResourceT(BaseModel):
    title: str = Field(min_length=1)
    url: str = ""
    kind: str = "docs"


class StepT(BaseModel):
    kind: Literal["learn", "practice", "build", "recap"]
    title: str = Field(min_length=1)
    tasks: List[str] = []
    prompts: List[str] = []
    done_when: str = ""
    est_minutes: int = Field(ge=1, le=100 * 60)
    resources: List[ResourceT] = []


class UnitT(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1)
    why: str = ""
    outcome: str = ""
    skills: List[str] = []
    requires: Optional[str] = None
    project: Optional[str] = None
    resources: List[ResourceT] = []
    steps: List[StepT] = []


class TrackT(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1)
    goal: str = ""
    weekly_target_hours: float = Field(ge=0, le=80)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    units: List[UnitT] = []


class ProjectT(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    est_hours: float = Field(0, ge=0)
    skills: List[str] = []
    description: str = ""
    features: List[str] = []
    stretch: List[str] = []
    unit: Optional[str] = None


class TemplateT(BaseModel):
    tracks: List[TrackT] = []
    projects: List[ProjectT] = []
    skill_levels: Dict[str, int] = {}

    @model_validator(mode="after")
    def unique_keys(self) -> "TemplateT":
        track_keys = [t.key for t in self.tracks]
        unit_keys = [u.key for t in self.tracks for u in t.units]
        project_keys = [p.key for p in self.projects]
        for name, keys in (("Track", track_keys), ("Unit", unit_keys), ("Project", project_keys)):
            if len(keys) != len(set(keys)):
                raise ValueError(f"{name} keys must be unique.")
        return self


# ---------- the built-in template ----------

def build_default_template() -> Dict[str, Any]:
    """curriculum.py + projects.py, with each unit's build and recap steps written out."""
    projects = {p["key"]: p for p in PROJECTS}
    tracks = []
    for track_key, name, goal, hours, color in TRACKS:
        units = []
        for u in UNITS[track_key]:
            steps = [{"kind": s["kind"], "title": s["title"], "tasks": s["tasks"], "prompts": [],
                      "done_when": s["done_when"], "est_minutes": s["minutes"], "resources": s["resources"]}
                     for s in u["steps"]]
            if u["build"]:
                proj = projects[u["build"]]
                steps.append({"kind": "build", "title": f"Build: {proj['title']}", "tasks": proj["features"],
                              "prompts": [], "done_when": BUILD_DONE_WHEN,
                              "est_minutes": int(proj["est_hours"] * 60), "resources": []})
            steps.append({"kind": "recap", "title": f"Recap: {u['title']}", "tasks": RECAP_TASKS,
                          "prompts": u["recap"], "done_when": RECAP_DONE_WHEN, "est_minutes": 60, "resources": []})
            units.append({"key": u["key"], "title": u["title"], "why": u["why"], "outcome": u["outcome"],
                          "skills": u["skills"], "requires": u["requires"], "project": u["build"],
                          "resources": [], "steps": steps})
        tracks.append({"key": track_key, "name": name, "goal": goal, "weekly_target_hours": hours,
                       "color": color, "units": units})
    return {"tracks": tracks, "projects": PROJECTS, "skill_levels": {}}


def _preset(goal: str, **answers):
    """A starter template made by the plan builder from fixed answers."""
    def build() -> Dict[str, Any]:
        from builder import Answers, generate
        return generate(Answers(goal=goal, **answers))
    return build


# (slug, name, description, public, build). Public ones are offered at sign-up; private ones only to admins.
BUILT_IN = [
    ("starter-backend-python", "Backend developer (Python)",
     "Python, FastAPI, databases, DevOps, with a little DSA and system design. 8 hours a week.", True,
     _preset("backend-python", experience="some", depth="deep", hours_per_week=8)),
    ("starter-frontend", "Frontend developer",
     "JavaScript, TypeScript, React and Next.js, plus interview practice. 8 hours a week.", True,
     _preset("frontend", experience="some", depth="deep", hours_per_week=8)),
    ("starter-ai", "AI engineer",
     "Python, LLM apps (tools, RAG, agents), a backend to ship them, and some ML. 10 hours a week.", True,
     _preset("ai", experience="some", depth="deep", hours_per_week=10)),
    ("starter-data-ml", "Data & machine learning",
     "pandas, statistics, classic ML and deep learning, with SQL. 8 hours a week.", True,
     _preset("data-ml", experience="some", depth="deep", hours_per_week=8)),
    (DEFAULT_SLUG, "Python backend → AI engineering & ML (owner's plan)",
     "The original Study Ledger plan: 7 tracks, 60 units and 46 projects.", False, build_default_template),
]


def upsert_templates(session: Session) -> None:
    """Keep built-in templates in step with the code. Accounts that already copied one are not touched."""
    for slug, name, description, public, build in BUILT_IN:
        data = build()
        tpl = session.scalar(select(PlanTemplate).where(PlanTemplate.slug == slug))
        if tpl is None:
            session.add(PlanTemplate(slug=slug, name=name, description=description, is_public=public, data=data))
        elif (tpl.data, tpl.name, tpl.description, tpl.is_public) != (data, name, description, public):
            tpl.name, tpl.description, tpl.is_public, tpl.data = name, description, public, data


def find_template(session: Session, slug: str, user: Optional[User]) -> Optional[PlanTemplate]:
    """A template the user may use: public ones for everyone, private ones only for admins."""
    tpl = session.scalar(select(PlanTemplate).where(PlanTemplate.slug == slug))
    if tpl is None or (not tpl.is_public and not (user and user.is_admin)):
        return None
    return tpl


# ---------- copy into / out of an account ----------

def clear_plan(session: Session, user: User) -> None:
    """Delete the account's plan, projects and logged sessions (sessions cascade with their track)."""
    session.execute(delete(Project).where(Project.user_id == user.id))
    session.execute(delete(Track).where(Track.user_id == user.id))
    session.flush()


def copy_template(session: Session, user: User, data: Dict[str, Any]) -> None:
    """Create the account's rows from template data (validated first)."""
    tpl = TemplateT.model_validate(data)
    for position, t in enumerate(tpl.tracks):
        track = Track(user_id=user.id, key=t.key, name=t.name, goal=t.goal,
                      weekly_target_hours=t.weekly_target_hours, color=t.color, position=position)
        session.add(track)
        session.flush()
        for unit_seq, u in enumerate(t.units):
            unit = Unit(user_id=user.id, track_id=track.id, key=u.key, seq=unit_seq, title=u.title, why=u.why,
                        outcome=u.outcome, skills=u.skills, requires_key=u.requires, project_key=u.project)
            session.add(unit)
            session.flush()
            for res in u.resources:
                session.add(Resource(user_id=user.id, unit_id=unit.id, title=res.title, url=res.url, kind=res.kind))
            for step_seq, s in enumerate(u.steps):
                step = Step(user_id=user.id, unit_id=unit.id, track_id=track.id, seq=step_seq, kind=s.kind,
                            title=s.title, tasks=s.tasks, prompts=s.prompts, done_when=s.done_when,
                            est_minutes=s.est_minutes)
                session.add(step)
                session.flush()
                for res in s.resources:
                    session.add(Resource(user_id=user.id, unit_id=unit.id, step_id=step.id,
                                         title=res.title, url=res.url, kind=res.kind))
    for p in tpl.projects:
        session.add(Project(user_id=user.id, key=p.key, title=p.title, difficulty=p.difficulty,
                            est_hours=p.est_hours, skills=p.skills, description=p.description,
                            features=p.features, stretch=p.stretch, unit_key=p.unit))
    for name, level in tpl.skill_levels.items():
        set_skill_level(session, user, name, level)
    session.flush()


def set_skill_level(session: Session, user: User, name: str, level: int) -> None:
    if session.get(Skill, name) is None:
        return
    row = session.get(UserSkill, (user.id, name))
    if row is None:
        session.add(UserSkill(user_id=user.id, skill=name, my_level=level))
    else:
        row.my_level = level


def export_plan(session: Session, user: User) -> Dict[str, Any]:
    """The account's plan in template format (structure only, no progress)."""
    tracks = session.scalars(select(Track).where(Track.user_id == user.id).order_by(Track.position)).all()
    units = session.scalars(select(Unit).where(Unit.user_id == user.id).order_by(Unit.seq)).all()
    steps = session.scalars(select(Step).where(Step.user_id == user.id).order_by(Step.seq)).all()
    resources = session.scalars(select(Resource).where(Resource.user_id == user.id).order_by(Resource.id)).all()
    projects = session.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.id)).all()
    levels = session.scalars(select(UserSkill).where(UserSkill.user_id == user.id)).all()

    def res(r: Resource) -> Dict[str, str]:
        return {"title": r.title, "url": r.url, "kind": r.kind}

    out_tracks = []
    for t in tracks:
        out_units = []
        for u in (u for u in units if u.track_id == t.id):
            out_steps = [{"kind": s.kind, "title": s.title, "tasks": s.tasks, "prompts": s.prompts,
                          "done_when": s.done_when, "est_minutes": s.est_minutes,
                          "resources": [res(r) for r in resources if r.step_id == s.id]}
                         for s in steps if s.unit_id == u.id]
            out_units.append({"key": u.key, "title": u.title, "why": u.why, "outcome": u.outcome,
                              "skills": u.skills, "requires": u.requires_key, "project": u.project_key,
                              "resources": [res(r) for r in resources if r.unit_id == u.id and r.step_id is None],
                              "steps": out_steps})
        out_tracks.append({"key": t.key, "name": t.name, "goal": t.goal,
                           "weekly_target_hours": t.weekly_target_hours, "color": t.color, "units": out_units})
    return {
        "tracks": out_tracks,
        "projects": [{"key": p.key, "title": p.title, "difficulty": p.difficulty, "est_hours": p.est_hours,
                      "skills": p.skills, "description": p.description, "features": p.features,
                      "stretch": p.stretch, "unit": p.unit_key} for p in projects],
        "skill_levels": {lv.skill: lv.my_level for lv in levels if lv.my_level},
    }
