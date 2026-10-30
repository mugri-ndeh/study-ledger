"""Derived state: where each track is, the planned schedule, today's plan and strengths.

Nothing here writes to the database; routes in main.py call these for the logged-in user.
"""

import math
from datetime import date, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Resource, Step, StudySession, Track, Unit, User

PROBLEM_SCORE = {"solo": 1.0, "hint": 0.6, "solution": 0.3}


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def load(session: Session, user: User) -> Dict:
    """The user's tracks, units and steps as dicts. Steps are in plan order: unit seq, then step seq."""
    tracks = [t.to_dict() for t in session.scalars(
        select(Track).where(Track.user_id == user.id).order_by(Track.position, Track.id))]
    units = [u.to_dict() for u in session.scalars(
        select(Unit).where(Unit.user_id == user.id).order_by(Unit.track_id, Unit.seq, Unit.id))]
    unit_seq = {u["id"]: u["seq"] for u in units}
    steps = [s.to_dict() for s in session.scalars(select(Step).where(Step.user_id == user.id))]
    steps.sort(key=lambda s: (s["track_id"], unit_seq[s["unit_id"]], s["seq"], s["id"]))
    logged = dict(session.execute(
        select(StudySession.step_id, func.sum(StudySession.minutes))
        .where(StudySession.user_id == user.id, StudySession.step_id.is_not(None))
        .group_by(StudySession.step_id)).all())
    for s in steps:
        s["logged_minutes"] = int(logged.get(s["id"], 0))
    return {"tracks": tracks, "units": units, "steps": steps, "plan_start": user.plan_start}


def progress(data: Dict) -> Dict:
    """Per-unit status and per-track cursor. A track's current step is its first unfinished step."""
    units_by_key = {u["key"]: u for u in data["units"]}
    steps_by_unit: Dict[int, List[Dict]] = {}
    for s in data["steps"]:
        steps_by_unit.setdefault(s["unit_id"], []).append(s)

    for u in data["units"]:
        own = steps_by_unit.get(u["id"], [])
        u["steps_total"] = len(own)
        u["steps_done"] = sum(s["status"] == "done" for s in own)
        u["est_minutes"] = sum(s["est_minutes"] for s in own)
        u["logged_minutes"] = sum(s["logged_minutes"] for s in own)
        u["complete"] = bool(own) and u["steps_done"] == len(own)
        recap = next((s for s in own if s["kind"] == "recap"), None)
        u["rating"] = recap["rating"] if recap else None

    tracks = {}
    for t in data["tracks"]:
        own = [s for s in data["steps"] if s["track_id"] == t["id"]]
        current = next((s for s in own if s["status"] != "done"), None)
        blocked_by = None
        if current:
            unit = next(u for u in data["units"] if u["id"] == current["unit_id"])
            req = units_by_key.get(unit["requires_key"]) if unit["requires_key"] else None
            if req and not req["complete"]:
                blocked_by = {"key": req["key"], "title": req["title"], "track_id": req["track_id"]}
        done = [s for s in own if s["status"] == "done"]
        last_done = done[-1] if done else None
        tracks[t["id"]] = {
            "current_step_id": current["id"] if current else None,
            "current_unit_id": current["unit_id"] if current else None,
            "blocked_by": blocked_by,
            "complete": current is None,
            "steps_done": len(done),
            "steps_total": len(own),
            "est_minutes_done": sum(s["est_minutes"] for s in done),
            "est_minutes_total": sum(s["est_minutes"] for s in own),
            "last_done_step_id": last_done["id"] if last_done else None,
        }

    for u in data["units"]:
        tp = tracks[u["track_id"]]
        if u["complete"]:
            u["state"] = "done"
        elif tp["current_unit_id"] == u["id"]:
            u["state"] = "blocked" if tp["blocked_by"] else "current"
        else:
            u["state"] = "upcoming"
    return tracks


