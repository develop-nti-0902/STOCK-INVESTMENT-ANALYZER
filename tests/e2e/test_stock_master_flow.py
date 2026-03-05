"""Stock master flow E2E tests."""

# flake8: noqa
import time

import pytest

from app.repositories.market_data.stock_master import (
    MarketCategoryMasterRepository,
    ScaleMasterRepository,
    Sector17MasterRepository,
    Sector33MasterRepository,
    StockCodeMappingRepository,
    StockMasterRepository,
)
from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_repository_delete_all,
    fetch_market_category_master_for_artifact,
    fetch_scale_master_for_artifact,
    fetch_sector_17_master_for_artifact,
    fetch_sector_33_master_for_artifact,
    fetch_stock_code_mapping_for_artifact,
    run_async_safely,
    verify_stock_master_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


async def _fetch_stock_master_rows_for_artifact():
    """stock_master テーブルから全データを取得（async）."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_master import StockMaster
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(StockMaster))
            rows = result.scalars().all()
            cols = [c.name for c in StockMaster.__table__.columns]
            out = []
            for r in rows:
                row = {}
                for c in cols:
                    v = getattr(r, c)
                    try:
                        if hasattr(v, "isoformat"):
                            v = v.isoformat()
                    except Exception:
                        pass
                    row[c] = v
                out.append(row)
            return out
    finally:
        await engine.dispose()


async def _fetch_stock_master_rows_for_artifact():
    """stock_master テーブルから全データを取得（async）."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_master import StockMaster
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(StockMaster))
            rows = result.scalars().all()
            cols = [c.name for c in StockMaster.__table__.columns]
            out = []
            for r in rows:
                row = {}
                for c in cols:
                    v = getattr(r, c)
                    try:
                        if hasattr(v, "isoformat"):
                            v = v.isoformat()
                    except Exception:
                        pass
                    row[c] = v
                out.append(row)
            return out
    finally:
        await engine.dispose()


