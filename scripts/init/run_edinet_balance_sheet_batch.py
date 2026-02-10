"""EDINET 貸借対照表バッチ実行スクリプト.

使い方例:
    python -m scripts.init.run_edinet_balance_sheet_batch \
        --start-date 2025-06-25 --end-date 2025-06-25 --max-documents 2

このスクリプトはEdinetBalanceSheetServiceの一括取得メソッドを直接呼び出します。
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.market_data.edinet.balance_sheet.converter import EdinetBalanceSheetConverter
from app.services.market_data.edinet.balance_sheet.fetcher import EdinetDocumentFetcher
from app.services.market_data.edinet.balance_sheet.file_manager import EdinetFileManager
from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser
from app.services.market_data.edinet.balance_sheet.saver import EdinetBalanceSheetSaver
from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService
from app.services.market_data.edinet.common.api_client import EdinetAPIClient
from app.utils.database import get_engine

logger = logging.getLogger(__name__)


async def _run(
    start_date: str,
    end_date: str,
    progress_interval: int = 10,
    max_documents: int | None = None,
) -> None:
    """EDINET 貸借対照表の一括取得を実行する.

    Args:
        start_date: 検索開始日（YYYY-MM-DD形式）
        end_date: 検索終了日（YYYY-MM-DD形式）
        progress_interval: 進捗ログ出力の間隔
        max_documents: 最大処理ドキュメント数
    """
    engine = get_engine()
    SessionMaker = async_sessionmaker(
        bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False
    )

    async with SessionMaker() as session:
        ##########################################################
        # 依存コンポーネントの構築
        ##########################################################
        api_client = EdinetAPIClient()
        fetcher = EdinetDocumentFetcher(api_client=api_client, work_dir=Path("work/edinet_temp"))
        parser = EdinetBalanceSheetParser()
        file_manager = EdinetFileManager()
        converter = EdinetBalanceSheetConverter()
        saver = EdinetBalanceSheetSaver(session=session)

        ##########################################################
        # サービスの初期化
        ##########################################################
        service = EdinetBalanceSheetService(
            fetcher=fetcher,
            parser=parser,
            converter=converter,
            saver=saver,
            file_manager=file_manager,
        )

        ##########################################################
        # 日付のパース
        ##########################################################
        try:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
        except Exception as e:
            logger.exception("Invalid date format: %s", e)
            raise

        logger.info(
            "Starting EDINET balance sheet fetch: %s - %s (max_documents=%s)",
            sd,
            ed,
            max_documents,
        )

        ##########################################################
        # 一括取得の実行
        ##########################################################
        result = await service.fetch_multiple_balance_sheets(
            start_date=sd,
            end_date=ed,
            progress_interval=progress_interval,
            max_documents=max_documents,
        )
        # 明示的にコミットして永続化する
        try:
            await session.commit()
        except Exception:
            logger.exception("Failed to commit DB session")

        logger.info("Batch processing result: %s", result)
        print("\n=== Processing Result ===")
        print(f"Status: {result['status']}")
        print(f"Total documents: {result['total_documents']}")
        print(f"Processed documents: {result['processed_documents']}")
        print(f"Saved years: {result['saved_years']}")
        print(f"Failed documents: {result['failed_documents']}")

    ##########################################################
    # エンジンのクリーンアップ
    ##########################################################
    try:
        await engine.dispose()
    except Exception:
        logger.exception("Failed to dispose DB engine")


def _parse_args() -> argparse.Namespace:
    """コマンドライン引数をパースする."""
    from datetime import date as _date

    p = argparse.ArgumentParser(description="Run EDINET balance sheet batch")

    today = _date.today().isoformat()
    p.add_argument("--start-date", default=today, help="Start date (YYYY-MM-DD)")
    p.add_argument("--end-date", default=today, help="End date (YYYY-MM-DD)")
    p.add_argument("--progress-interval", type=int, default=10, help="Progress log interval")
    p.add_argument(
        "--max-documents", type=int, default=None, help="Max documents to process (optional)"
    )
    return p.parse_args()


def main() -> None:
    """エントリポイント."""
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    try:
        asyncio.run(
            _run(
                start_date=args.start_date,
                end_date=args.end_date,
                progress_interval=args.progress_interval,
                max_documents=args.max_documents,
            )
        )
    except Exception as e:
        logger.exception("EDINET script failed: %s", e)
        raise


if __name__ == "__main__":
    main()
