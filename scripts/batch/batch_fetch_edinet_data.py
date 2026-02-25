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
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.repositories.market_data.edinet.edinet_balance_sheet_repository import (
    EdinetBalanceSheetRepository,
)
from app.repositories.market_data.edinet.edinet_cash_flow_statement_repository import (
    EdinetCashFlowStatementRepository,
)
from app.repositories.market_data.edinet.edinet_profit_and_loss_repository import (
    EdinetProfitAndLossRepository,
)
from app.repositories.market_data.edinet.edinet_stock_dividend_repository import (
    EdinetStockDividendRepository,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.converter import (
    EdinetBalanceSheetConverter,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)
from app.services.data_synchronization.market_data.edinet.edinet_cash_flow_statement.converter import (
    EdinetCashFlowStatementConverter,
)
from app.services.data_synchronization.market_data.edinet.edinet_cash_flow_statement.parser import (
    EdinetCashFlowStatementParser,
)
from app.services.market_data.edinet.download_service import EdinetDownloadService
from app.services.market_data.edinet.profit_and_loss.converter import EdinetProfitAndLossConverter
from app.services.market_data.edinet.profit_and_loss.parser import EdinetProfitAndLossParser
from app.services.market_data.edinet.stock_dividend.converter import EdinetStockDividendConverter
from app.services.market_data.edinet.stock_dividend.parser import EdinetStockDividendParser
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.database import close_db, get_engine

logger = logging.getLogger(__name__)


async def _run(
    start_date: date,
    end_date: date,
    progress_interval: int = 10,
    max_documents: int | None = None,
) -> None:
    """メイン処理: 指定期間のEDINETデータを取得しDBへ保存します.

    Args:
        start_date: 取得開始日
        end_date: 取得終了日
        progress_interval: 進捗表示間隔（ドキュメント数）
        max_documents: 最大処理ドキュメント数（Noneの場合は全件）
    """
    engine: AsyncEngine = get_engine()
    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    logger.info(
        "Starting EDINET batch fetch: start_date=%s, end_date=%s, max_documents=%s",
        start_date,
        end_date,
        max_documents,
    )

    async with session_maker() as session:  # type: AsyncSession
        # リポジトリの初期化
        balance_sheet_repo = EdinetBalanceSheetRepository(session=session)
        profit_and_loss_repo = EdinetProfitAndLossRepository(session=session)
        stock_dividend_repo = EdinetStockDividendRepository(session=session)
        cash_flow_repo = EdinetCashFlowStatementRepository(session=session)

        # コンバータの初期化
        balance_sheet_converter = EdinetBalanceSheetConverter()
        profit_and_loss_converter = EdinetProfitAndLossConverter()
        stock_dividend_converter = EdinetStockDividendConverter()
        cash_flow_converter = EdinetCashFlowStatementConverter()

        # パーサとセーバーのペアを設定
        bs_parser = EdinetBalanceSheetParser()
        pl_parser = EdinetProfitAndLossParser()
        sd_parser = EdinetStockDividendParser()
        cfs_parser = EdinetCashFlowStatementParser()

        parser_saver_pairs = [
            (
                bs_parser.parse_root,
                balance_sheet_converter,
                balance_sheet_repo.upsert,
            ),
            (
                pl_parser.parse_root,
                profit_and_loss_converter,
                profit_and_loss_repo.upsert,
            ),
            (
                sd_parser.parse_root,
                stock_dividend_converter,
                stock_dividend_repo.upsert,
            ),
            (
                cfs_parser.parse_root,
                cash_flow_converter,
                cash_flow_repo.upsert,
            ),
        ]

        # サービスの初期化
        download_service = EdinetDownloadService()
        update_service = EdinetAggregateUpdateService(
            download_service=download_service,
            parser_saver_pairs=parser_saver_pairs,
        )

        # バッチ処理の実行
        try:
            summary = await update_service.process_date_range(
                start_date=start_date,
                end_date=end_date,
                progress_interval=progress_interval,
                max_documents=max_documents,
                session=session,
                transaction_atomic=True,
            )

            logger.info(
                "Batch processing completed: status=%s, total=%s, processed=%s, "
                "saved=%s, failed=%s",
                summary.get("status"),
                summary.get("total_documents"),
                summary.get("processed_documents"),
                summary.get("saved_items"),
                summary.get("failed_documents"),
            )

            # 成功時はコミット
            await session.commit()
            logger.info("Successfully committed all changes")

        except Exception as e:
            logger.exception("Batch processing failed: %s", e)
            await session.rollback()
            logger.warning("Rolled back all changes due to error")
            raise

    # エンジンをクリーンアップ
    logger.info("Disposing database engine")
    try:
        await close_db()
    except Exception:
        logger.exception("Failed to dispose DB engine cleanly")


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースします."""
    p = argparse.ArgumentParser(
        description="Fetch EDINET data (Balance Sheet & P/L) for a specified date range"
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
    """エントリポイント.

    コマンドライン引数を解析して非同期メイン処理を実行する。
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    args = _parse_args()

    # 日付文字列をdateオブジェクトに変換
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    except ValueError as e:
        logger.error("Invalid date format: %s", e)
        logger.error("Please use YYYY-MM-DD format for dates")
        raise

    # 日付の妥当性チェック
    if start_date > end_date:
        logger.error("start_date must be before or equal to end_date")
        raise ValueError("start_date must be before or equal to end_date")

    try:
        asyncio.run(
            _run(
                start_date=start_date,
                end_date=end_date,
                progress_interval=args.progress_interval,
                max_documents=args.max_documents,
            )
        )
    except Exception as e:
        logger.exception("Script failed: %s", e)
        raise


if __name__ == "__main__":
    main()
