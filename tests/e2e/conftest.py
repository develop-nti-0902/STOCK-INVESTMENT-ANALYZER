"""E2E テスト用の共通フィクスチャとユーティリティ.

このモジュールは E2E テストの共通セットアップを提供します.
"""

import os
import socket
from urllib.parse import unquote, urlparse

import pytest
from fastapi.testclient import TestClient

from app.main import app


def is_db_reachable() -> bool:
    """DB 到達性を同期ソケットで簡易チェックする.

    優先順序:
    1. DATABASE_URL を優先。SQLite の場合はファイル存在確認で判定
    2. DATABASE_URL がなければ DB_HOST/DB_PORT でソケット接続判定

    SQLiteの場合はファイルの存在またはメモリDBを確認します。
    E2Eテストは各テスト内で独自のDBセットアップを行うため、
    相対パスの場合は到達可能と判断します。
    """
    # 最優先: DATABASE_URL を取得して判定
    db_url = None
    try:
        from app.utils.config import get_settings

        try:
            settings = get_settings()
            db_url = getattr(settings, "DATABASE_URL", None)
        except Exception:
            # 設定が不完全な場合は環境変数にフォールバック
            pass
    except Exception:
        # import エラー等は無視
        pass

    # get_settings() から取得できなかった場合は環境変数を使う
    if not db_url:
        db_url = os.getenv("DATABASE_URL")

    # DATABASE_URL が設定されている場合、それを優先的に使用
    if db_url:
        parsed = urlparse(db_url)
        scheme = (parsed.scheme or "").lower()

        # SQLite を使う場合、ファイルが存在するかメモリ DB の場合は到達可能と判定
        if scheme.startswith("sqlite"):
            # sqlite:///path の場合、parsed.path は /path になる（Windows なら /C:/path）
            path = unquote(parsed.path or "")

            # メモリDB の場合
            if path == ":memory:" or path == "" or not path:
                return True

            # Windows 絶対パスの場合: /C:/path -> C:/path に正規化
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

            # ファイル存在確認（相対・絶対両方に対応）
            # E2E テストは各テストで独自の DB をセットアップするため、
            # 相対パスの場合は到達可能と判断する
            if os.path.exists(path):
                return True

            # 相対パスの場合は E2E テスト用として許可
            if not os.path.isabs(path):
                return True

            # 絶対パスの場合、ファイルが存在しなければ到達不可
            return os.path.exists(path)

        # PostgreSQL など他のスキームの場合、ソケット接続を試みる
        parsed_host = parsed.hostname
        parsed_port = parsed.port
        if parsed_host and parsed_port:
            try:
                with socket.create_connection((parsed_host, parsed_port), timeout=1):
                    return True
            except Exception:
                return False
        return False

    # DATABASE_URL が設定されていない場合、DB_HOST/DB_PORT を使用
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")

    # アプリ設定から取得
    try:
        from app.utils.config import get_settings

        try:
            settings = get_settings()
            host = getattr(settings, "DB_HOST", host)
            port = getattr(settings, "DB_PORT", port)
        except Exception:
            pass
    except Exception:
        pass

    if not host or not port:
        return False

    try:
        with socket.create_connection((host, int(port)), timeout=1):
            return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """E2E テスト実行時に DB 到達不良なら該当テストをスキップする."""
    if not is_db_reachable():
        skip_marker = pytest.mark.skip(reason="DB unreachable — skipping E2E tests")
        for item in items:
            # ファイルパスをUNIX形式に変換して判定
            if "tests/e2e" in str(item.fspath).replace("\\", "/"):
                item.add_marker(skip_marker)


@pytest.fixture(scope="function", autouse=True)
def reset_event_loop_for_e2e():
    """E2E Tests用のイベントループ管理（tests/conftest.py を上書き）.

    tests/conftest.py の `reset_event_loop` を E2E 環境用に上書きします。
    E2E テストでは独自の TestClient を使うため、`close_db()` を呼びません。
    """
    import asyncio
    import gc

    # テスト前: イベントループの確認/作成
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    yield

    # テスト後: ガベージコレクションのみ
    try:
        gc.collect()
    except Exception:
        pass


@pytest.fixture(scope="function")
def client():
    """Provide a FastAPI TestClient pytest fixture with Lifespan enabled."""
    # E2E テストでも Lifespan を実行して、ScreeningService を初期化
    try:
        with TestClient(app) as c:
            yield c
    except Exception as e:
        print(f"⚠️  TestClient setup error: {e}")
        raise


@pytest.fixture(scope="function")
def clear_advisory_locks(request):
    """No-op for advisory locks in SQLite environment."""
    # SQLite環境では何もせずにyield
    yield


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_database():
    """E2Eテスト用データベースをセットアップ.

    Alembicマイグレーションを実行して、テーブルを作成します。
    セッションスコープで一度だけ実行されます。
    """
    import subprocess
    import sys

    try:
        # alembic upgrade head を実行
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )

        if result.returncode != 0:
            print(f"⚠️  Alembic migration warning: {result.stderr}")
        else:
            print("✅ E2E database initialized with alembic migrations")
    except Exception as e:
        print(f"⚠️  Failed to run alembic migrations: {e}")
        # マイグレーション失敗時も続行（テーブルが既に存在する可能性）

    yield


