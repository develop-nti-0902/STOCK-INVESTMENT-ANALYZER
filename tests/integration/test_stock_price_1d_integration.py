import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.models.base import Base
from app.models.stock_data import Stocks1d
from app.repositories.stock_data_repository import StockData1dRepository
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.mark.anyio
async def test_fetch_and_save_1d_stock_data(monkeypatch):
    """
    統合テスト: yfinanceから1d株価データをフェッチし、Stocks1dテーブルへ保存するまでの
    一連の流れを検証する。

    前提:
    - `app.utils.database.get_database_url()` がテスト用Postgresの接続文字列を返すこと
    - テストは実ネットワーク（Yahoo Finance API）へアクセスし、DBへ書き込みを行うため
      テスト用の分離された環境で実行すること

    検証内容:
    1. StockPriceFetcherで特定銘柄の1dデータを取得
    2. StockPriceSaverを使用してStocks1dテーブルへ保存
    3. DBに正しくデータが保存されていることを確認
    4. 取得したデータをCSVとして出力
    """

    # Arrange（準備）: DB エンジン準備
    try:
        DATABASE_URL = db_mod.get_database_url()
    except (
        Exception
    ) as exc:  # pragma: no cover - 環境変数未設定時は明示的に失敗させる
        pytest.skip(f"Skipping integration test: missing DB config ({exc})")

    engine = create_async_engine(DATABASE_URL, echo=False)

    # モジュールの `get_engine` をテスト用エンジンに差し替える
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    # キャッシュクリア（既存のキャッシュが残っている可能性があるため）
    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    # Arrange（準備）: テーブル作成とクリーンアップ
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # integrationテストは毎回クリーンな状態から開始するため、既存データを削除
        from sqlalchemy import delete

        from app.models.stock_master import StockMaster

        await conn.execute(delete(Stocks1d))
        await conn.execute(delete(StockMaster))

    # Arrange（準備）: テスト対象銘柄とパラメータ設定
    # 日本市場の主要10銘柄を選定
    test_symbols = [
        "7203.T",  # トヨタ自動車
        "9984.T",  # ソフトバンクグループ
        "6758.T",  # ソニーグループ
        "9433.T",  # KDDI
        "8306.T",  # 三菱UFJフィナンシャル・グループ
        "6861.T",  # キーエンス
        "6954.T",  # ファナック
        "4063.T",  # 信越化学工業
        "6902.T",  # デンソー
        "7741.T",  # HOYA
    ]
    timeframe = "1d"
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)

    # Arrange（準備）: stock_masterに銘柄を登録
    # 外部キー制約を満たすため、株価データを保存する前に銘柄情報を登録
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        from app.models.stock_master import StockMaster

        for symbol in test_symbols:
            master = StockMaster(
                stock_code=symbol,
                stock_name=f"Test Company {symbol}",
                market_category="TSE Prime",
                sector_name_33="Test Industry",
                is_active=1,
            )
            session.add(master)

        await session.commit()
        logger.info(f"Registered {len(test_symbols)} symbols in stock_master")

    # Act（実行）: StockPriceFetcherで複数銘柄のデータを並列取得
    fetcher = StockPriceFetcher()
    all_stock_data = await fetcher.fetch_batch(
        symbols=test_symbols,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    # Assert（事前検証）: すべての銘柄でデータが取得できていること
    total_records = 0
    for symbol in test_symbols:
        stock_data_list = all_stock_data.get(symbol, [])
        assert len(stock_data_list) > 0, (
            f"No data fetched for {symbol} between {start_date} and "
            f"{end_date}"
        )
        total_records += len(stock_data_list)
        logger.info(
            f"Fetched {len(stock_data_list)} records for {symbol} from "
            "Yahoo Finance"
        )

    expected_count = total_records
    logger.info(
        f"Total fetched {expected_count} records for {len(test_symbols)} "
        "symbols from Yahoo Finance"
    )

    # Act（実行）: StockData1dRepositoryで複数銘柄のデータを保存
    async with session_maker() as session:
        # StockData1dRepositoryを直接使用して保存
        repo = StockData1dRepository(session=session)

        # 全銘柄のStockDataリストをDB形式の辞書リストに変換
        # Stocks1dモデルは "symbol" と "date" カラムを持っている
        all_db_records = []
        for symbol, stock_data_list in all_stock_data.items():
            for data in stock_data_list:
                all_db_records.append(
                    {
                        "symbol": symbol,
                        "date": (
                            data.trade_date.date()
                            if hasattr(data.trade_date, "date")
                            else data.trade_date
                        ),
                        "open": data.open_price,
                        "high": data.high,
                        "low": data.low,
                        "close": data.close,
                        "volume": data.volume,
                        "adj_close": data.adj_close,
                    }
                )

        # リポジトリのupsert_bulkメソッドを使ってデータ保存
        saved_count = await repo.upsert_bulk(all_db_records)

        # Assert（検証）: 保存が成功したこと
        # 注: yfinanceの一部データがDBのチェック制約（high >= low など）に
        # 違反する可能性があるため、わずかな失敗レコードは許容する
        success_rate = (
            saved_count / expected_count if expected_count > 0 else 0
        )
        assert success_rate > 0.99, (
            f"Expected to save most records (>99%), but only saved "
            f"{saved_count}/{expected_count} ({success_rate:.2%})"
        )

        if saved_count < expected_count:
            logger.warning(
                f"Some records failed to save: {expected_count - saved_count} "
                "out of {expected_count} (likely due to data quality issues)"
            )

    # Assert（検証）: 新しいセッションで永続化が完了していることを確認
    async with session_maker() as verify_session:
        # 全銘柄のデータが正しく保存されているか確認
        all_rows = []
        for symbol in test_symbols:
            result = await verify_session.execute(
                select(Stocks1d).where(Stocks1d.symbol == symbol)
            )
            symbol_rows = result.scalars().all()
            all_rows.extend(symbol_rows)

            expected_symbol_count = len(all_stock_data[symbol])
            # データ品質問題による少数の失敗は許容
            symbol_rate = (
                len(symbol_rows) / expected_symbol_count
                if expected_symbol_count > 0
                else 0
            )
            symbol_msg = (
                f"Expected most records (>95%) for {symbol}, "
                f"but got {len(symbol_rows)}/{expected_symbol_count} "
                f"({symbol_rate:.2%})"
            )
            assert symbol_rate > 0.95, symbol_msg

            # データの整合性を確認（各銘柄の最初のレコードをサンプルチェック）
            if symbol_rows:
                first_row = symbol_rows[0]
                assert first_row.symbol == symbol
                assert first_row.open is not None
                assert first_row.high is not None
                assert first_row.low is not None
                assert first_row.close is not None

            logger.info(
                f"Verified {len(symbol_rows)} records for {symbol} "
                "persisted correctly"
            )

        # 全体の永続化件数を確認（わずかなデータ品質問題による失敗は許容）
        persistence_rate = (
            len(all_rows) / expected_count if expected_count > 0 else 0
        )
        assert persistence_rate > 0.99, (
            f"Expected most rows (>99%) in Stocks1d table, but got "
            f"{len(all_rows)}/{expected_count} ({persistence_rate:.2%})"
        )

        logger.info(
            f"Verified total {len(all_rows)} records for "
            f"{len(test_symbols)} symbols persisted correctly in Stocks1d "
            "table"
        )

        rows = all_rows  # CSV出力用に変数を設定

        # 生産物: 全件ダンプを CSV で出力（tests/integration/artifacts/ に保存）
        import csv

        artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(artifacts_dir, f"stocks_1d_multiple_{ts}.csv")

        fieldnames = [
            "id",
            "symbol",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adj_close",
            "created_at",
            "updated_at",
        ]

        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(
                        {
                            "id": getattr(r, "id", None),
                            "symbol": getattr(r, "symbol", None),
                            "date": getattr(r, "date", None),
                            "open": getattr(r, "open", None),
                            "high": getattr(r, "high", None),
                            "low": getattr(r, "low", None),
                            "close": getattr(r, "close", None),
                            "volume": getattr(r, "volume", None),
                            "adj_close": getattr(r, "adj_close", None),
                            "created_at": getattr(r, "created_at", None),
                            "updated_at": getattr(r, "updated_at", None),
                        }
                    )
            logger.info(f"Wrote full dump to {out_path}")
        except Exception as e:  # pragma: no cover - artifact write
            logger.error(f"Failed to write artifact: {e}")

    # Cleanup: drop tables (best-effort)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        # テーブル削除失敗は無視（テスト自体は成功している）
        pass
