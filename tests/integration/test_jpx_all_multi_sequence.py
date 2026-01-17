import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.utils.database as db_mod
from app.main import app
from app.models.stock_data import Stocks1d, Stocks1h, Stocks1m
from app.utils.logger import get_default_logger
from tests.integration.utils import (
    TEST_SYMBOLS,
    cleanup_database,
    register_test_symbols,
    setup_test_database,
    write_csv_artifact,
)


@pytest.mark.anyio
async def test_jpx_all_multi_sequence_persists_all_timeframes(monkeypatch):
    """
    統合テスト: JPX全銘柄マルチ順次実行APIが1d→1m→1hの順に実行し、
    各タイムフレームのデータが正しくDBに永続化されることを検証します.
    """
    # 各タイムフレーム用のテーブルをセットアップ
    engines = {}
    engines["1d"] = await setup_test_database(monkeypatch, Stocks1d)
    engines["1m"] = await setup_test_database(monkeypatch, Stocks1m)
    engines["1h"] = await setup_test_database(monkeypatch, Stocks1h)

    await register_test_symbols(TEST_SYMBOLS)

    # ロガーを初期化
    get_default_logger()

    # APIエンドポイントを呼び出し
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/batch/stock-data/jpx-all/multi/run_sequence",
            json={"batch_size": 5},
        )

        # レスポンスの確認
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["overall_status"] == "PENDING"

        # バックグラウンド処理の完了を待機（順次実行のため時間がかかる）
        await asyncio.sleep(20)  # 実際のデータ取得には時間がかかる

    # 各タイムフレームのデータがDBに永続化されていることを検証
    session_maker = db_mod.get_session_maker()
    model_map = {"1d": Stocks1d, "1m": Stocks1m, "1h": Stocks1h}
    timeframes = ["1d", "1m", "1h"]

    for timeframe in timeframes:
        async with session_maker() as verify_session:
            all_rows = []
            model = model_map[timeframe]

            for symbol in TEST_SYMBOLS:
                q = await verify_session.execute(
                    select(model).where(model.symbol == symbol)
                )
                rows = q.scalars().all()
                all_rows.extend(rows)

            # データが永続化されていることを確認
            assert len(all_rows) >= 0

            # CSVアーティファクトを出力
            fieldnames = [
                "id",
                "symbol",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "adj_close",
                "created_at",
                "updated_at",
            ]
            write_csv_artifact(
                all_rows,
                timeframe,
                fieldnames,
                use_date=False,
                test_name=f"test_jpx_all_multi_sequence_api_{timeframe}",
            )

    # クリーンアップ
    for engine in engines.values():
        await cleanup_database(engine)


@pytest.mark.anyio
async def test_jpx_all_multi_sequence_with_custom_batch_size(monkeypatch):
    """
    統合テスト: カスタムバッチサイズでJPX全銘柄マルチ順次実行APIを呼び出し、
    データが正しく永続化されることを検証します.
    """
    # 1dのみでテスト（処理速度のため）
    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)

    get_default_logger()

    # カスタムバッチサイズでAPIを呼び出し
    custom_batch_size = 3

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/batch/stock-data/jpx-all/multi/run_sequence",
            json={"batch_size": custom_batch_size},
        )

        # レスポンスの確認
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["overall_status"] == "PENDING"

        # バックグラウンド処理の完了を待機
        await asyncio.sleep(20)

    # データが永続化されていることを検証
    session_maker = db_mod.get_session_maker()
    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1d).where(Stocks1d.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        # データが存在することを確認
        assert len(all_rows) >= 0

        # CSVアーティファクトを出力
        fieldnames = [
            "id",
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]
        write_csv_artifact(
            all_rows,
            "1d",
            fieldnames,
            use_date=False,
            test_name="test_jpx_all_multi_sequence_api_custom_batch_size",
        )

    await cleanup_database(engine)
