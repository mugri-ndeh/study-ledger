from datetime import date


def plan(c):
    return c.get("/api/plan").json()


def unit_steps(c, unit_id):
    return next(u for u in plan(c)["units"] if u["id"] == unit_id)["steps"]


def test_track_unit_step_crud(client):
    t = client.post("/api/tracks", json={"name": "Go backend", "weekly_target_hours": 2, "color": "#123456"}).json()
    assert t["key"] == "go-backend" and t["position"] == len(plan(client)["tracks"]) - 1
    u = client.post("/api/units", json={"track_id": t["id"], "title": "Go basics"}).json()
    steps = unit_steps(client, u["id"])
    assert [s["kind"] for s in steps] == ["recap"]

    a = client.post("/api/steps", json={"unit_id": u["id"], "title": "Tour of Go", "est_minutes": 90}).json()
    b = client.post("/api/steps", json={"unit_id": u["id"], "title": "Exercises", "kind": "practice"}).json()
    assert [s["title"] for s in unit_steps(client, u["id"])] == ["Tour of Go", "Exercises", "Recap: Go basics"]

    client.post(f"/api/steps/{b['id']}/move", json={"direction": -1})
    assert [s["id"] for s in unit_steps(client, u["id"])][:2] == [b["id"], a["id"]]
    assert [s["seq"] for s in unit_steps(client, u["id"])] == [0, 1, 2]

    client.delete(f"/api/steps/{b['id']}")
    assert [s["seq"] for s in unit_steps(client, u["id"])] == [0, 1]

    # Progression follows the edited order.
    track = next(x for x in plan(client)["tracks"] if x["id"] == t["id"])
    assert track["current_step_id"] == a["id"]
    client.post("/api/sessions", json={"day": date.today().isoformat(), "minutes": 30, "track_id": t["id"], "finish_step": True})
    track = next(x for x in plan(client)["tracks"] if x["id"] == t["id"])
    assert unit_steps(client, u["id"])[1]["id"] == track["current_step_id"]

    assert client.patch(f"/api/steps/{a['id']}", json={"title": "Tour of Go (all)"}).json()["title"] == "Tour of Go (all)"
    assert client.patch(f"/api/tracks/{t['id']}", json={"name": None}).status_code == 422
    assert client.delete(f"/api/tracks/{t['id']}").status_code == 204
    assert all(x["id"] != t["id"] for x in plan(client)["tracks"])


def test_unit_move_requires_and_delete(client):
    p = plan(client)
    units = [u for u in p["units"] if u["track_id"] == p["tracks"][0]["id"]]
    first, second = units[0], units[1]
    client.post(f"/api/units/{second['id']}/move", json={"direction": -1})
    reordered = [u["id"] for u in plan(client)["units"] if u["track_id"] == p["tracks"][0]["id"]]
    assert reordered[:2] == [second["id"], first["id"]]

    assert client.patch(f"/api/units/{first['id']}", json={"requires_key": first["key"]}).status_code == 422
    assert client.patch(f"/api/units/{first['id']}", json={"requires_key": "nope"}).status_code == 422
    dependant = next(u for u in p["units"] if u["requires_key"])
    required = next(u for u in p["units"] if u["key"] == dependant["requires_key"])
    assert client.delete(f"/api/units/{required['id']}").status_code == 204
    after = next(u for u in plan(client)["units"] if u["id"] == dependant["id"])
    assert after["requires_key"] is None
    seqs = [u["seq"] for u in plan(client)["units"] if u["track_id"] == required["track_id"]]
    assert seqs == list(range(len(seqs)))


def test_export_import_reset(client):
    exported = client.get("/api/plan/export").json()
    n_tracks, n_units = len(plan(client)["tracks"]), len(plan(client)["units"])
    assert len(exported["tracks"]) == n_tracks
    small = {"tracks": [exported["tracks"][0]], "projects": [], "skill_levels": {"Python": 2}}
    assert client.post("/api/plan/import", json={"plan": small}).status_code == 422  # needs confirm
    assert client.post("/api/plan/import", json={"plan": small, "confirm": True}).status_code == 200
    p = plan(client)
    assert len(p["tracks"]) == 1 and len(p["units"]) == len(small["tracks"][0]["units"])
    assert next(s for s in client.get("/api/skills").json()["skills"] if s["name"] == "Python")["my_level"] == 2

    bad = {"tracks": [exported["tracks"][0], exported["tracks"][0]]}
    assert client.post("/api/plan/import", json={"plan": bad, "confirm": True}).status_code == 422

    assert client.post("/api/plan/reset", json={"template": "starter-backend-python", "confirm": True}).status_code == 200
    assert len(plan(client)["units"]) == n_units
    assert client.post("/api/plan/reset", json={"template": "blank", "confirm": True}).status_code == 200
    assert plan(client)["tracks"] == []
