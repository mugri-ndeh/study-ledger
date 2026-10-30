"""Build a market snapshot: fetch postings, spot skills, store the percentages.

Only one refresh runs at a time across all server processes (Postgres advisory lock).
"""

import json
import logging
import statistics
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from market.matching import SKILL_PATTERNS, compile_patterns, skills_in
from market.sources import Posting, fetch_all, load_companies
from models import MarketSnapshot, Skill, SkillStat

log = logging.getLogger("market")

LOCK_KEY = 7_311_204  # any constant; identifies the refresh lock
MIN_POSTINGS = 200  # fewer tech postings than this means something broke; keep the old numbers
MIN_SALARIES = 5
SNAPSHOT_FILE = Path(__file__).parent.parent / "market_snapshot.json"

status: Dict[str, Optional[str]] = {"running": None, "last_error": None, "last_finished": None}


def upsert_skills(session: Session) -> None:
    """Make sure every built-in skill exists with its current patterns."""
    for name, patterns in SKILL_PATTERNS.items():
        skill = session.get(Skill, name)
        if skill is None:
            session.add(Skill(name=name, patterns=patterns))
        elif skill.patterns != patterns:
            skill.patterns = patterns
    session.flush()


def import_snapshot_file(session: Session, path: Path = SNAPSHOT_FILE) -> bool:
    """Load the original career-ops snapshot when there's no market data yet."""
    if session.scalar(select(MarketSnapshot.id).limit(1)) is not None:
        return False
    data = json.loads(path.read_text())
    snap = MarketSnapshot(taken_on=date.fromisoformat(data["snapshot_date"]), source="career-ops",
                          postings=data["postings"], open_postings=data["open_postings"], companies=0)
    session.add(snap)
    session.flush()
    for s in data["skills"]:
        if session.get(Skill, s["name"]) is None:
            session.add(Skill(name=s["name"], patterns=[]))
            session.flush()
        session.add(SkillStat(snapshot_id=snap.id, skill=s["name"], pct_all=s["pct_all"], pct_open=s["pct_open"],
                              n_all=s.get("n_all", 0), median_usd=s.get("median_usd")))
    session.flush()
    return True


def aggregate(postings: List[Posting], patterns: Dict[str, List[str]]) -> Dict:
    """Percent of tech postings mentioning each skill, overall and among open-to-anywhere remote ones."""
    tech = [p for p in postings if p.is_tech]
    open_ = [p for p in tech if p.is_open]
    compiled = compile_patterns(patterns)
    found = [skills_in(f"{p.title} {p.text}", compiled) for p in tech]
    stats = []
    for name in compiled:
        hits = [p for p, skills in zip(tech, found) if name in skills]
        open_hits = sum(1 for p in hits if p.is_open)
        pay = [(p.salary_min + p.salary_max) / 2 for p in hits if p.salary_min]
        stats.append({
            "skill": name, "n_all": len(hits),
            "pct_all": round(100 * len(hits) / len(tech), 1) if tech else 0.0,
            "pct_open": round(100 * open_hits / len(open_), 1) if open_ else 0.0,
            "median_usd": int(round(statistics.median(pay), -3)) if len(pay) >= MIN_SALARIES else None,
        })
    return {"postings": len(tech), "open_postings": len(open_),
            "companies": len({p.company for p in tech}), "skills": stats}


def save_snapshot(session: Session, result: Dict, source: str = "boards") -> MarketSnapshot:
    snap = MarketSnapshot(taken_on=date.today(), source=source, postings=result["postings"],
                          open_postings=result["open_postings"], companies=result["companies"])
    session.add(snap)
    session.flush()
    for s in result["skills"]:
        session.add(SkillStat(snapshot_id=snap.id, **s))
    session.flush()
    return snap


def refresh(fetch=fetch_all) -> Optional[int]:
    """Run one refresh. Returns the new snapshot id, or None if another refresh holds the lock."""
    with engine.connect() as lock_conn:
        if not lock_conn.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY}):
            return None
        status["running"] = datetime.now(timezone.utc).isoformat()
        try:
            with SessionLocal() as session:
                patterns = {s.name: s.patterns for s in session.scalars(select(Skill)) if s.patterns}
            postings, errors = fetch(load_companies())
            for e in errors:
                log.warning("market board failed: %s", e)
            result = aggregate(postings, patterns)
            if result["postings"] < MIN_POSTINGS:
                raise RuntimeError(f"Only {result['postings']} tech postings fetched; keeping the previous snapshot.")
            with SessionLocal.begin() as session:
                snap_id = save_snapshot(session, result).id
            status["last_error"] = None
            log.info("market snapshot %s: %s postings, %s open", snap_id, result["postings"], result["open_postings"])
            return snap_id
        except Exception as e:
            status["last_error"] = str(e)
            raise
        finally:
            status["running"] = None
            status["last_finished"] = datetime.now(timezone.utc).isoformat()
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})
            lock_conn.commit()
