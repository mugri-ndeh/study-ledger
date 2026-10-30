from datetime import date

from conftest import make_client, signup


def plan(c):
    return c.get("/api/plan").json()


def test_template_copy_counts(client):
    from database import SessionLocal
    from models import PlanTemplate
    from sqlalchemy import select
    with SessionLocal() as s:
        data = s.scalar(select(PlanTemplate).where(PlanTemplate.slug == "starter-backend-python")).data
    p = plan(client)
    assert len(p["tracks"]) == len(data["tracks"])
    assert len(p["units"]) == sum(len(t["units"]) for t in data["tracks"])
    assert sum(len(u["steps"]) for u in p["units"]) == sum(len(u["steps"]) for t in data["tracks"] for u in t["units"])
    assert sum(len(s["resources"]) for u in p["units"] for s in u["steps"]) == \
        sum(len(s["resources"]) for t in data["tracks"] for u in t["units"] for s in u["steps"])
    assert len(client.get("/api/projects").json()) == len(data["projects"])


def test_blank_signup_has_empty_plan():
    with make_client() as c:
        signup(c, "blank@example.com", template="blank")
        p = plan(c)
        assert p["tracks"] == [] and p["units"] == []
        assert c.get("/api/dashboard").status_code == 200
        assert c.get("/api/strengths").status_code == 200


def test_progression(client):
    track = next(t for t in plan(client)["tracks"] if t["key"] == "python")
    first = track["current_step_id"]
    today = date.today().isoformat()
    r = client.post("/api/sessions", json={"day": today, "minutes": 45, "track_id": track["id"], "finish_step": True})
    assert r.status_code == 201 and r.json()["step_id"] == first
    track = next(t for t in plan(client)["tracks"] if t["key"] == "python")
    assert track["current_step_id"] != first and track["last_done_step_id"] == first
    d = client.get("/api/dashboard", params={"today": today}).json()
    assert d["total_minutes"] == 45 and d["studied_today"]

    # Only the last finished step can be reopened, and only the current step can be completed.
    second = track["current_step_id"]
    assert client.post(f"/api/steps/{first}/reopen").status_code == 200
    assert client.post(f"/api/steps/{second}/complete", json={}).status_code == 409


def test_recap_needs_rating_and_build_ships_project(client):
    """Finish python units in order until one with a build project is done."""
    while True:
        p = plan(client)
        track = next(t for t in p["tracks"] if t["key"] == "python")
        unit = next(u for u in p["units"] if u["id"] == track["current_unit_id"])
        for step in unit["steps"]:
            body = {"rating": 4} if step["kind"] == "recap" else {}
            if step["kind"] == "recap":
                assert client.post(f"/api/steps/{step['id']}/complete", json={}).status_code == 422
            if step["kind"] == "build":
                client.post("/api/sessions", json={"day": date.today().isoformat(), "minutes": 30, "track_id": track["id"]})
                proj = next(x for x in client.get("/api/projects").json() if x["key"] == unit["project_key"])
                assert proj["status"] == "building"
            assert client.post(f"/api/steps/{step['id']}/complete", json=body).status_code == 200, step
        if unit["project_key"]:
            break
    proj = next(x for x in client.get("/api/projects").json() if x["key"] == unit["project_key"])
    assert proj["status"] == "shipped"
    s = client.get("/api/strengths").json()
    assert any(r["key"] == unit["key"] and r["rating"] == 4 for r in s["timeline"])


def test_blocked_by_requires(client):
    p = plan(client)
    a, b = p["tracks"][0], p["tracks"][1]
    needed = next(u for u in p["units"] if u["id"] == a["current_unit_id"])
    current_b = next(u for u in p["units"] if u["id"] == b["current_unit_id"])
    assert client.patch(f"/api/units/{current_b['id']}", json={"requires_key": needed["key"]}).status_code == 200
    track = next(t for t in plan(client)["tracks"] if t["id"] == b["id"])
    assert track["blocked_by"]["key"] == needed["key"]
    r = client.post("/api/sessions", json={"day": date.today().isoformat(), "minutes": 30, "track_id": track["id"]})
    assert r.status_code == 409


def test_resources_and_projects(client):
    step = plan(client)["units"][0]["steps"][0]
    res = step["resources"][0]
    r = client.patch(f"/api/resources/{res['id']}", json={"outcome": "hint"})
    assert r.json()["done"] is True and r.json()["outcome"] == "hint"
    proj = client.post("/api/projects", json={"title": "Side thing"}).json()
    assert proj["key"] == f"custom-{proj['id']}"
    assert client.patch(f"/api/projects/{proj['id']}", json={"status": "building"}).json()["status"] == "building"
    assert client.delete(f"/api/projects/{proj['id']}").status_code == 204
    plan_proj = next(x for x in client.get("/api/projects").json() if x["unit_key"])
    assert client.delete(f"/api/projects/{plan_proj['id']}").status_code == 409


def test_users_are_isolated(client):
    a_plan = plan(client)
    a_step = a_plan["units"][0]["steps"][0]
    a_track = a_plan["tracks"][0]
    client.post("/api/sessions", json={"day": date.today().isoformat(), "minutes": 20, "track_id": a_track["id"]})
    a_session = client.get("/api/sessions").json()[0]
    a_project = client.get("/api/projects").json()[0]

    with make_client() as b:
        signup(b, "bob@example.com")
        assert b.get("/api/sessions").json() == []
        assert b.post(f"/api/steps/{a_step['id']}/complete", json={}).status_code == 404
        assert b.post(f"/api/steps/{a_step['id']}/reopen").status_code == 404
        assert b.delete(f"/api/sessions/{a_session['id']}").status_code == 404
        assert b.patch(f"/api/projects/{a_project['id']}", json={"notes": "x"}).status_code == 404
        assert b.patch(f"/api/resources/{a_step['resources'][0]['id']}", json={"done": True}).status_code == 404
        assert b.post("/api/sessions", json={"day": date.today().isoformat(), "minutes": 5,
                                             "track_id": a_track["id"]}).status_code == 404
        assert b.patch(f"/api/tracks/{a_track['id']}", json={"name": "mine"}).status_code == 404
        assert b.delete(f"/api/units/{a_plan['units'][0]['id']}").status_code == 404
        assert b.post("/api/resources", json={"unit_id": a_plan["units"][0]["id"], "title": "x"}).status_code == 404
    assert len(client.get("/api/sessions").json()) == 1
