"""Performance test fixtures.

パフォーマンステスト用のfixture定義。実DB接続を使用します。
"""

# flake8: noqa

import asyncio
from pathlib import Path
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import app as fastapi_app
from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
from app.models.market_data.stock_master.sector_33_master import Sector33Master
from app.models.market_data.stock_master.stock_code_mapping import StockCodeMapping
from app.models.market_data.stock_master.stock_master import StockMaster
from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
    StockMasterUpdatesRepository,
)
from app.utils.database import get_database_url
from tests.e2e.csv_data_loader import EdinetCsvDataLoader


def _run_async(coro):
    """非同期関数を同期コンテキストで実行するヘルパー."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@pytest.fixture(scope="function")
def perf_client():
    """パフォーマンステスト用の実DB接続を備えたTestClient.

    E2Eテストと同様に、実DBに接続します（モック不使用）。
    """
    try:
        with TestClient(fastapi_app) as tc:
            yield tc
    finally:
        pass


@pytest.fixture(scope="function")
def setup_perf_test_db():
    """パフォーマンステスト実行前のDB準備とクリーンアップ.

    テスト対象テーブルを削除し、クリーンな状態にします：
    - stock_masters
    - stock_code_mappings
    - stock_master_updates

    Yields:
        None（クリーンアップ完了後）
    """

    async def _cleanup():
        """非同期クリーンアップ処理."""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                # 各リポジトリの delete メソッドでクリーンアップ
                repo = StockMasterRepository(session=session)
                await repo.delete_all()

                code_mapping_repo = StockCodeMappingRepository(session=session)
                await code_mapping_repo.delete_all()

                updates_repo = StockMasterUpdatesRepository(session=session)
                await updates_repo.delete_by_reset()

                await session.commit()
        finally:
            await engine.dispose()

    # テスト前: DB クリーンアップ
    _run_async(_cleanup())

    yield

    # テスト後: DB クリーンアップ（残存データ削除）
    _run_async(_cleanup())


@pytest.fixture(scope="function")
def loaded_edinet_test_data() -> Dict:
    """
    CSV から過去5年のEDINET疑似データを投入.

    Fixture 仕様:
    - Scope: function（各テスト独立）
    - 前処理: テーブルクリア → CSV 読み込み → DB 投入
    - 後処理: テスト後は自動クリーンアップ

    Returns:
        {
            "stock_master": LoadResult,
            "profit_and_loss": LoadResult,
            "cash_flow_statement": LoadResult,
            "stock_dividend": LoadResult,
        }
    """

    async def _load_data():
        # テスト用 AsyncSession を作成
        db_url = get_database_url()
        engine = create_async_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=1,
        )

        async_session = AsyncSession(engine, expire_on_commit=False)
        await async_session.begin()

        try:
            # テスト対象テーブルをクリア（既存データを削除）
            await async_session.execute(delete(EdinetStockDividend))
            await async_session.execute(delete(EdinetCashFlowStatement))
            await async_session.execute(delete(EdinetProfitAndLoss))
            await async_session.execute(delete(StockMaster))
            await async_session.execute(delete(StockCodeMapping))
            await async_session.commit()

            # sector_33_master にテストデータを投入
            await async_session.execute(delete(Sector33Master))

            # 全33業種のテストデータを投入
            industry_list = [
                ("01", "水産・農林業"),
                ("02", "鉱業"),
                ("03", "建設業"),
                ("04", "食料品"),
                ("05", "繊維製品"),
                ("06", "パルプ・紙"),
                ("07", "化学"),
                ("08", "医薬品"),
                ("09", "石油・石炭製品"),
                ("10", "ゴム製品"),
                ("11", "ガラス・土石製品"),
                ("12", "鉄鋼"),
                ("13", "非鉄金属"),
                ("14", "金属製品"),
                ("15", "機械"),
                ("16", "電気機器"),
                ("17", "輸送用機器"),
                ("18", "精密機器"),
                ("19", "その他製品"),
                ("20", "電気・ガス業"),
                ("21", "陸運業"),
                ("22", "海運業"),
                ("23", "空運業"),
                ("24", "倉庫・運搬関連業"),
                ("25", "情報・通信業"),
                ("26", "卸売業"),
                ("27", "小売業"),
                ("28", "銀行業"),
                ("29", "証券业"),
                ("30", "保険業"),
                ("31", "その他金融業"),
                ("32", "不動産業"),
                ("33", "サービス業"),
            ]

            for code, name in industry_list:
                sector = Sector33Master(code=code, name=name)
                async_session.add(sector)

            await async_session.commit()

            loader = EdinetCsvDataLoader(async_session)

            # CSV ファイルパスを指定
            csv_paths = {
                "stock_master": Path("tests/e2e/fixtures/data/stock_master_screening.csv"),
                "profit_and_loss": Path("tests/e2e/fixtures/data/edinet_profit_and_loss_5yr.csv"),
                "cash_flow_statement": Path(
                    "tests/e2e/fixtures/data/edinet_cash_flow_statement_5yr.csv"
                ),
                "stock_dividend": Path("tests/e2e/fixtures/data/edinet_stock_dividend_5yr.csv"),
            }

            result = await loader.load_edinet_test_data(csv_paths)

            # デバッグ用ログ
            for model_name, load_result in result.items():
                print(f"  ✅ {model_name}: {load_result.records_loaded} records loaded")

            # stock_code_mapping テーブルに投入（stock_code = sec_code としてシンプルにマッピング）
            test_codes = ["1001", "1002", "1003", "2001", "2002"]
            for code in test_codes:
                mapping = StockCodeMapping(stock_code=code, sec_code=code)
                async_session.add(mapping)
            await async_session.commit()
            print(f"  ✅ stock_code_mapping: {len(test_codes)} mappings added")

            return result
        finally:
            # クリーンアップ（テスト用データは commit済みのため、closeのみ）
            await async_session.close()
            await engine.dispose()

    # asyncio.run() で async 処理を実行
    result = asyncio.run(_load_data())

    # screening_service のキャッシュを再度初期化（fixture で投入したデータを反映）
    if hasattr(fastapi_app.state, "screening_service") and fastapi_app.state.screening_service:
        try:
            asyncio.run(fastapi_app.state.screening_service._init_industry_config_cache())
            print("✅ Screening service industry config cache reloaded after test data load")
        except Exception as e:
            print(f"⚠️  Failed to reload screening service cache: {e}")

    yield result
