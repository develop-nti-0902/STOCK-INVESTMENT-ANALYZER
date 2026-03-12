"""バッチスクリプト: スクリーニング実行スクリプト。

スクリーニングを実行し、結果をDBに保存します。

使い方:
    # デフォルト（本日を評価日として実行）
    python -m scripts.batch.batch_run_screening

    # 特定の評価日を指定
    python -m scripts.batch.batch_run_screening --evaluation-date 2025-03-31

    # 特定の銘柄コードでフィルタリング
    python -m scripts.batch.batch_run_screening --sec-codes 1001,1002,1003

    # 複合オプション
    python -m scripts.batch.batch_run_screening --evaluation-date 2025-03-31 --sec-codes 1001,1002
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from app.main import app
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    """CLI 引数をパースします。

    Returns:
        パース済み引数オブジェクト
        - evaluation_date: ISO 形式の日付文字列 or None（デフォルト: 本日）
        - sec_codes: カンマ区切り銘柄コード文字列 or None（デフォルト: None → 全銘柄）

    Raises:
        SystemExit: argparse の parse_error() で exit
    """
    p = argparse.ArgumentParser(
        description=(
            "Run stock screening with optional evaluation date and security codes. "
            "Results are saved to the database screening_results table."
        ),
        epilog=(
            "Examples:\n"
            "  python -m scripts.batch.batch_run_screening\n"
            "  python -m scripts.batch.batch_run_screening --evaluation-date 2025-03-31\n"
            "  python -m scripts.batch.batch_run_screening --sec-codes 1001,1002,1003"
        ),
    )

    p.add_argument(
        "--evaluation-date",
        type=str,
        default=None,
        help="Evaluation date in ISO format (YYYY-MM-DD). Defaults to today.",
    )

    p.add_argument(
        "--sec-codes",
        type=str,
        default=None,
        help="Comma-separated security codes to screen (e.g., '1001,1002,1003'). Defaults to all codes.",
    )

    return p.parse_args()


def _validate_dates(evaluation_date_str: Optional[str]) -> date:
    """評価日を妥当性チェックし、date オブジェクトに変換します。

    Args:
        evaluation_date_str: ISO 形式の日付文字列 or None

    Returns:
        検証済み date オブジェクト

    Raises:
        ValueError: 無効な日付フォーマット
    """
    if evaluation_date_str is None:
        logger.info("No evaluation_date specified, using today's date")
        return datetime.now().date()

    try:
        eval_date = datetime.fromisoformat(evaluation_date_str).date()
        logger.info("Using evaluation_date: %s", eval_date.isoformat())
        return eval_date
    except ValueError as e:
        error_msg = (
            f"Invalid evaluation_date format. Expected YYYY-MM-DD, got '{evaluation_date_str}'"
        )
        logger.error(error_msg)
        raise ValueError(error_msg) from e


def _prepare_stock_master(client: TestClient) -> None:
    """stock_master データを準備するために `/api/v1/stock-master/fetch` を呼び出します。

    Args:
        client: FastAPI TestClient インスタンス

    Raises:
        Exception: API エラーまたは予期しないエラー
    """
    logger.info("Calling stock-master/fetch to prepare stock_master data")

    try:
        response = client.post("/api/v1/stock-master/fetch")
        response.raise_for_status()

        result = response.json()
        status = result.get("status", "unknown")
        fetched_count = result.get("fetched_count", 0)
        updated_count = result.get("updated_count", 0)

        logger.info(
            "Stock master preparation completed: status=%s, fetched=%d, updated=%d",
            status,
            fetched_count,
            updated_count,
        )

    except Exception as e:
        logger.warning("Stock master preparation failed (non-critical): %s", e, exc_info=True)
        # スクリーニング自体は継続する（stock_master データがない場合のみスクリーニングが失敗）


def _run(
    client: TestClient,
    evaluation_date: date,
    sec_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """スクリーニング API を呼び出し、結果を返します。

    Args:
        client: FastAPI TestClient インスタンス
        evaluation_date: 評価日 (date オブジェクト)
        sec_codes: 対象銘柄コードリスト or None（全銘柄対象）

    Returns:
        API レスポンスの JSON（status, result, evaluation_year を含む）

    Raises:
        Exception: API エラーまたは予期しないエラー
    """
    logger.info(
        "Starting screening run: evaluation_date=%s, sec_codes=%s",
        evaluation_date.isoformat(),
        "all" if sec_codes is None else len(sec_codes),
    )

    params = {
        "evaluation_date": evaluation_date.isoformat(),
    }

    if sec_codes is not None and len(sec_codes) > 0:
        params["sec_codes"] = sec_codes

    try:
        response = client.post("/api/v1/screening/run", params=params)
        response.raise_for_status()

        result = response.json()
        result_count = len(result.get("result", []))
        logger.info(
            "Screening API returned status=%s, result_count=%d, evaluation_year=%d",
            result.get("status"),
            result_count,
            result.get("evaluation_year"),
        )

        return result

    except Exception as e:
        logger.error("Screening API failed: %s", e, exc_info=True)
        raise


def _log_screening_results(result: Dict[str, Any]) -> None:
    """スクリーニング結果をログ出力し、統計情報を表示します。

    Args:
        result: API レスポンスオブジェクト
    """
    status = result.get("status", "unknown")
    evaluation_year = result.get("evaluation_year")
    screening_results = result.get("result", [])

    if status != "success":
        logger.warning("Screening status is not success: %s", status)
        return

    logger.info("=" * 80)
    logger.info("SCREENING RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info("Evaluation Year: %d", evaluation_year)
    logger.info("Total Passed: %d", len(screening_results))

    if len(screening_results) > 0:
        # Top 5 結果をログ
        logger.info("Top 5 Results:")
        for i, item in enumerate(screening_results[:5], 1):
            symbol = item.get("symbol", "N/A")
            total_score = item.get("total_score", 0)
            item_status = item.get("status", "N/A")
            logger.info(
                "  %d. Symbol=%s, Score=%.2f, Status=%s",
                i,
                symbol,
                total_score,
                item_status,
            )
    else:
        logger.info("No stocks passed the screening criteria.")

    logger.info("=" * 80)


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

    logger.info("Starting batch screening run script")

    try:
        # Step 1: CLI 引数パース
        args = _parse_args()
        logger.info("CLI args parsed successfully")

        # Step 2: 評価日の妥当性チェック
        evaluation_date = _validate_dates(args.evaluation_date)

        # Step 3: sec_codes のパース
        sec_codes = None
        if args.sec_codes is not None:
            sec_codes = [code.strip() for code in args.sec_codes.split(",") if code.strip()]
            logger.info("Parsed sec_codes: %d items", len(sec_codes))

        # Step 4-6: TestClient が Lifespan イベントを実行するようコンテキストマネージャーで実行
        with TestClient(app) as client:
            # Step 4: stock_master データを準備（非クリティカル）
            _prepare_stock_master(client)

            # Step 5: スクリーニング実行
            result = _run(
                client=client,
                evaluation_date=evaluation_date,
                sec_codes=sec_codes if sec_codes else None,
            )

            # Step 6: 結果ログ出力
            _log_screening_results(result)

        logger.info("Batch screening run completed successfully")

    except ValueError as e:
        logger.error("Validation error: %s", e)
        raise SystemExit(1) from e

    except Exception as e:
        logger.exception("Screening failed: %s", e)
        raise SystemExit(1) from e

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
