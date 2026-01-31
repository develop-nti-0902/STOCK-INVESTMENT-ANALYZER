"""EDINET 貸借対照表取得バッチのラッパースクリプト。

使用例:
    # 過去30日間のデータを取得
    python scripts/run_edinet_batch.py --days 30

    # 指定期間のデータを取得
    python scripts/run_edinet_batch.py --start-date 2024-01-01 \
        --end-date 2024-01-31
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# noqa: E402 - プロジェクトルートをパスに追加した後にインポート
from app.repositories.batch_execution_repository import (  # noqa: E402
    BatchExecutionRepository,
)
from app.services.batch.batch_execution_service import (  # noqa: E402
    BatchExecutionService,
)
from app.services.batch.fetch_edinet_balance_sheets import (  # noqa: E402
    fetch_edinet_balance_sheets_job,
)
from app.utils.database import get_session_maker  # noqa: E402
from app.utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


async def main() -> None:
    """メイン処理。"""
    parser = argparse.ArgumentParser(description="EDINET 貸借対照表取得バッチ")
    parser.add_argument(
        "--start-date",
        type=str,
        help="検索開始日 (YYYY-MM-DD形式)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="検索終了日 (YYYY-MM-DD形式)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="過去何日分のデータを取得するか（デフォルト: 30日）",
    )

    args = parser.parse_args()

    # 日付の設定
    if args.start_date and args.end_date:
        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)
        except ValueError as e:
            logger.error("Invalid date format: %s", e)
            sys.exit(1)
    else:
        end_date = date.today()
        start_date = end_date - timedelta(days=args.days)

    logger.info(
        "Starting EDINET batch for period: %s to %s", start_date, end_date
    )

    # バッチサービスの初期化
    session_maker = get_session_maker()

    # バッチ実行リポジトリとサービスの作成
    async with session_maker() as session:
        batch_repository = BatchExecutionRepository(session)
        batch_service = BatchExecutionService(repository=batch_repository)

        try:
            result = await fetch_edinet_balance_sheets_job(
                batch_service=batch_service,
                start_date=start_date,
                end_date=end_date,
            )
            logger.info("Batch completed successfully: %s", result)
            print("\n=== バッチ実行結果 ===")
            print(f"ステータス: {result.get('status')}")
            print(f"総ドキュメント数: {result.get('total_documents')}")
            print(f"処理成功: {result.get('processed_documents')}")
            print(f"保存年度数: {result.get('saved_years')}")
            print(f"処理失敗: {result.get('failed_documents')}")
            print("=" * 25)
        except Exception as e:
            logger.exception("Batch failed: %s", e)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
