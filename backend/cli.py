"""Admin commands. Run from backend/ (or inside the container):

  python -m cli bootstrap                       templates, skills and the first market snapshot (safe to repeat)
  python -m cli import-sqlite PATH --email E    copy an old single-user learning.db into a new account
  python -m cli make-admin EMAIL                let an account trigger market refreshes
  python -m cli refresh-market                  fetch job postings now and store a new snapshot
"""

import argparse
import getpass
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select

from auth import create_user
from database import SessionLocal
from market.refresh import import_snapshot_file, refresh, upsert_skills
from models import Project, Resource, Skill, Step, StudySession, Track, Unit, User, UserSkill
from templates import upsert_templates


def bootstrap() -> None:
    with SessionLocal.begin() as session:
        upsert_templates(session)
        upsert_skills(session)
        if import_snapshot_file(session):
            print("Imported the career-ops market snapshot.")
    print("Bootstrap done.")


def _password() -> str:
    password = os.environ.get("LEDGER_PASSWORD")
    if password:
        return password
    password = getpass.getpass("Password for the new account (min 10 characters): ")
    if password != getpass.getpass("Repeat it: "):
        sys.exit("Passwords don't match.")
    return password


def _day(value):
    return date.fromisoformat(value) if value else None


def import_sqlite(path: Path, email: str, name: str, admin: bool) -> None:
    """Copy tracks, units, steps, resources, sessions, projects, skill levels and plan_start."""
    if not path.exists():
        sys.exit(f"No database at {path}")
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    def rows(sql):
        return [dict(r) for r in src.execute(sql)]

    def js(value):
        return json.loads(value) if isinstance(value, str) else value

    password = _password()
    if len(password) < 10:
        sys.exit("The password needs at least 10 characters.")

    with SessionLocal.begin() as session:
        if session.scalar(select(User.id).where(User.email == email.strip().lower())):
            sys.exit(f"An account for {email} already exists; nothing imported.")
        user = create_user(session, email, password, name, is_admin=admin)
        meta = {r["key"]: r["value"] for r in rows("SELECT key, value FROM meta")}
        if meta.get("plan_start"):
            user.plan_start = date.fromisoformat(meta["plan_start"])

        track_ids = {}
        for t in rows("SELECT * FROM tracks ORDER BY position"):
            track = Track(user_id=user.id, key=t["id"], name=t["name"], goal=t["goal"],
                          weekly_target_hours=t["weekly_target_hours"], color=t["color"], position=t["position"])
            session.add(track)
            session.flush()
            track_ids[t["id"]] = track.id

        unit_ids = {}
        for u in rows("SELECT * FROM units ORDER BY track_id, seq"):
            unit = Unit(user_id=user.id, track_id=track_ids[u["track_id"]], key=u["key"], seq=u["seq"],
                        title=u["title"], why=u["why"], outcome=u["outcome"], skills=js(u["skills"]),
                        requires_key=u["requires_key"], project_key=u["project_key"])
            session.add(unit)
            session.flush()
            unit_ids[u["id"]] = unit.id

        # Old steps were numbered across the whole track; new ones count from 0 within their unit.
        step_ids, position = {}, {}
        for s in rows("SELECT * FROM steps ORDER BY track_id, seq"):
            seq = position.get(s["unit_id"], 0)
            position[s["unit_id"]] = seq + 1
            step = Step(user_id=user.id, unit_id=unit_ids[s["unit_id"]], track_id=track_ids[s["track_id"]], seq=seq,
                        kind=s["kind"], title=s["title"], tasks=js(s["tasks"]), prompts=js(s["prompts"]),
                        done_when=s["done_when"], est_minutes=s["est_minutes"], status=s["status"],
                        started_on=_day(s["started_on"]), completed_on=_day(s["completed_on"]),
                        rating=s["rating"], reflection=s["reflection"] or "")
            session.add(step)
            session.flush()
            step_ids[s["id"]] = step.id

        for r in rows("SELECT * FROM resources ORDER BY id"):
            session.add(Resource(user_id=user.id, unit_id=unit_ids[r["unit_id"]], step_id=step_ids.get(r["step_id"]),
                                 title=r["title"], url=r["url"], kind=r["kind"], done=bool(r["done"]),
                                 outcome=r["outcome"] or ""))

        for s in rows("SELECT * FROM sessions ORDER BY id"):
            row = StudySession(user_id=user.id, day=date.fromisoformat(s["day"]), minutes=s["minutes"],
                               track_id=track_ids[s["track_id"]], step_id=step_ids.get(s["step_id"]), note=s["note"] or "")
            if s["created_at"]:
                row.created_at = datetime.fromisoformat(s["created_at"]).replace(tzinfo=timezone.utc)
            session.add(row)

        for p in rows("SELECT * FROM projects ORDER BY id"):
            session.add(Project(user_id=user.id, key=p["key"], title=p["title"], difficulty=p["difficulty"],
                                est_hours=p["est_hours"], skills=js(p["skills"]), description=p["description"],
                                features=js(p["features"]), stretch=js(p["stretch"]), unit_key=p["unit_key"],
                                status=p["status"], repo_url=p["repo_url"], demo_url=p["demo_url"], notes=p["notes"]))

        upsert_skills(session)
        import_snapshot_file(session)
        for s in rows("SELECT name, my_level FROM skills WHERE my_level > 0"):
            if session.get(Skill, s["name"]) is not None:
                session.add(UserSkill(user_id=user.id, skill=s["name"], my_level=s["my_level"]))

        counts = {name: len(v) for name, v in (("tracks", track_ids), ("units", unit_ids), ("steps", step_ids))}
    done = src.execute("SELECT COUNT(*) FROM steps WHERE status = 'done'").fetchone()[0]
    logged = src.execute("SELECT COUNT(*), COALESCE(SUM(minutes), 0) FROM sessions").fetchone()
    src.close()
    print(f"Imported into {email}: {counts}, {done} finished steps, {logged[0]} sessions ({logged[1]} minutes).")


def make_admin(email: str) -> None:
    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            sys.exit(f"No account for {email}")
        user.is_admin = True
    print(f"{email} is now an admin.")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("bootstrap")
    imp = sub.add_parser("import-sqlite")
    imp.add_argument("path", type=Path)
    imp.add_argument("--email", required=True)
    imp.add_argument("--name", default="Me")
    imp.add_argument("--admin", action="store_true")
    adm = sub.add_parser("make-admin")
    adm.add_argument("email")
    sub.add_parser("refresh-market")
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        bootstrap()
    elif args.command == "import-sqlite":
        import_sqlite(args.path, args.email, args.name, args.admin)
    elif args.command == "make-admin":
        make_admin(args.email)
    elif args.command == "refresh-market":
        snap = refresh()
        print("Another refresh is running." if snap is None else f"Stored market snapshot {snap}.")


if __name__ == "__main__":
    main()
