"""バッチスクリプト: 指定日付のレラティブストレングスを全銘柄分計算してDB保存します.

使い方:
    # 昨日のデータを計算（デフォルト）
    python -m scripts.batch.batch_run_relative_strength

    # 特定日付を指定
    python -m scripts.batch.batch_run_relative_strength --target-date 2026-03-20
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _run(
    client: TestClient,
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """RS計算バッチ API を呼び出し、結果を返します."""
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info("Starting RS batch calculation: target_date=%s", target_date)

    payload = {"target_date": target_date}

    try:
        response = client.post("/api/v1/relative-strength/calculate/date", json=payload)
        response.raise_for_status()

        result = response.json()
        logger.info(
            "RS batch API returned: status=%s, rowcount=%d, skipped=%d, errors=%d",
            result.get("status", ""),
            result.get("rowcount", 0),
            result.get("skipped_count", 0),
            result.get("error_count", 0),
        )
        return result

    except Exception as e:
        logger.error("RS batch API failed: %s", e, exc_info=True)
        raise


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Calculate relative strength for all symbols on a specified date",
    )
    p.add_argument(
        "--target-date",
        type=str,
        default=None,
        help="計算対象日 (YYYY-MM-DD)。デフォルトは昨日。",
    )
    return p.parse_args()


def main() -> int:
    """バッチスクリプトのエントリポイント."""
    args = _parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")

    try:
        with TestClient(app) as client:
            result = _run(client, target_date=args.target_date)

        status = result.get("status", "")
        logger.info("RS batch completed: status=%s", status)

        if status == "partial_error":
            return 1
        return 0

    except Exception as e:
        logger.error("RS batch failed: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
