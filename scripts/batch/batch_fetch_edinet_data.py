"""バッチスクリプト: 指定期間のEDINETデータを取得してDB保存します.

対象データ:
- 貸借対照表 (Balance Sheet)
- 損益計算書 (Profit and Loss)
- 配当情報 (Stock Dividend)
- キャッシュフロー計算書 (Cash Flow Statement)

使い方:
    # 指定期間のデータを取得
    python -m scripts.batch.batch_fetch_edinet_data \
        --start-date 2024-01-01 \
        --end-date 2024-01-31

    # 最大処理件数を指定
    python -m scripts.batch.batch_fetch_edinet_data \
        --start-date 2024-01-01 \
        --end-date 2024-01-31 \
        --max-documents 10

    # 進捗表示間隔を変更
    python -m scripts.batch.batch_fetch_edinet_data \
        --start-date 2024-01-01 \
        --end-date 2024-01-31 \
        --progress-interval 5
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _validate_dates(start_date_str: str, end_date_str: str) -> tuple[date, date]:
    """日付を妥当性チェックし、date オブジェクトに変換します。

    Args:
        start_date_str: ISO 形式の開始日付文字列
        end_date_str: ISO 形式の終了日付文字列

    Returns:
        (start_date, end_date)のタプル

    Raises:
        ValueError: 無効な日付フォーマットまたは日付ロジックエラー
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        error_msg = (
            f"Invalid date format. Expected YYYY-MM-DD, got '{start_date_str}', '{end_date_str}'"
        )
        logger.error(error_msg)
        raise ValueError(error_msg) from e

    if start_date > end_date:
        error_msg = "start_date must be before or equal to end_date"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Date validation passed: start_date=%s, end_date=%s", start_date, end_date)
    return start_date, end_date


def _run(
    client: TestClient,
    start_date: date,
    end_date: date,
    progress_interval: int = 10,
    max_documents: int | None = None,
) -> Dict[str, Any]:
    """EDINET バッチ API を呼び出し、結果を返します。

    Args:
        client: FastAPI TestClient インスタンス
        start_date: 取得開始日 (date オブジェクト)
        end_date: 取得終了日 (date オブジェクト)
        progress_interval: 進捗表示間隔（ドキュメント数、デフォルト: 10）
        max_documents: 最大処理ドキュメント数（Noneの場合は全件、デフォルト: None）

    Returns:
        API レスポンスの JSON（status, summary を含む）

    Raises:
        Exception: API エラーまたは予期しないエラー
    """
    logger.info(
        "Starting EDINET batch: start_date=%s, end_date=%s, progress_interval=%d, max_documents=%s",
        start_date.isoformat(),
        end_date.isoformat(),
        progress_interval,
        max_documents,
    )

    params = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "progress_interval": progress_interval,
        "transaction_atomic": True,
    }

    if max_documents is not None:
        params["max_documents"] = max_documents

    try:
        response = client.post("/api/v1/edinet/process-date-range", params=params)
        response.raise_for_status()

        result = response.json()
        logger.info(
            "EDINET API returned status=%s, total=%s, processed=%s, saved=%s, failed=%s",
            result.get("status"),
            result.get("total_documents"),
            result.get("processed_documents"),
            result.get("saved_items"),
            result.get("failed_documents"),
        )

        return result

    except Exception as e:
        logger.error("EDINET API failed: %s", e, exc_info=True)
        raise


def _log_edinet_results(result: Dict[str, Any]) -> None:
    """EDINET バッチ結果をログ出力します。

    Args:
        result: API レスポンスオブジェクト
    """
    status = result.get("status", "unknown")
    total_documents = result.get("total_documents", 0)
    processed = result.get("processed_documents", 0)
    saved = result.get("saved_items", 0)
    failed = result.get("failed_documents", 0)

    logger.info("=" * 80)
    logger.info("EDINET BATCH RESULT")
    logger.info("=" * 80)
    logger.info("Status: %s", status)
    logger.info("Total Documents: %d", total_documents)
    logger.info("Processed: %d", processed)
    logger.info("Saved: %d", saved)
    logger.info("Failed: %d", failed)
    logger.info("=" * 80)


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースします."""
    p = argparse.ArgumentParser(
        description="Fetch EDINET data (Balance Sheet & P/L) for a specified date range",
        epilog=(
            "Examples:\n"
            "  python -m scripts.batch.batch_fetch_edinet_data --start-date 2024-01-01 --end-date 2024-01-31\n"
            "  python -m scripts.batch.batch_fetch_edinet_data --start-date 2024-01-01 --end-date 2024-01-31 --max-documents 10"
        ),
    )
    p.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format",
    )
    p.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format",
    )
    p.add_argument(
        "--progress-interval",
        type=int,
        default=10,
        help="Progress logging interval (number of documents, default: 10)",
    )
    p.add_argument(
        "--max-documents",
        type=int,
        default=None,
        help="Maximum number of documents to process (default: None, process all)",
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

    logger.info("Starting EDINET batch fetch script")

    try:
        # Step 1: CLI 引数パース
        args = _parse_args()
        logger.info("CLI args parsed successfully")

        # Step 2: 日付の妥当性チェック
        start_date, end_date = _validate_dates(args.start_date, args.end_date)

        # Step 3-4: TestClient コンテキストで実行
        with TestClient(app) as client:
            # Step 3: EDINET バッチ実行
            result = _run(
                client=client,
                start_date=start_date,
                end_date=end_date,
                progress_interval=args.progress_interval,
                max_documents=args.max_documents,
            )

            # Step 4: 結果ログ出力
            _log_edinet_results(result)

        logger.info("EDINET batch fetch completed successfully")

    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise SystemExit(1) from e

    except Exception as e:
        logger.exception("EDINET batch fetch failed: %s", e)
        raise SystemExit(1) from e

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
