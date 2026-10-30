from sqlalchemy import func, select

from database import SessionLocal
from market import refresh as market_refresh
from market.matching import SKILL_PATTERNS, compile_patterns, plain_text, skills_in
from market.sources import Posting, parse_salary
from models import MarketSnapshot, User

C = compile_patterns(SKILL_PATTERNS)


def found(text):
    return skills_in(text, C)


def test_tricky_skill_names():
    assert "SQL" not in found("Experience with NoSQL stores")
    assert "SQL" in found("Strong SQL and PostgreSQL")
    assert "Go" in found("Languages: Python, Go, Rust")
    assert "Go" not in found("We go to market fast. Go-to-market experience")
    assert "Go" in found("services written in Golang")
    assert "Java" not in found("JavaScript and TypeScript")
    assert {"React Native"} <= found("React Native apps") and "React" not in found("React Native apps")
    assert "C#/.NET" in found("C# and ASP.NET Core") and "C#/.NET" not in found("visit example.net")
    assert "C++" in found("modern C++17")
    assert "RAG / vector DB" in found("retrieval-augmented generation with pgvector")


def test_plain_text_and_salary():
    assert plain_text("&lt;p&gt;Python &amp;amp; Go&lt;/p&gt;") == "Python & Go"
    assert parse_salary("The base range is $150,000 - $210,000 per year") == (150_000, 210_000)
    assert parse_salary("$220K – $300K • Offers Equity") == (220_000, 300_000)
    assert parse_salary("CA$150,000 - CA$200,000") == (None, None)
    assert parse_salary("raised $5 - $10 million") == (None, None)


def posting(title="Software Engineer", text="Python and AWS", location="Remote", remote=True, pay=None):
    low, high = pay or (None, None)
    return Posting("Acme", title, location, remote, text, low, high)


def test_aggregate():
    postings = [posting(pay=(100_000, 200_000)) for _ in range(5)]
    postings += [posting(location="New York", remote=False, text="Python only") for _ in range(5)]
    postings.append(posting(title="Account Executive", text="Python"))  # not a tech role
    result = market_refresh.aggregate(postings, SKILL_PATTERNS)
    stats = {s["skill"]: s for s in result["skills"]}
    assert result["postings"] == 10 and result["open_postings"] == 5
    assert stats["Python"]["pct_all"] == 100.0 and stats["AWS"]["pct_all"] == 50.0
    assert stats["AWS"]["pct_open"] == 100.0
    assert stats["AWS"]["median_usd"] == 150_000 and stats["Python"]["median_usd"] == 150_000
    assert stats["Rust"]["median_usd"] is None


def fake_fetch(n):
    def fetch(companies):
        return [posting(text="Python, Go, Kubernetes") for _ in range(n)], ["Broken Co: 404"]
    return fetch


def test_refresh_stores_snapshot_and_deltas(client):
    snap1 = market_refresh.refresh(fetch=fake_fetch(300))
    assert snap1 is not None
    skills = client.get("/api/skills").json()
    assert skills["source"] == "boards" and skills["postings"] == 300
    go = next(s for s in skills["skills"] if s["name"] == "Go")
    assert go["pct_all"] == 100.0 and go["delta_all"] is None  # career-ops numbers aren't compared

    market_refresh.refresh(fetch=lambda c: ([posting(text="Python") for _ in range(250)]
                                            + [posting(text="Python, Go") for _ in range(250)], []))
    go = next(s for s in client.get("/api/skills").json()["skills"] if s["name"] == "Go")
    assert go["pct_all"] == 50.0 and go["delta_all"] == -50.0
    history = client.get("/api/market/history", params={"skill": "Go"}).json()
    assert [h["source"] for h in history] == ["career-ops", "boards", "boards"]


def test_refresh_keeps_old_data_when_fetch_fails():
    with SessionLocal() as s:
        before = s.scalar(select(func.count(MarketSnapshot.id)))
    try:
        market_refresh.refresh(fetch=fake_fetch(3))
    except RuntimeError as e:
        assert "Only 3" in str(e)
    with SessionLocal() as s:
        assert s.scalar(select(func.count(MarketSnapshot.id))) == before
    assert market_refresh.status["last_error"]


def test_refresh_endpoint_is_admin_only(client, monkeypatch):
    assert client.post("/api/market/refresh").status_code == 403
    with SessionLocal.begin() as s:
        s.execute(User.__table__.update().values(is_admin=True))
    monkeypatch.setattr("market.api._run_refresh", lambda: None)
    assert client.post("/api/market/refresh").status_code == 202
    assert client.get("/api/market/status").json()["can_refresh"] is True


def test_skill_level(client):
    assert client.patch("/api/skills/Python", json={"my_level": 3}).status_code == 200
    assert next(s for s in client.get("/api/skills").json()["skills"] if s["name"] == "Python")["my_level"] == 3
    assert client.patch("/api/skills/Nope", json={"my_level": 1}).status_code == 404