async def _fetch_master_tables_for_artifact():
    """全マスターテーブルのデータを取得（sector_17, sector_33, market_category, stock_code_mapping, scale）."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_master import (
        MarketCategoryMaster,
        ScaleMaster,
        Sector17Master,
        Sector33Master,
        StockCodeMapping,
        StockMasterUpdates,
    )
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result_map = {}

            # 各テーブルをフェッチ
            for table_class, table_name in [
                (Sector17Master, "sector_17_master"),
                (Sector33Master, "sector_33_master"),
                (MarketCategoryMaster, "market_category_master"),
                (StockCodeMapping, "stock_code_mapping"),
                (ScaleMaster, "scale_master"),
                (StockMasterUpdates, "stock_master_updates"),
            ]:
                result = await session.execute(select(table_class))
                rows = result.scalars().all()
                cols = [c.name for c in table_class.__table__.columns]
                out = []
                for r in rows:
                    row = {}
                    for c in cols:
                        v = getattr(r, c)
                        try:
                            if hasattr(v, "isoformat"):
                                v = v.isoformat()
                        except Exception:
                            pass
                        row[c] = v
                    out.append(row)
                result_map[table_name] = out

            return result_map
    finally:
        await engine.dispose()


def test_fetch_sample_stock_master(client):
    """API: POST /stock-master/fetch/sample を実行してDB確認.

    手順:
    1. StockMaster テーブルをクリーンアップ
    2. POST /api/v1/stock-master/fetch/sample を実行
    3. レスポンス確認
    4. DB に格納されたことを確認（verify_stock_master_has_data）
    """
    # 前準備: リセット
    client.delete("/api/v1/stock-master/reset")

    # 全マスターテーブルをクリーンアップ
    run_async_safely(cleanup_repository_delete_all(StockMasterRepository))
    run_async_safely(cleanup_repository_delete_all(StockCodeMappingRepository))
    run_async_safely(cleanup_repository_delete_all(MarketCategoryMasterRepository))
    run_async_safely(cleanup_repository_delete_all(Sector33MasterRepository))
    run_async_safely(cleanup_repository_delete_all(Sector17MasterRepository))
    run_async_safely(cleanup_repository_delete_all(ScaleMasterRepository))

    # API: sample fetch を実行
    sample_url = "/api/v1/stock-master/fetch/sample?sample_size=50&batch_size=50"
    response = client.post(sample_url)

    # 入口確認: レスポンス
    assert response.status_code in (
        200,
        201,
        204,
    ), f"Expected 200/201/204, got {response.status_code}"

    if response.status_code == 200:
        data = response.json()
        assert "(sample_size=50)" in data.get(
            "message", ""
        ), "sample_size=50 がレスポンスに含まれていません"

    # 出口確認: DB格納（全7テーブル）
    assert verify_stock_master_has_data(), "StockMaster テーブルにデータが格納されていません"

    # artifact: 全テーブルのデータを出力（必須）
    try:
        # stock_master テーブル
        stock_master_data = run_async_safely(_fetch_stock_master_rows_for_artifact())
        if stock_master_data:
            write_csv_artifact(stock_master_data, name="test_fetch_sample_stock_master")
            assert_artifact_written("test_fetch_sample_stock_master")
        else:
            raise AssertionError("stock_master fetch returned empty list")

        # マスターテーブル群（sector_17, sector_33, market_category, stock_code_mapping, scale, updates）
        master_tables_data = run_async_safely(_fetch_master_tables_for_artifact())

        table_mapping = {
            "sector_17_master": "test_fetch_sample_sector_17_master",
            "sector_33_master": "test_fetch_sample_sector_33_master",
            "market_category_master": "test_fetch_sample_market_category_master",
            "stock_code_mapping": "test_fetch_sample_stock_code_mapping",
            "scale_master": "test_fetch_sample_scale_master",
            "stock_master_updates": "test_fetch_sample_stock_master_updates",
        }

        for table_name, artifact_name in table_mapping.items():
            if table_name in master_tables_data and master_tables_data[table_name]:
                write_csv_artifact(master_tables_data[table_name], name=artifact_name)
                assert_artifact_written(artifact_name)

    except Exception as e:
        import traceback

        error_msg = f"Failed to write/verify artifact: {e}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        raise AssertionError(error_msg) from e


def test_fetch_full_stock_master(client):
    """API: POST /stock-master/fetch を実行してDB確認.

    手順:
    1. StockMaster テーブルをクリーンアップ
    2. POST /api/v1/stock-master/fetch を実行
    3. レスポンス確認
    4. DB に格納されたことを確認（verify_stock_master_has_data）
    """
    # 前準備: リセット
    client.delete("/api/v1/stock-master/reset")

    # 全マスターテーブルをクリーンアップ
    run_async_safely(cleanup_repository_delete_all(StockMasterRepository))
    run_async_safely(cleanup_repository_delete_all(StockCodeMappingRepository))
    run_async_safely(cleanup_repository_delete_all(MarketCategoryMasterRepository))
    run_async_safely(cleanup_repository_delete_all(Sector33MasterRepository))
    run_async_safely(cleanup_repository_delete_all(Sector17MasterRepository))
    run_async_safely(cleanup_repository_delete_all(ScaleMasterRepository))

    # API: full fetch を実行
    response = client.post("/api/v1/stock-master/fetch")

    # 入口確認: レスポンス
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    assert isinstance(data.get("updated_count"), int), "updated_count は整数である必要があります"

    # 出口確認: DB格納（全7テーブル）
    assert verify_stock_master_has_data(), "StockMaster テーブルにデータが格納されていません"

    # artifact: 全テーブルのデータを出力（必須）
    try:
        # stock_master テーブル
        stock_master_data = run_async_safely(_fetch_stock_master_rows_for_artifact())
        if stock_master_data:
            write_csv_artifact(stock_master_data, name="test_fetch_full_stock_master")
            assert_artifact_written("test_fetch_full_stock_master")
        else:
            raise AssertionError("stock_master fetch returned empty list")

        # マスターテーブル群（sector_17, sector_33, market_category, stock_code_mapping, scale, updates）
        master_tables_data = run_async_safely(_fetch_master_tables_for_artifact())

        table_mapping = {
            "sector_17_master": "test_fetch_full_sector_17_master",
            "sector_33_master": "test_fetch_full_sector_33_master",
            "market_category_master": "test_fetch_full_market_category_master",
            "stock_code_mapping": "test_fetch_full_stock_code_mapping",
            "scale_master": "test_fetch_full_scale_master",
            "stock_master_updates": "test_fetch_full_stock_master_updates",
        }

        for table_name, artifact_name in table_mapping.items():
            if table_name in master_tables_data and master_tables_data[table_name]:
                write_csv_artifact(master_tables_data[table_name], name=artifact_name)
                assert_artifact_written(artifact_name)

    except Exception as e:
        import traceback

        error_msg = f"Failed to write/verify artifact: {e}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        raise AssertionError(error_msg) from e


def test_get_stock_symbols(client):
    """API: GET /stock-master/symbols の応答確認.

    手順:
    1. 前提条件確認（stock_master にデータが存在）
    2. GET /api/v1/stock-master/symbols を実行
    3. レスポンス確認
    """
    # 前提条件確認
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    # API: symbols を取得
    response = client.get("/api/v1/stock-master/symbols")

    # 入口確認: レスポンス
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    data = response.json()
    symbols = data.get("symbols") if isinstance(data, dict) else data

    assert isinstance(symbols, list), "symbols はリストである必要があります"
    assert len(symbols) > 0, "symbols が空です"


def test_get_stock_symbols_by_market(client):
    """API: GET /stock-master/symbols/market/{market} の応答確認.

    手順:
    1. 前提条件確認（stock_master にデータが存在）
    2. GET /api/v1/stock-master/symbols を実行してサンプル market を取得
    3. GET /api/v1/stock-master/symbols/market/{market} でフィルタ取得
    4. レスポンス確認
    """
    # 前提条件確認
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    # symbols を取得してマーケット情報を確認
    response = client.get("/api/v1/stock-master/symbols")
    assert response.status_code == 200

    data = response.json()
    symbols = data.get("symbols") if isinstance(data, dict) else data

    # テスト対象の市場リスト
    candidate_markets = [
        "ETF・ETN",
        "PRO Market",
        "REIT・ベンチャーファンド・カントリーファンド・インフラファンド",
        "グロース（外国株式）",
        "グロース（内国株式）",
        "スタンダード（外国株式）",
        "スタンダード（内国株式）",
        "プライム（外国株式）",
        "プライム（内国株式）",
        "出資証券",
    ]

    # 各市場についてフィルタリングを確認
    for market in candidate_markets:
        url = f"/api/v1/stock-master/symbols/market/{market}"
        response = client.get(url)

        assert (
            response.status_code == 200
        ), f"市場 {market} のエンドポイントが失敗しました: {response.status_code}"

        items = response.json()
        if isinstance(items, dict):
            items = items.get("symbols") or []

        assert isinstance(items, list), f"市場 {market} のレスポンスがリストではありません"

        assert len(items) > 0, f"市場 {market} の symbols が空です"