@pytest.fixture(scope="session", autouse=True)
def setup_dividend_yield_history_test_data():
    """配当利回り履歴e2eテスト用テストデータをセットアップ.

    セッションスコープで一度だけ実行されます。
    全テストプロセスで共有されるようにセッション開始時にデータを投入します。
    """
    import asyncio
    from datetime import date, datetime, timedelta
    from decimal import Decimal

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.dividend_yield_history import DividendYieldHistory
    from app.models.market_data.edinet import EdinetDocument, EdinetStockDividend
    from app.models.market_data.stock_master import StockCodeMapping, StockMaster
    from app.models.market_data.stock_price import Stocks1d
    from app.utils.database import get_database_url

    async def _setup_data():
        """非同期でテストデータを投入"""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                target_date = date(2026, 3, 7)

                # 1. 既存データをクリーンアップ
                tables_to_clean = [
                    DividendYieldHistory,
                    EdinetStockDividend,
                    EdinetDocument,
                    Stocks1d,
                    StockCodeMapping,
                    StockMaster,
                ]
                for table in tables_to_clean:
                    await session.execute(delete(table))
                await session.commit()
                print("✅ Cleaned up existing dividend yield history test data")

                # 2. StockMaster を投入
                stock_definitions = [
                    ("7203", "トヨタ自動車"),
                    ("6098", "リクルート"),
                    ("9984", "ソフトバンクグループ"),
                    ("9437", "ＮＴＴドコモ"),
                    ("8306", "三井住友銀行"),
                ]
                stocks = [
                    StockMaster(
                        stock_code=code,
                        stock_name=name,
                        data_date=target_date,
                        is_active=True,
                    )
                    for code, name in stock_definitions
                ]
                stock_codes = [s.stock_code for s in stocks]

                for stock in stocks:
                    session.add(stock)
                await session.flush()
                print(f"✅ Inserted {len(stocks)} StockMaster records")

                # 3. StockCodeMapping を投入
                sec_codes = ["10001", "10002", "10003", "10004", "10005"]
                mappings = [
                    StockCodeMapping(stock_code=code, sec_code=sec)
                    for code, sec in zip(stock_codes, sec_codes)
                ]
                for mapping in mappings:
                    session.add(mapping)
                await session.flush()
                print(f"✅ Inserted {len(mappings)} StockCodeMapping records")

                # 4. Stocks1d を投入（過去30日分）
                total_stocks_1d = 0
                for symbol in stock_codes:
                    for i in range(30):
                        check_date = target_date - timedelta(days=i)
                        timestamp = datetime.combine(check_date, datetime.min.time())
                        stock_1d = Stocks1d(
                            symbol=symbol,
                            timestamp=timestamp,
                            open=Decimal("1000.0") + Decimal(i),
                            high=Decimal("1050.0") + Decimal(i),
                            low=Decimal("950.0") + Decimal(i),
                            close=Decimal("1010.0") + Decimal(i),
                            adj_close=Decimal("1010.0") + Decimal(i),
                            volume=1000000,
                        )
                        session.add(stock_1d)
                        total_stocks_1d += 1
                await session.flush()
                print(f"✅ Inserted {total_stocks_1d} Stocks1d records")

                # 5. EdinetDocument を投入
                fiscal_year = target_date.year - 1
                edinet_docs = []
                for sec_code in sec_codes:
                    for fy_offset in range(3):
                        doc_id = f"E{sec_code}{fiscal_year - fy_offset:04d}12-31-000"
                        doc = EdinetDocument(
                            doc_id=doc_id,
                            sec_code=sec_code,
                            submission_date=date(fiscal_year - fy_offset, 6, 30),
                            report_type="annual",
                        )
                        edinet_docs.append(doc)
                        session.add(doc)
                await session.flush()
                print(f"✅ Inserted {len(edinet_docs)} EdinetDocument records")

                # 6. EdinetStockDividend を投入
                dividend_count = 0
                for _stock_code, sec_code in zip(stock_codes, sec_codes):
                    matching_docs = [d for d in edinet_docs if d.sec_code == sec_code]
                    if matching_docs:
                        doc = matching_docs[0]
                        dividend = EdinetStockDividend(
                            edinet_document_id=doc.id,
                            period_end_date=date(target_date.year - 1, 3, 31),
                            fiscal_year=target_date.year - 1,
                            dividend_actual=Decimal("50.00"),
                            dividend_adj=Decimal("50.00"),
                            is_consolidated=True,
                        )
                        session.add(dividend)
                        dividend_count += 1

                await session.commit()
                print(f"✅ Inserted {dividend_count} EdinetStockDividend records")
                print("✅ Dividend yield history e2e test data initialization completed")
        finally:
            await engine.dispose()

    # セッション開始時にデータ投入
    print("🔧 Starting dividend yield history e2e test data setup fixture...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_setup_data())
    finally:
        loop.close()

    yield


@pytest.fixture(scope="function")
def loaded_edinet_test_data():
    """
    CSV から過去5年のEDINET疑似データを投入

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
    import asyncio
    from pathlib import Path

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet.edinet_cash_flow_statement import EdinetCashFlowStatement
    from app.models.market_data.edinet.edinet_profit_and_loss import EdinetProfitAndLoss
    from app.models.market_data.edinet.edinet_stock_dividend import EdinetStockDividend
    from app.models.market_data.stock_master.stock_master import StockMaster
    from app.utils.database import get_database_url
    from tests.e2e.csv_data_loader import EdinetCsvDataLoader

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
            from app.models.market_data.stock_master.stock_code_mapping import StockCodeMapping

            await async_session.execute(delete(StockCodeMapping))
            await async_session.commit()

            # sector_33_master にテストデータを投入
            from app.models.market_data.stock_master.sector_33_master import Sector33Master

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
    import asyncio

    from app.main import app as fastapi_app

    if hasattr(fastapi_app.state, "screening_service") and fastapi_app.state.screening_service:
        try:
            asyncio.run(fastapi_app.state.screening_service._init_industry_config_cache())
            print("✅ Screening service industry config cache reloaded after test data load")
        except Exception as e:
            print(f"⚠️  Failed to reload screening service cache: {e}")

    yield result
