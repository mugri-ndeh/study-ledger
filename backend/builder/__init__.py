"""The plan builder: turns a few answers (goal, experience, depth, hours, topics) into a plan.

Pure code, no LLM: it picks units from builder/library.py by level, splits the weekly hours
between topics by weight, and writes the result in the template format (see templates.py),
so it can be previewed, copied into an account and edited like any other plan.
"""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

from builder.library import DEPTH, EXPERIENCE, GOALS, TOPICS

RECAP_TASKS = [
    "Close your notes. On a blank page, explain this unit's main ideas as if teaching a friend.",
    "Answer the recap questions below from memory, then check yourself.",
    "Redo one exercise from this unit from scratch without looking at your old code.",
    "Write your weak spots in the reflection box.",
    "Rate your confidence honestly: 1 = lost, 3 = can do it with notes, 5 = could teach it.",
]
BUILD_DONE_WHEN = "Every feature above works, the code is on GitHub, and the README says what it does and how to run it."
RECAP_DONE_WHEN = "Recap questions answered from memory and confidence rated."


class Answers(BaseModel):
    goal: str = "custom"
    experience: Literal["new", "some", "experienced"] = "some"
    depth: Literal["essentials", "deep"] = "deep"
    hours_per_week: float = Field(8, ge=1, le=60)
    # Topic keys; empty means "the goal's suggested topics".
    topics: List[str] = []

    @field_validator("goal")
    @classmethod
    def known_goal(cls, v: str) -> str:
        if v not in GOALS:
            raise ValueError("Unknown goal.")
        return v

    @field_validator("topics")
    @classmethod
    def known_topics(cls, v: List[str]) -> List[str]:
        unknown = [t for t in v if t not in TOPICS]
        if unknown:
            raise ValueError(f"Unknown topics: {', '.join(unknown)}")
        return list(dict.fromkeys(v))


def options() -> Dict:
    """Everything the builder form needs to render."""
    return {
        "goals": [{"key": k, "label": g["label"], "topics": g["topics"]} for k, g in GOALS.items()],
        "experience": [{"key": k, "label": e["label"]} for k, e in EXPERIENCE.items()],
        "depth": [{"key": k, "label": d["label"]} for k, d in DEPTH.items()],
        "topics": [{"key": k, "name": t["name"], "goal": t["goal"], "units": len(t["units"])} for k, t in TOPICS.items()],
    }


def _weights(answers: Answers) -> Dict[str, int]:
    suggested = GOALS[answers.goal]["topics"]
    chosen = answers.topics or list(suggested)
    # Keep the library's order within the same weight so plans read naturally.
    order = {k: i for i, k in enumerate(TOPICS)}
    picked = sorted(chosen, key=lambda k: (-suggested.get(k, 1), order[k]))
    return {k: suggested.get(k, 1) for k in picked}


def _split_hours(total: float, weights: Dict[str, int]) -> Dict[str, float]:
    """Hours per topic in proportion to weight, in half hours, at least half an hour each."""
    if not weights:
        return {}
    weight_sum = sum(weights.values())
    hours = {k: max(0.5, round(total * w / weight_sum * 2) / 2) for k, w in weights.items()}
    # Rounding can drift; give or take half hours from the biggest topics until the total matches.
    diff = round((total - sum(hours.values())) * 2) / 2
    for k in sorted(hours, key=lambda k: -hours[k]):
        if abs(diff) < 0.25:
            break
        step = 0.5 if diff > 0 else -0.5
        if hours[k] + step >= 0.5:
            hours[k] += step
            diff -= step
    return hours


def generate(answers: Answers) -> Dict:
    """A plan in template format, plus nothing else: progress always starts empty."""
    exp, depth = EXPERIENCE[answers.experience], DEPTH[answers.depth]
    weights = _weights(answers)
    picked_units = {key: [u for u in TOPICS[key]["units"] if exp["min_level"] <= u["level"] <= depth["max_level"]]
                    for key in weights}
    picked_units = {k: v for k, v in picked_units.items() if v}
    hours = _split_hours(answers.hours_per_week, {k: weights[k] for k in picked_units})
    included = {u["key"] for units in picked_units.values() for u in units}

    tracks, projects = [], []
    for key, units in picked_units.items():
        t = TOPICS[key]
        out_units = []
        for u in units:
            steps = [{"kind": s["kind"], "title": s["title"], "tasks": s["tasks"], "prompts": [],
                      "done_when": s["done_when"], "resources": s["resources"],
                      "est_minutes": max(15, int(round(s["minutes"] * exp["time_factor"] / 15)) * 15)}
                     for s in u["steps"]]
            if u["build"]:
                b = u["build"]
                steps.append({"kind": "build", "title": f"Build: {b['title']}", "tasks": b["features"], "prompts": [],
                              "done_when": BUILD_DONE_WHEN, "est_minutes": int(b["est_hours"] * 60), "resources": []})
                projects.append({"key": b["key"], "title": b["title"], "difficulty": b["difficulty"],
                                 "est_hours": b["est_hours"], "skills": u["skills"], "description": b["description"],
                                 "features": b["features"], "stretch": b["stretch"], "unit": u["key"]})
            steps.append({"kind": "recap", "title": f"Recap: {u['title']}", "tasks": RECAP_TASKS, "prompts": u["recap"],
                          "done_when": RECAP_DONE_WHEN, "est_minutes": 60, "resources": []})
            out_units.append({"key": u["key"], "title": u["title"], "why": u["why"], "outcome": u["outcome"],
                              "skills": u["skills"], "resources": [], "steps": steps,
                              "requires": u["requires"] if u["requires"] in included else None,
                              "project": u["build"]["key"] if u["build"] else None})
        tracks.append({"key": key, "name": t["name"], "goal": t["goal"], "weekly_target_hours": hours[key],
                       "color": t["color"], "units": out_units})
    return {"tracks": tracks, "projects": projects, "skill_levels": {}}


def summary(plan: Dict) -> Dict:
    """What the preview shows: per track hours, units and roughly how many weeks it takes."""
    rows = []
    for t in plan["tracks"]:
        minutes = sum(s["est_minutes"] for u in t["units"] for s in u["steps"])
        rows.append({"key": t["key"], "name": t["name"], "color": t["color"], "hours_per_week": t["weekly_target_hours"],
                     "units": len(t["units"]), "steps": sum(len(u["steps"]) for u in t["units"]),
                     "total_hours": round(minutes / 60, 1),
                     "weeks": round(minutes / 60 / t["weekly_target_hours"]) if t["weekly_target_hours"] else None,
                     "unit_titles": [u["title"] for u in t["units"]]})
    return {"tracks": rows, "projects": len(plan["projects"]),
            "weeks": max((r["weeks"] or 0 for r in rows), default=0)}
