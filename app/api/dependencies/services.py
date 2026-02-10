"""Service依存性注入プロバイダ.

FastAPIの`Depends`パターンを使用して各Serviceインスタンスを提供します。
Repository や他の Service との依存関係を解決します。

仕様書: docs/architecture/layers/service_layer.md 3.3章
"""

from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.batch_execution_repository import BatchExecutionRepository
from app.repositories.latest_stocks_repository import LatestStocksRepository
from app.repositories.stock_master_repository import StockMasterRepository
from app.repositories.stock_master_updates_repository import StockMasterUpdatesRepository
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.market_data.edinet.balance_sheet.converter import EdinetBalanceSheetConverter
from app.services.market_data.edinet.balance_sheet.fetcher import EdinetDocumentFetcher
from app.services.market_data.edinet.balance_sheet.file_manager import EdinetFileManager
from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser
from app.services.market_data.edinet.balance_sheet.saver import EdinetBalanceSheetSaver
from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService
from app.services.market_data.edinet.common.api_client import EdinetAPIClient
from app.services.market_data.stock_master import StockMasterService
from app.services.market_data.stock_price import (
    StockPriceConverter,
    StockPriceFetcher,
    StockPriceSaver,
    StockPriceService,
    StockPriceValidator,
)
from app.services.views.latest_stocks.refresh import LatestStocksRefreshService
from app.services.views.latest_stocks.service import LatestStocksService
from app.utils.database import get_db


def get_batch_execution_repository(
    db: AsyncSession = Depends(get_db),
) -> BatchExecutionRepository:
    """BatchExecutionRepository を提供する依存性プロバイダ.

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        BatchExecutionRepository: バッチ実行データアクセスリポジトリ
    """
    return BatchExecutionRepository(session=db)


def get_batch_execution_service(
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
) -> BatchExecutionService:
    """BatchExecutionService を提供する依存性プロバイダ.

    Args:
        repo (BatchExecutionRepository): バッチ実行リポジトリ

    Returns:
        BatchExecutionService: バッチ実行のビジネスロジックサービス
    """
    return BatchExecutionService(repository=repo)


def get_stock_price_fetcher() -> StockPriceFetcher:
    """StockPriceFetcher を提供する依存性プロバイダ.

    Returns:
        StockPriceFetcher: 株価データ取得サービスのインスタンス
    """
    return StockPriceFetcher()


def get_stock_price_converter() -> StockPriceConverter:
    """StockPriceConverter を提供する依存性プロバイダ.

    Returns:
        StockPriceConverter: データ変換サービスのインスタンス
    """
    return StockPriceConverter()


def get_stock_price_validator() -> StockPriceValidator:
    """StockPriceValidator を提供する依存性プロバイダ.

    Returns:
        StockPriceValidator: データ検証サービスのインスタンス
    """
    return StockPriceValidator()


def get_stock_price_saver(
    db: AsyncSession = Depends(get_db),
) -> StockPriceSaver:
    """StockPriceSaver を提供する依存性プロバイダ.

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        StockPriceSaver: 株価データ保存サービスのインスタンス
    """
    return StockPriceSaver(session=db)


def get_stock_master_repository(
    db: AsyncSession = Depends(get_db),
) -> StockMasterRepository:
    """StockMasterRepository を提供する依存性プロバイダ.

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        StockMasterRepository: 銘柄マスタデータのリポジトリ
    """
    return StockMasterRepository(session=db)


def get_stock_master_updates_repository(
    db: AsyncSession = Depends(get_db),
) -> StockMasterUpdatesRepository:
    """StockMasterUpdatesRepository を提供する依存性プロバイダ.

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        StockMasterUpdatesRepository: 銘柄マスタ更新履歴のリポジトリ
    """
    return StockMasterUpdatesRepository(session=db)


def get_stock_master_service(
    repo: StockMasterRepository = Depends(get_stock_master_repository),
    updates_repo: StockMasterUpdatesRepository = Depends(get_stock_master_updates_repository),
) -> StockMasterService:
    """StockMasterService を提供する依存性プロバイダ.

    Args:
        repo (StockMasterRepository): 銘柄マスタリポジトリ
        updates_repo (StockMasterUpdatesRepository): 銘柄マスタ更新履歴リポジトリ

    Returns:
        StockMasterService: 銘柄マスタ関連のビジネスロジックサービス
    """
    return StockMasterService(repo=repo, updates_repo=updates_repo)


