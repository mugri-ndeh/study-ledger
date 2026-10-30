"""Fetch postings from public job-board APIs (Greenhouse, Lever, Ashby) and normalise them."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import httpx

from market.matching import plain_text

COMPANIES_FILE = Path(__file__).parent / "companies.json"

# Engineering and data roles only; the skill numbers are about technical jobs.
TECH_TITLE = re.compile(
    r"engineer|developer|programmer|scientist|\bsre\b|devops|architect|machine learning|\bml\b|\bai\b|"
    r"data|technical staff|research(?:er)?|software|platform|infrastructure|security|analyst", re.IGNORECASE)
NON_TECH_TITLE = re.compile(r"sales|account (?:executive|manager)|recruit|marketing|legal|counsel|finance|"
                            r"people partner|customer success|business development", re.IGNORECASE)

# "$150,000 - $200,000", "$150K – $200K", "US$150k to $200k". Other currencies (CA$, A$, €) are skipped.
SALARY = re.compile(
    r"(?<![A-Za-z])(?:US)?\$\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])\s*(?:-|–|—|to)\s*(?:US)?\$?\s?(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d)?\s?[kK])")
OPEN_LOCATION = re.compile(r"anywhere|worldwide|global|\bemea\b|africa|\bremote\s*$", re.IGNORECASE)


@dataclass
class Posting:
    company: str
    title: str
    location: str
    remote: bool
    text: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    @property
    def is_open(self) -> bool:
        """Remote with no country restriction, i.e. open to someone outside the US/EU."""
        return self.remote and bool(OPEN_LOCATION.search(self.location.strip()))

    @property
    def is_tech(self) -> bool:
        return bool(TECH_TITLE.search(self.title)) and not NON_TECH_TITLE.search(self.title)


def _amount(raw: str) -> int:
    raw = raw.replace(",", "").replace(" ", "").lower()
    return int(float(raw[:-1]) * 1000) if raw.endswith("k") else int(raw)


def parse_salary(text: str) -> Tuple[Optional[int], Optional[int]]:
    """The first plausible yearly USD range in the text."""
    for m in SALARY.finditer(text or ""):
        low, high = _amount(m.group(1)), _amount(m.group(2))
        if 30_000 <= low <= high <= 1_500_000:
            return low, high
    return None, None


def _remote(location: str) -> bool:
    return "remote" in location.lower()


def greenhouse(client: httpx.Client, board: str, company: str) -> List[Posting]:
    r = client.get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", params={"content": "true"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        location = (j.get("location") or {}).get("name") or ""
        text = plain_text(j.get("content", ""))
        low, high = parse_salary(text)
        out.append(Posting(company, j.get("title", ""), location, _remote(location), text, low, high))
    return out


def lever(client: httpx.Client, site: str, company: str) -> List[Posting]:
    r = client.get(f"https://api.lever.co/v0/postings/{site}", params={"mode": "json"})
    r.raise_for_status()
    out = []
    for j in r.json():
        cats = j.get("categories") or {}
        location = cats.get("location") or ""
        lists = " ".join(plain_text(x.get("content", "")) for x in j.get("lists") or [])
        text = " ".join([j.get("descriptionPlain") or "", lists, j.get("additionalPlain") or ""])
        low, high = None, None
        rng = j.get("salaryRange") or {}
        if rng.get("currency") == "USD" and rng.get("interval") in ("per-year-salary", None) and rng.get("min"):
            low, high = int(rng["min"]), int(rng.get("max") or rng["min"])
        else:
            low, high = parse_salary(text)
        remote = j.get("workplaceType") == "remote" or _remote(location)
        out.append(Posting(company, j.get("text", ""), location, remote, text, low, high))
    return out


def ashby(client: httpx.Client, board: str, company: str) -> List[Posting]:
    r = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{board}", params={"includeCompensation": "true"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        if j.get("isListed") is False:
            continue
        location = j.get("location") or ""
        text = j.get("descriptionPlain") or plain_text(j.get("descriptionHtml", ""))
        comp = j.get("compensation") or {}
        low, high = parse_salary(comp.get("scrapeableCompensationSalarySummary") or "")
        if low is None:
            low, high = parse_salary(text)
        remote = bool(j.get("isRemote")) or _remote(location)
        out.append(Posting(company, j.get("title", ""), location, remote, text, low, high))
    return out


PROVIDERS: Dict[str, Callable[[httpx.Client, str, str], List[Posting]]] = {
    "greenhouse": greenhouse, "lever": lever, "ashby": ashby,
}


def load_companies() -> List[Dict[str, str]]:
    return json.loads(COMPANIES_FILE.read_text())


def fetch_all(companies: List[Dict[str, str]], client: Optional[httpx.Client] = None) -> Tuple[List[Posting], List[str]]:
    """All postings from every board. The same role listed in several cities counts once (the
    remote-open listing wins). Boards that fail are reported, not fatal."""
    own_client = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": "StudyLedger/1.0 (market snapshot)"})
    unique: Dict[Tuple[str, str], Posting] = {}
    errors = []
    try:
        for c in companies:
            try:
                batch = PROVIDERS[c["provider"]](client, c["board"], c["name"])
            except (httpx.HTTPError, ValueError, KeyError) as e:
                errors.append(f"{c['name']}: {e}")
                continue
            for p in batch:
                key = (p.company, " ".join(p.title.lower().split()))
                if key not in unique or (p.is_open and not unique[key].is_open):
                    unique[key] = p
    finally:
        if own_client:
            client.close()
    return list(unique.values()), errors
