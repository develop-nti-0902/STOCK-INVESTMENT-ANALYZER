"""バッチスクリプト: ローカルに格納された株価データを使って全銘柄分のRS計算を実行します。

使い方:
    # デフォルト（scripts/batch 配下のデータを想定）
    python -m scripts.batch.batch_run_relative_strength_all

    # 別ディレクトリを指定
    python -m scripts.batch.batch_run_relative_strength_all --data-dir path/to/data

注意: 既存のバッチと同様に `fastapi.testclient.TestClient` を使って内部 API を呼び出します。
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _run(client: TestClient, data_dir: Path | None = None) -> Dict[str, Any]:
    """/api/v1/relative-strength/calculate/all を呼び出す。

    Args:
        client: TestClient
        data_dir: ローカル株価データのパス（省略可）。API 側がこのパラメータを受け取る場合は body に含めて送る。
    """
    payload: Dict[str, Any] = {}
    if data_dir is not None:
        payload["data_dir"] = str(data_dir)

    logger.info("Starting RS all calculation (local data_dir=%s)", data_dir)

    try:
        response = client.post("/api/v1/relative-strength/calculate/all", json=payload)
        response.raise_for_status()

        result = response.json()
        logger.info(
            "RS all API returned: status=%s, rowcount=%d, errors=%d",
            result.get("status", ""),
            result.get("rowcount", 0),
            result.get("error_count", 0),
        )
        return result

    except Exception as e:
        logger.error("RS all API failed: %s", e, exc_info=True)
        raise


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run relative strength calculation for all symbols using local data"
    )
    p.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="ローカルに保存された株価データのディレクトリ（省略時は scripts/batch 配下を想定）",
    )
    return p.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    args = _parse_args()
    data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent

    try:
        with TestClient(app) as client:
            _run(client, data_dir=data_dir)
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
