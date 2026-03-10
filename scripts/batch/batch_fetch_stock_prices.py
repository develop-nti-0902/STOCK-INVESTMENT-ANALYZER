"""バッチスクリプト: 全銘柄の株価データを指定期間で取得してDB保存します.

デフォルトでは過去7日分のデータを取得します。

使い方:
    # 過去7日分のデータを取得（デフォルト）
    python -m scripts.batch.batch_fetch_stock_prices

    # 過去30日分のデータを取得
    python -m scripts.batch.batch_fetch_stock_prices --days 30

    # バッチサイズとタイムフレームを指定
    python -m scripts.batch.batch_fetch_stock_prices --days 7 --timeframe 1d
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
    days: int = 7,
    timeframe: str = "1d",
    batch_size: int = 100,
) -> Dict[str, Any]:
    """株価取得バッチ API を呼び出し、結果を返します。

    Args:
        client: FastAPI TestClient インスタンス
        days: 取得する日数（デフォルト: 7日）
        timeframe: タイムフレーム（デフォルト: 1d）
        batch_size: バッチサイズ（デフォルト: 100）

    Returns:
        API レスポンスの JSON（total, success, failed, elapsed_time を含む）

    Raises:
        Exception: API エラーまたは予期しないエラー
    """
    # periodパラメータの構築（例: "7d", "30d"）
    period = f"{days}d"

    logger.info(
        "Starting JPX batch stock price fetch: period=%s, timeframe=%s, batch_size=%d",
        period,
        timeframe,
        batch_size,
    )

    # リクエストボディの構築
    payload = {
        "timeframe": timeframe,
        "batch_size": batch_size,
        "period": period,
    }

    try:
        response = client.post("/api/v1/stock-price/batch", json=payload)
        response.raise_for_status()

        result = response.json()
        logger.info(
            "Stock price batch API returned: total=%d, success=%d, failed=%d, elapsed=%.2fs",
            result.get("total", 0),
            result.get("success", 0),
            result.get("failed", 0),
            result.get("elapsed_time", 0.0),
        )

        return result

    except Exception as e:
        logger.error("Stock price batch API failed: %s", e, exc_info=True)
        raise


def _log_stock_price_results(result: Dict[str, Any]) -> None:
    """株価取得バッチ結果をログ出力します。

    Args:
        result: API レスポンスオブジェクト
    """
    total = result.get("total", 0)
    success = result.get("success", 0)
    failed = result.get("failed", 0)
    elapsed = result.get("elapsed_time", 0.0)
    errors = result.get("errors", [])

    logger.info("=" * 80)
    logger.info("STOCK PRICE BATCH RESULT")
    logger.info("=" * 80)
    logger.info("Total: %d", total)
    logger.info("Success: %d", success)
    logger.info("Failed: %d", failed)
    logger.info("Elapsed Time: %.2f seconds", elapsed)

    if errors:
        logger.warning("Errors: %d items", len(errors))
        for i, err in enumerate(errors[:5], 1):  # 最初の5件を表示
            logger.warning("  %d. %s", i, err)
        if len(errors) > 5:
            logger.warning("  ... and %d more errors", len(errors) - 5)

    logger.info("=" * 80)


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースします."""
    p = argparse.ArgumentParser(
        description="Fetch stock prices for all JPX symbols for a specified period",
        epilog=(
            "Examples:\n"
            "  python -m scripts.batch.batch_fetch_stock_prices\n"
            "  python -m scripts.batch.batch_fetch_stock_prices --days 30\n"
            "  python -m scripts.batch.batch_fetch_stock_prices --days 7 --timeframe 1d"
        ),
    )
    p.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to fetch (default: 7)",
    )
    p.add_argument(
        "--timeframe",
        type=str,
        default="1d",
        choices=["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
        help="Timeframe to fetch (default: 1d)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for processing (default: 100)",
    )
    return p.parse_args()


def main() -> None:
    """エントリポイント。全体の実行制御を行います。

    Raises:
        SystemExit: CLI 引数パースエラーまたは予期しないエラー
    """
    # ロギング初期化
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting stock price batch fetch script")

    try:
        # Step 1: CLI 引数パース
        args = _parse_args()
        logger.info("CLI args parsed successfully")

        # Step 2-3: TestClient コンテキストで実行
        with TestClient(app) as client:
            # Step 2: 株価バッチ実行
            result = _run(
                client=client,
                days=args.days,
                timeframe=args.timeframe,
                batch_size=args.batch_size,
            )

            # Step 3: 結果ログ出力
            _log_stock_price_results(result)

        logger.info("Stock price batch fetch completed successfully")

    except Exception as e:
        logger.exception("Stock price batch fetch failed: %s", e)
        raise SystemExit(1) from e

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