def get_stock_price_service(
    fetcher: StockPriceFetcher = Depends(get_stock_price_fetcher),
    saver: StockPriceSaver = Depends(get_stock_price_saver),
    converter: StockPriceConverter = Depends(get_stock_price_converter),
    validator: StockPriceValidator = Depends(get_stock_price_validator),
    stock_master: StockMasterService = Depends(get_stock_master_service),
    batch_service: BatchExecutionService = Depends(get_batch_execution_service),
) -> StockPriceService:
    """StockPriceService を提供する依存性プロバイダ（オーケストレーション層）.

    Args:
        fetcher (StockPriceFetcher): 株価データ取得サービス
        saver (StockPriceSaver): 株価データ保存サービス
        converter (StockPriceConverter): データ変換サービス
        validator (StockPriceValidator): データ検証サービス
        stock_master (StockMasterService): 銘柄マスタサービス
        batch_service (BatchExecutionService): バッチ実行サービス

    Returns:
        StockPriceService: 株価データ収集・保存をオーケストレートするサービス
    """
    # StockMasterService と BatchExecutionService を注入して StockPriceService を生成
    return StockPriceService(
        fetcher=fetcher,
        saver=saver,
        converter=converter,
        validator=validator,
        stock_master_service=stock_master,
        batch_service=batch_service,
    )


def get_latest_stocks_refresh_service(
    batch_service: BatchExecutionService = Depends(get_batch_execution_service),
) -> LatestStocksRefreshService:
    """LatestStocksRefreshService を提供する依存性プロバイダ."""
    return LatestStocksRefreshService(batch_service=batch_service)


def get_latest_stocks_repository(
    db: AsyncSession = Depends(get_db),
) -> LatestStocksRepository:
    """LatestStocksRepository を提供する依存性プロバイダ.

    Args:
        db (AsyncSession): 非同期DBセッション

    Returns:
        LatestStocksRepository: latest_stocks_1dビューへのアクセスリポジトリ
    """
    return LatestStocksRepository(session=db)


def get_latest_stocks_service(
    repository: LatestStocksRepository = Depends(get_latest_stocks_repository),
) -> LatestStocksService:
    """LatestStocksService を提供する依存性プロバイダ.

    Args:
        repository (LatestStocksRepository): latest_stocks_1dリポジトリ

    Returns:
        LatestStocksService: latest_stocks_1dビューからのデータ取得サービス
    """
    return LatestStocksService(repository=repository)


# EDINET 関連の依存性プロバイダ


def get_edinet_api_client() -> EdinetAPIClient:
    """EdinetAPIClient を提供する依存性プロバイダ.

    Returns:
        EdinetAPIClient: EDINET API クライアント
    """
    return EdinetAPIClient()


def get_edinet_document_fetcher(
    api_client: EdinetAPIClient = Depends(get_edinet_api_client),
) -> EdinetDocumentFetcher:
    """EdinetDocumentFetcher を提供する依存性プロバイダ.

    Args:
        api_client: EDINET API クライアント

    Returns:
        EdinetDocumentFetcher: EDINET 文書取得フェッチャ
    """
    work_dir = Path("work/edinet_temp")
    return EdinetDocumentFetcher(api_client=api_client, work_dir=work_dir)


def get_edinet_balance_sheet_parser() -> EdinetBalanceSheetParser:
    """EdinetBalanceSheetParser を提供する依存性プロバイダ.

    Returns:
        EdinetBalanceSheetParser: EDINET 貸借対照表パーサ
    """
    return EdinetBalanceSheetParser()


def get_edinet_balance_sheet_converter() -> EdinetBalanceSheetConverter:
    """EdinetBalanceSheetConverter を提供する依存性プロバイダ.

    Returns:
        EdinetBalanceSheetConverter: EDINET 貸借対照表コンバータ
    """
    return EdinetBalanceSheetConverter()


def get_edinet_balance_sheet_saver(
    db: AsyncSession = Depends(get_db),
) -> EdinetBalanceSheetSaver:
    """EdinetBalanceSheetSaver を提供する依存性プロバイダ.

    Args:
        db: 非同期DBセッション

    Returns:
        EdinetBalanceSheetSaver: EDINET 貸借対照表データ保存サービス
    """
    return EdinetBalanceSheetSaver(session=db)


def get_edinet_file_manager() -> EdinetFileManager:
    """EdinetFileManager を提供する依存性プロバイダ.

    Returns:
        EdinetFileManager: EDINET 一時ファイル管理ユーティリティ
    """
    return EdinetFileManager()


def get_edinet_balance_sheet_service(
    fetcher: EdinetDocumentFetcher = Depends(get_edinet_document_fetcher),
    parser: EdinetBalanceSheetParser = Depends(get_edinet_balance_sheet_parser),
    converter: EdinetBalanceSheetConverter = Depends(get_edinet_balance_sheet_converter),
    saver: EdinetBalanceSheetSaver = Depends(get_edinet_balance_sheet_saver),
    file_manager: EdinetFileManager = Depends(get_edinet_file_manager),
) -> EdinetBalanceSheetService:
    """EdinetBalanceSheetService を提供する依存性プロバイダ.

    Args:
        fetcher: EDINET 文書取得フェッチャ
        parser: EDINET 貸借対照表パーサ
        converter: EDINET 貸借対照表コンバータ
        saver: EDINET 貸借対照表データ保存サービス
        file_manager: EDINET 一時ファイル管理ユーティリティ

    Returns:
        EdinetBalanceSheetService: EDINET 貸借対照表サービス
    """
    return EdinetBalanceSheetService(
        fetcher=fetcher,
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=file_manager,
    )
