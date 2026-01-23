"""古い `batch_execution_details` を削除するユーティリティスクリプト。

使い方:
    - ドライラン: `python scripts/maintenance/cleanup_batch_history.py --dry-run`
    - 実行:     `python scripts/maintenance/cleanup_batch_history.py`

環境変数:
    - `BATCH_HISTORY_RETENTION_DAYS` : 保持日数（未設定は365日）

非同期の DB セッションで削除処理を行います。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select

from app.models.batch_execution_details import BatchExecutionDetails
from app.utils.database import get_session_maker

logger = logging.getLogger("cleanup_batch_history")
logging.basicConfig(level=logging.INFO)


def _get_retention_days(cli_days: Optional[int]) -> int:
    if cli_days is not None:
        return cli_days
    env_val = os.getenv("BATCH_HISTORY_RETENTION_DAYS")
    try:
        return int(env_val) if env_val is not None else 365
    except Exception:
        logger.warning(
            "Invalid BATCH_HISTORY_RETENTION_DAYS=%s, fallback to 365", env_val
        )
        return 365


async def _collect_candidates(
    session_maker, cutoff: datetime
) -> list[BatchExecutionDetails]:
    async with session_maker() as session:
        result = await session.execute(
            select(BatchExecutionDetails).where(
                BatchExecutionDetails.created_at < cutoff
            )
        )
        return list(result.scalars().all())


async def _delete_older_than(session_maker, cutoff: datetime) -> int:
    async with session_maker() as session:
        stmt = delete(BatchExecutionDetails).where(
            BatchExecutionDetails.created_at < cutoff
        )
        result = await session.execute(stmt)
        # SQLAlchemy Core の execute が返す rowcount は場合により None になり得る
        try:
            deleted = result.rowcount or 0
        except Exception:
            deleted = 0
        await session.commit()
        return deleted


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="古い batch_execution_details レコードを削除します"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="削除せず報告のみ行う"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="保持日数を上書き（未指定は環境変数か365日）",
    )
    args = parser.parse_args(argv)

    retention_days = _get_retention_days(args.days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    session_maker = get_session_maker()

    logger.info(
        "Retention days=%s, cutoff=%s", retention_days, cutoff.isoformat()
    )

    candidates = await _collect_candidates(session_maker, cutoff)
    logger.info("Found %d candidate(s) older than cutoff", len(candidates))

    if args.dry_run:
        for c in candidates[:20]:
            logger.info(
                "Candidate id=%s created_at=%s batch_execution_id=%s",
                c.id,
                c.created_at,
                c.batch_execution_id,
            )
        if len(candidates) > 20:
            logger.info("...and %d more", len(candidates) - 20)
        logger.info("Dry-run complete: no records were deleted")
        return 0

    deleted = await _delete_older_than(session_maker, cutoff)
    logger.info("Deleted %d records from batch_execution_details", deleted)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
