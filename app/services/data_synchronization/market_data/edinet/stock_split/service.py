"""Service: CSV から `stock_split` を読み込みリポジトリへ格納する処理.

配置: app/services/data_synchronization/market_data/edinet/stock_split/service.py
"""

from __future__ import annotations

import csv
import logging
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.edinet.stock_split_repository import StockSplitRepository

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date:
    # ISO YYYY-MM-DD を想定
    return date.fromisoformat(value)


async def import_stock_splits_from_csv(
    file_path: str, session: AsyncSession, *, delimiter: str = ","
) -> int:
    """CSV を読み込んで `stock_split` を upsert する.

    CSV はヘッダ行を含み、少なくとも以下カラムを持つこと:
      - code, effective_date, ratio_from, ratio_to

    Returns:
        int: 成功して upsert した行数
    """
    repo = StockSplitRepository(session)
    count = 0

    with open(file_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for idx, row in enumerate(reader, start=1):
            try:
                code = row.get("code")
                eff = row.get("effective_date")
                if not code or not eff:
                    logger.warning("Skipping row %s: missing required fields", idx)
                    continue

                payload: dict[str, Any] = {
                    "code": code.strip(),
                    "effective_date": _parse_date(eff.strip()),
                }

                # optional ratios
                rf = row.get("ratio_from")
                rt = row.get("ratio_to")
                if rf is not None and rf != "":
                    payload["ratio_from"] = int(rf)
                if rt is not None and rt != "":
                    payload["ratio_to"] = int(rt)

                await repo.upsert(payload)
                count += 1
            except Exception as exc:  # pragma: no cover - robustness
                logger.exception("Failed to process CSV row %s: %s", idx, exc)
                continue

        # Ensure changes are committed to the database
        try:
            await session.commit()
        except Exception:
            # best-effort: log and re-raise
            logger.exception("Failed to commit imported stock splits")
            raise

    return count


__all__ = ["import_stock_splits_from_csv"]
