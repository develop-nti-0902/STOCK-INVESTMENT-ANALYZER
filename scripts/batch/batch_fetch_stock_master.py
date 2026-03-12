"""バッチスクリプト: 銘柄マスタを API 経由で取得して DB 保存します。

用途:
  - 日次バッチで銘柄マスタを最新化するために `/api/v1/stock-master/fetch` を呼び出します。
  - テスト用途に `/api/v1/stock-master/fetch/sample` を呼び出すオプションも提供します。

使い方:
  # フル取得
  python -m scripts.batch.batch_fetch_stock_master

  # サンプル取得（先頭 N 件）
  python -m scripts.batch.batch_fetch_stock_master --sample --sample-size 100 --batch-size 500
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
    client: TestClient, sample: bool = False, sample_size: int = 100, batch_size: int | None = None
) -> Dict[str, Any]:
    """API を呼び出して銘柄マスタを更新する。

    Args:
        client: TestClient
        sample: True の場合は `/fetch/sample` を呼ぶ
        sample_size: sample 用のサイズ
        batch_size: 任意のクエリパラメータ（未指定可）

    Returns:
        API レスポンスの JSON
    """
    if sample:
        url = "/api/v1/stock-master/fetch/sample"
        params: dict[str, Any] = {"sample_size": sample_size}
        if batch_size is not None:
            params["batch_size"] = batch_size
        logger.info("Calling %s with params=%s", url, params)
        resp = client.post(url, params=params)
    else:
        url = "/api/v1/stock-master/fetch"
        params = {}
        if batch_size is not None:
            params["batch_size"] = batch_size
        logger.info("Calling %s with params=%s", url, params)
        resp = client.post(url, params=params)

    try:
        resp.raise_for_status()
        result = resp.json()
        logger.info("Stock master fetch completed: %s", result)
        return result
    except Exception as e:
        logger.exception("Stock master fetch failed: %s", e)
        raise


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch stock master via internal API")
    p.add_argument(
        "--sample", action="store_true", help="Fetch sample subset instead of full fetch"
    )
    p.add_argument(
        "--sample-size", type=int, default=100, help="Sample size for sample fetch (default 100)"
    )
    p.add_argument("--batch-size", type=int, default=None, help="Optional batch_size query param")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info("Starting stock master fetch batch script")

    try:
        args = _parse_args()
        with TestClient(app) as client:
            result = _run(
                client=client,
                sample=args.sample,
                sample_size=args.sample_size,
                batch_size=args.batch_size,
            )
            logger.info("Result: %s", result)
        logger.info("Stock master fetch batch finished successfully")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        raise SystemExit(130)
    except Exception as e:
        logger.exception("Stock master fetch batch failed: %s", e)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
