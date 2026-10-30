"""Background check: refresh market data when the latest snapshot is older than MARKET_MAX_AGE_DAYS.

Runs inside the API process. The advisory lock in refresh.py keeps it to one run at a time
even if several server processes start this loop.
"""

import asyncio
import logging
from datetime import date
from typing import Optional

from sqlalchemy import func, select

import settings
from database import SessionLocal
from market.refresh import refresh
from models import MarketSnapshot

log = logging.getLogger("market")

CHECK_EVERY_SECONDS = 6 * 3600
FIRST_CHECK_AFTER_SECONDS = 60


def is_stale() -> bool:
    with SessionLocal() as session:
        latest = session.scalar(select(func.max(MarketSnapshot.taken_on)))
    return latest is None or (date.today() - latest).days >= settings.MARKET_MAX_AGE_DAYS


async def _loop() -> None:
    await asyncio.sleep(FIRST_CHECK_AFTER_SECONDS)
    while True:
        try:
            if await asyncio.to_thread(is_stale):
                await asyncio.to_thread(refresh)
        except Exception:
            log.exception("market refresh failed")
        await asyncio.sleep(CHECK_EVERY_SECONDS)


def start() -> Optional[asyncio.Task]:
    if settings.MARKET_MAX_AGE_DAYS <= 0:
        return None
    return asyncio.create_task(_loop())


def stop(task: Optional[asyncio.Task]) -> None:
    if task:
        task.cancel()
