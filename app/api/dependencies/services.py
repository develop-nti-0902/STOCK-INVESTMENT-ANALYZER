"""
Service依存性注入プロバイダ

FastAPIのDependsパターンを使用して、各Serviceインスタンスを提供する。
Repositoryや他のServiceとの依存関係を解決します。

仕様書: docs/architecture/layers/service_layer.md 3.3章
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master import StockMasterService
from app.services.market_data.stock_price import (
    StockPriceConverter,
    StockPriceFetcher,
    StockPriceSaver,
    StockPriceService,
    StockPriceValidator,
)
from app.utils.database import get_db


def get_stock_price_fetcher() -> StockPriceFetcher:
    """
    StockPriceFetcherを提供

    Returns:
        StockPriceFetcher: 株価データ取得サービス
    """
    return StockPriceFetcher()


def get_stock_price_converter() -> StockPriceConverter:
    """
    StockPriceConverterを提供

    Returns:
        StockPriceConverter: データ変換サービス
    """
    return StockPriceConverter()


def get_stock_price_validator() -> StockPriceValidator:
    """
    StockPriceValidatorを提供

    Returns:
        StockPriceValidator: データ検証サービス
    """
    return StockPriceValidator()


def get_stock_price_saver(
    db: AsyncSession = Depends(get_db),
) -> StockPriceSaver:
    """
    StockPriceSaverを提供

    Args:
        db: 非同期DBセッション

    Returns:
        StockPriceSaver: 株価データ保存サービス
    """
    return StockPriceSaver(session=db)


def get_stock_master_repository(
    db: AsyncSession = Depends(get_db),
) -> StockMasterRepository:
    """
    StockMasterRepositoryを提供

    Args:
        db: 非同期DBセッション

    Returns:
        StockMasterRepository: 銘柄マスタリポジトリ
    """
    return StockMasterRepository(session=db)


def get_stock_master_service(
    repo: StockMasterRepository = Depends(get_stock_master_repository),
) -> StockMasterService:
    """
    StockMasterServiceを提供

    Args:
        repo: 銘柄マスタリポジトリ

    Returns:
        StockMasterService: 銘柄マスタサービス
    """
    return StockMasterService(repo=repo)


def get_stock_price_service(
    fetcher: StockPriceFetcher = Depends(get_stock_price_fetcher),
    saver: StockPriceSaver = Depends(get_stock_price_saver),
    converter: StockPriceConverter = Depends(get_stock_price_converter),
    validator: StockPriceValidator = Depends(get_stock_price_validator),
    stock_master: StockMasterService = Depends(get_stock_master_service),
) -> StockPriceService:
    """
    StockPriceServiceを提供（オーケストレーション層）

    Args:
        fetcher: 株価データ取得サービス
        saver: 株価データ保存サービス
        converter: データ変換サービス
        validator: データ検証サービス

    Returns:
        StockPriceService: 株価データ収集サービス
    """
    # StockMasterService を注入して StockPriceService を生成
    return StockPriceService(
        fetcher=fetcher,
        saver=saver,
        converter=converter,
        validator=validator,
        stock_master_service=stock_master,
    )