def schedule(data: Dict) -> None:
    """Planned start/end week for every unit, at each track's weekly target, honouring `requires`."""
    rate = {t["id"]: max(t["weekly_target_hours"], 0.25) * 60 for t in data["tracks"]}
    units = data["units"]
    by_key = {u["key"]: u for u in units}
    for u in units:
        u["plan_start_week"] = 0.0
        u["plan_end_week"] = 0.0
    for _ in range(12):  # dependencies span tracks; repeat until stable
        changed = False
        prev_end: Dict[str, float] = {}
        for u in units:
            start = prev_end.get(u["track_id"], 0.0)
            req = by_key.get(u["requires_key"]) if u["requires_key"] else None
            if req:
                start = max(start, req["plan_end_week"])
            end = start + u["est_minutes"] / rate[u["track_id"]]
            if abs(start - u["plan_start_week"]) > 1e-6 or abs(end - u["plan_end_week"]) > 1e-6:
                changed = True
            u["plan_start_week"], u["plan_end_week"] = round(start, 3), round(end, 3)
            prev_end[u["track_id"]] = end
        if not changed:
            break


def streaks(days: set, today: date):
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    prev: Optional[date] = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = d
    return current, longest


def dashboard(session: Session, user: User, today: date) -> Dict:
    data = load(session, user)
    tp = progress(data)
    week_start = monday(today)

    sessions = session.execute(select(StudySession.day, StudySession.minutes, StudySession.track_id)
                               .where(StudySession.user_id == user.id)).all()
    per_day: Dict[date, int] = {}
    per_week_track: Dict[date, Dict[int, int]] = {}
    for d, minutes, track_id in sessions:
        per_day[d] = per_day.get(d, 0) + minutes
        wk = per_week_track.setdefault(monday(d), {})
        wk[track_id] = wk.get(track_id, 0) + minutes

    current, longest = streaks({d for d, m in per_day.items() if m > 0}, today)
    week = per_week_track.get(week_start, {})
    weekly_target = sum(t["weekly_target_hours"] for t in data["tracks"]) * 60

    # Today's plan: a few focused 30-90 minute blocks, chosen from the tracks furthest behind
    # their weekly target, until today's share of what's left this week is covered.
    days_left = 7 - today.weekday()
    steps_by_id = {s["id"]: s for s in data["steps"]}
    units_by_id = {u["id"]: u for u in data["units"]}
    today_plan = []
    for t in data["tracks"]:
        p = tp[t["id"]]
        if p["complete"]:
            continue
        step = steps_by_id[p["current_step_id"]]
        today_plan.append({
            "track_id": t["id"], "week_minutes": week.get(t["id"], 0),
            "target_minutes": t["weekly_target_hours"] * 60, "blocked_by": p["blocked_by"],
            "deficit": max(0, t["weekly_target_hours"] * 60 - week.get(t["id"], 0)),
            "step": step, "unit": {k: units_by_id[step["unit_id"]][k] for k in ("id", "key", "title", "seq")},
        })
    open_items = sorted((x for x in today_plan if not x["blocked_by"] and x["deficit"] > 0), key=lambda x: -x["deficit"])
    budget = sum(x["deficit"] for x in open_items) / days_left
    for x in today_plan:
        x["slot"], x["suggested_minutes"] = ("blocked" if x["blocked_by"] else "done_for_week"), 0
    for x in open_items:
        block = min(90, max(30, int(math.ceil(x["deficit"] / 15.0)) * 15))
        block = min(block, int(math.ceil(x["deficit"] / 15.0)) * 15)
        if budget > 0:
            block = min(block, max(30, int(math.ceil(budget / 15.0)) * 15))
            x["slot"], x["suggested_minutes"] = "today", block
            budget -= block
        else:
            x["slot"] = "later"
    order = {"today": 0, "later": 1, "done_for_week": 2, "blocked": 3}
    today_plan.sort(key=lambda x: (order[x["slot"]], -x["deficit"]))

    heat_start = week_start - timedelta(weeks=25)
    heatmap = [{"day": (heat_start + timedelta(days=i)).isoformat(),
                "minutes": per_day.get(heat_start + timedelta(days=i), 0)}
               for i in range((today - heat_start).days + 1)]

    weekly = []
    for i in range(11, -1, -1):
        ws = week_start - timedelta(weeks=i)
        weekly.append({"week_start": ws.isoformat(), "tracks": per_week_track.get(ws, {})})

    start_week = monday(data["plan_start"])
    n_weeks = max(1, min(104, (week_start - start_week).days // 7 + 1))
    burnup, cumulative = [], 0
    for i in range(n_weeks):
        ws = start_week + timedelta(weeks=i)
        cumulative += sum(per_week_track.get(ws, {}).values())
        burnup.append({"week_start": ws.isoformat(), "actual_minutes": cumulative, "planned_minutes": weekly_target * (i + 1)})

    track_rows = []
    for t in data["tracks"]:
        p = tp[t["id"]]
        remaining = p["est_minutes_total"] - p["est_minutes_done"]
        weeks_left = remaining / max(t["weekly_target_hours"] * 60, 1)
        track_rows.append({**t, **p, "week_minutes": week.get(t["id"], 0),
                           "total_minutes": sum(per_week_track.get(w, {}).get(t["id"], 0) for w in per_week_track),
                           "projected_finish": (today + timedelta(weeks=weeks_left)).isoformat()})

    return {
        "today": today.isoformat(), "week_start": week_start.isoformat(), "plan_start": data["plan_start"].isoformat(),
        "current_streak": current, "longest_streak": longest, "studied_today": per_day.get(today, 0) > 0,
        "total_minutes": sum(per_day.values()),
        "last7_minutes": sum(per_day.get(today - timedelta(days=i), 0) for i in range(7)),
        "week_minutes": sum(week.values()), "week_target_minutes": weekly_target,
        "tracks": track_rows, "today_plan": today_plan, "heatmap": heatmap, "weekly": weekly, "burnup": burnup,
    }


def strengths(session: Session, user: User) -> Dict:
    data = load(session, user)
    tp = progress(data)
    problems = [{"unit_id": unit_id, "outcome": outcome} for unit_id, outcome in session.execute(
        select(Resource.unit_id, Resource.outcome).where(Resource.user_id == user.id, Resource.kind == "problem"))]

    tracks = []
    for t in data["tracks"]:
        rated = [u["rating"] for u in data["units"] if u["track_id"] == t["id"] and u["rating"]]
        p = tp[t["id"]]
        tracks.append({"id": t["id"], "name": t["name"], "color": t["color"],
                       "confidence": round(sum(rated) / len(rated), 2) if rated else None,
                       "rated_units": len(rated),
                       "coverage": round(p["est_minutes_done"] / p["est_minutes_total"], 3) if p["est_minutes_total"] else 0})

    # Practice-problem patterns: any unit with LeetCode-style problems, whichever track it's in.
    patterns = []
    for u in data["units"]:
        own = [x for x in problems if x["unit_id"] == u["id"]]
        if not own:
            continue
        counts = {k: sum(x["outcome"] == k for x in own) for k in ("solo", "hint", "solution")}
        score = sum(PROBLEM_SCORE.get(x["outcome"], 0) for x in own) / len(own)
        patterns.append({"key": u["key"], "title": u["title"], "total": len(own), **counts,
                         "untouched": len(own) - sum(counts.values()), "score": round(score, 3), "rating": u["rating"]})

    skill_ratings: Dict[str, List[int]] = {}
    for u in data["units"]:
        if u["rating"]:
            for sk in u["skills"]:
                skill_ratings.setdefault(sk, []).append(u["rating"])
    skills = sorted(({"name": k, "confidence": round(sum(v) / len(v), 2), "units": len(v)} for k, v in skill_ratings.items()),
                    key=lambda x: -x["confidence"])

    recaps = {s["unit_id"]: s for s in data["steps"] if s["kind"] == "recap" and s["status"] == "done"}
    rated_units = [{"key": u["key"], "title": u["title"], "track_id": u["track_id"], "rating": u["rating"],
                    "reflection": recaps[u["id"]]["reflection"], "completed_on": recaps[u["id"]]["completed_on"]}
                   for u in data["units"] if u["id"] in recaps and u["rating"]]

    return {
        "tracks": tracks, "patterns": patterns, "skills": skills,
        "strong": sorted([u for u in rated_units if u["rating"] >= 4], key=lambda u: -u["rating"]),
        "weak": sorted([u for u in rated_units if u["rating"] <= 2], key=lambda u: u["rating"]),
        "timeline": sorted(rated_units, key=lambda u: u["completed_on"] or ""),
    }
