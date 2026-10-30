from sqlalchemy import update

import builder
from conftest import make_client, signup
from database import SessionLocal
from models import User
from templates import TemplateT

OWNER_PLAN = "python-ai-ml"


def gen(**answers):
    return builder.generate(builder.Answers(**answers))


def unit_keys(p):
    return {u["key"] for t in p["tracks"] for u in t["units"]}


def test_every_combination_is_a_valid_plan():
    for goal in builder.GOALS:
        for exp in builder.EXPERIENCE:
            for depth in builder.DEPTH:
                p = gen(goal=goal, experience=exp, depth=depth, hours_per_week=9)
                TemplateT.model_validate(p)
                if p["tracks"]:
                    assert sum(t["weekly_target_hours"] for t in p["tracks"]) == 9


def test_levels_follow_experience_and_depth():
    new_deep = gen(goal="backend-python", experience="new", depth="deep")
    pro_short = gen(goal="backend-python", experience="experienced", depth="essentials")
    assert "py-start" in unit_keys(new_deep) and "py-advanced" in unit_keys(new_deep)
    assert "py-start" not in unit_keys(pro_short) and "py-advanced" not in unit_keys(pro_short)
    first = lambda p: p["tracks"][0]["units"][0]["steps"][0]["est_minutes"]  # noqa: E731
    # System design starts at level 2, so both plans have the same first step; beginners get more time.
    sd = dict(goal="custom", topics=["system-design"])
    assert first(gen(experience="new", **sd)) > first(gen(experience="experienced", **sd))


def test_topics_weights_and_requires():
    p = gen(goal="ai", hours_per_week=10)
    hours = {t["key"]: t["weekly_target_hours"] for t in p["tracks"]}
    assert list(hours)[:2] == ["python", "ai-eng"] and hours["python"] > hours["databases"]
    # Requirements are kept only when the required unit is in the plan.
    alone = gen(goal="custom", topics=["ai-eng"])
    assert all(u["requires"] is None for t in alone["tracks"] for u in t["units"])
    with_py = gen(goal="custom", topics=["ai-eng", "python"])
    llm = next(u for t in with_py["tracks"] for u in t["units"] if u["key"] == "ai-llm")
    assert llm["requires"] == "py-data"
    assert gen(goal="custom")["tracks"] == []


def test_preview_and_build_endpoints():
    with make_client() as c:
        opts = c.get("/api/builder/options").json()
        assert {g["key"] for g in opts["goals"]} >= {"backend-python", "frontend", "custom"}
        preview = c.post("/api/builder/preview", json={"goal": "frontend", "hours_per_week": 6}).json()
        assert preview["tracks"][0]["key"] == "javascript" and preview["weeks"] > 0
        assert c.post("/api/builder/preview", json={"goal": "nope"}).status_code == 422

        signup(c, "builder@example.com", template="blank")
        answers = {"goal": "custom", "topics": ["dsa", "databases"], "hours_per_week": 5}
        r = c.post("/api/plan/build", json={"answers": answers})
        assert r.status_code == 200
        assert [t["key"] for t in c.get("/api/plan").json()["tracks"]] == ["databases", "dsa"]
        # A plan exists now, so replacing it needs confirm.
        assert c.post("/api/plan/build", json={"answers": answers}).status_code == 422
        assert c.post("/api/plan/build", json={"answers": {"goal": "custom"}, "confirm": True}).status_code == 422


def test_owner_plan_is_private():
    with make_client() as c:
        public = {t["slug"] for t in c.get("/api/auth/templates").json()}
        assert OWNER_PLAN not in public and "starter-frontend" in public
        r = c.post("/api/auth/signup", json={"email": "x@example.com", "password": "correct horse battery",
                                             "display_name": "X", "template": OWNER_PLAN})
        assert r.status_code == 422
        signup(c, "y@example.com")
        assert c.post("/api/plan/reset", json={"template": OWNER_PLAN, "confirm": True}).status_code == 422
        with SessionLocal.begin() as s:
            s.execute(update(User).where(User.email == "y@example.com").values(is_admin=True))
        assert OWNER_PLAN in {t["slug"] for t in c.get("/api/auth/templates").json()}
        assert c.post("/api/plan/reset", json={"template": OWNER_PLAN, "confirm": True}).status_code == 200
        assert len(c.get("/api/plan").json()["units"]) == 60


def test_signup_with_uploaded_plan():
    plan = gen(goal="custom", topics=["system-design"])
    with make_client() as c:
        r = c.post("/api/auth/signup", json={"email": "up@example.com", "password": "correct horse battery",
                                             "display_name": "Up", "template": "upload", "plan": plan})
        assert r.status_code == 201
        assert [t["key"] for t in c.get("/api/plan").json()["tracks"]] == ["system-design"]
    with make_client() as c:
        bad = {"tracks": [plan["tracks"][0], plan["tracks"][0]]}
        r = c.post("/api/auth/signup", json={"email": "up2@example.com", "password": "correct horse battery",
                                             "display_name": "Up", "template": "upload", "plan": bad})
        assert r.status_code == 422
        r = c.post("/api/auth/signup", json={"email": "up3@example.com", "password": "correct horse battery",
                                             "display_name": "Up", "template": "upload"})
        assert r.status_code == 422
