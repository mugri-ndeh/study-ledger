import shutil
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import func, select

from cli import import_sqlite
from conftest import make_client
from database import SessionLocal
from models import Step, StudySession, User, UserSkill

SOURCE = Path(__file__).parent.parent / "data" / "learning.db"


@pytest.mark.skipif(not SOURCE.exists(), reason="no old learning.db to import")
def test_import_sqlite_copy(tmp_path, monkeypatch):
    db = tmp_path / "learning.db"
    shutil.copy(SOURCE, db)  # never touch the real file
    con = sqlite3.connect(db)
    first = con.execute("SELECT id, track_id, unit_id FROM steps WHERE track_id = 'python' ORDER BY seq LIMIT 2").fetchall()
    con.execute("UPDATE steps SET status='done', completed_on='2026-10-20', rating=NULL WHERE id = ?", (first[0][0],))
    con.execute("INSERT INTO sessions (day, minutes, track_id, step_id, note) VALUES ('2026-10-20', 50, 'python', ?, 'x')", (first[0][0],))
    con.execute("INSERT INTO sessions (day, minutes, track_id, step_id, note) VALUES ('2026-10-21', 25, 'python', ?, '')", (first[1][0],))
    con.execute("UPDATE skills SET my_level = 3 WHERE name = 'TypeScript'")
    con.commit()
    con.close()

    monkeypatch.setenv("LEDGER_PASSWORD", "imported-password")
    import_sqlite(db, "me@example.com", "Me", admin=True)
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.email == "me@example.com"))
        assert user.is_admin
        assert s.scalar(select(func.count(Step.id)).where(Step.user_id == user.id)) == 221
        assert s.scalar(select(func.count(Step.id)).where(Step.user_id == user.id, Step.status == "done")) == 1
        assert s.scalar(select(func.sum(StudySession.minutes)).where(StudySession.user_id == user.id)) == 75
        assert s.get(UserSkill, (user.id, "TypeScript")).my_level == 3

    with make_client() as c:
        c.post("/api/auth/login", json={"email": "me@example.com", "password": "imported-password"})
        track = next(t for t in c.get("/api/plan").json()["tracks"] if t["key"] == "python")
        assert track["steps_done"] == 1 and track["current_step_id"] is not None
        assert c.get("/api/dashboard", params={"today": "2026-10-21"}).json()["total_minutes"] == 75

    with pytest.raises(SystemExit):
        import_sqlite(db, "me@example.com", "Me", admin=False)
