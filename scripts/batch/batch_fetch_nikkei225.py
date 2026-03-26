"""バッチスクリプト: 日経225（^N225）日足データを yfinance から取得して DB 保存します.

使い方:
    # 全データ取得（デフォルト）
    python -m scripts.batch.batch_fetch_nikkei225

    # 過去30日分のみ
    python -m scripts.batch.batch_fetch_nikkei225 --max-period 30
"""

from __future__ import annotations

import argparse
import logging
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _run(
    client: TestClient,
    max_period: Optional[int] = None,
) -> Dict[str, Any]:
    """日経225取得バッチ API を呼び出し、結果を返します。

    Args:
        client: FastAPI TestClient インスタンス
        max_period: 取得する最大日数（None = 全データ）

    Returns:
        API レスポンスの JSON（success, records_fetched, records_saved, errors, elapsed_time を含む）

    Raises:
        Exception: API エラーまたは予期しないエラー
    """
    logger.info(
        "Starting Nikkei225 fetch: max_period=%s",
        max_period if max_period is not None else "all",
    )

    payload: Dict[str, Any] = {}
    if max_period is not None:
        payload["max_period"] = max_period

    try:
        response = client.post("/api/v1/nikkei225/fetch", json=payload)
        response.raise_for_status()

        result = response.json()
        logger.info(
            "Nikkei225 fetch API returned: success=%s, fetched=%d, saved=%d, elapsed=%.2fs",
            result.get("success", False),
            result.get("records_fetched", 0),
            result.get("records_saved", 0),
            result.get("elapsed_time", 0.0),
        )

        return result

    except Exception as e:
        logger.error("Nikkei225 fetch API failed: %s", e, exc_info=True)
        raise


def _log_results(result: Dict[str, Any]) -> None:
    """日経225取得バッチ結果をログ出力します。

    Args:
        result: API レスポンスオブジェクト
    """
    success = result.get("success", False)
    fetched = result.get("records_fetched", 0)
    saved = result.get("records_saved", 0)
    elapsed = result.get("elapsed_time", 0.0)
    errors = result.get("errors", [])

    logger.info("=" * 80)
    logger.info("NIKKEI225 FETCH RESULT")
    logger.info("=" * 80)
    logger.info("Success: %s", success)
    logger.info("Records Fetched: %d", fetched)
    logger.info("Records Saved: %d", saved)
    logger.info("Elapsed Time: %.2f seconds", elapsed)

    if errors:
        logger.warning("Errors: %d items", len(errors))
        for i, err in enumerate(errors[:5], 1):
            logger.warning("  %d. %s", i, err)
        if len(errors) > 5:
            logger.warning("  ... and %d more errors", len(errors) - 5)

    logger.info("=" * 80)


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数を解析する."""
    p = argparse.ArgumentParser(
        description="Fetch Nikkei225 daily data from yfinance and save to DB"
    )
    p.add_argument(
        "--max-period",
        type=int,
        default=None,
        dest="max_period",
        help="取得する最大日数（省略時は全利用可能データを取得）",
    )
    return p.parse_args()


def main() -> None:
    """エントリポイント."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting Nikkei225 batch fetch script")

    try:
        args = _parse_args()

        with TestClient(app) as client:
            result = _run(client=client, max_period=args.max_period)
            _log_results(result)

        if not result.get("success", False):
            logger.error("Nikkei225 fetch reported failure")
            raise SystemExit(1)

        logger.info("Nikkei225 batch fetch completed successfully")

    except SystemExit:
        raise
    except Exception as e:
        logger.exception("Nikkei225 batch fetch failed: %s", e)
        raise SystemExit(1) from e

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
