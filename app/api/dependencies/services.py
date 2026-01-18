"""Service依存性注入プロバイダ.

FastAPIの`Depends`パターンを使用して各Serviceインスタンスを提供します。
Repository や他の Service との依存関係を解決します。

仕様書: docs/architecture/layers/service_layer.md 3.3章
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.repositories.stock_master_repository import StockMasterRepository
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.market_data.stock_master import StockMasterService
from app.services.market_data.stock_price import (
    StockPriceConverter,
    StockPriceFetcher,
    StockPriceSaver,
    StockPriceService,
    StockPriceValidator,
)
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


def get_stock_master_service(
    repo: StockMasterRepository = Depends(get_stock_master_repository),
) -> StockMasterService:
    """StockMasterService を提供する依存性プロバイダ.

    Args:
        repo (StockMasterRepository): 銘柄マスタリポジトリ

    Returns:
        StockMasterService: 銘柄マスタ関連のビジネスロジックサービス
    """
    return StockMasterService(repo=repo)


def get_stock_price_service(
    fetcher: StockPriceFetcher = Depends(get_stock_price_fetcher),
    saver: StockPriceSaver = Depends(get_stock_price_saver),
    converter: StockPriceConverter = Depends(get_stock_price_converter),
    validator: StockPriceValidator = Depends(get_stock_price_validator),
    stock_master: StockMasterService = Depends(get_stock_master_service),
    batch_service: BatchExecutionService = Depends(
        get_batch_execution_service
    ),
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
