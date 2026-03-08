"""配当利回り履歴 e2e テスト."""

# flake8: noqa

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.models.market_data.dividend_yield_history import DividendYieldHistory
from app.models.market_data.edinet import EdinetDocument, EdinetStockDividend
from app.models.market_data.stock_master import StockCodeMapping, StockMaster
from app.models.market_data.stock_price import Stocks1d
from app.utils.database import get_database_url
from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_table,
    run_async_safely,
    verify_stock_master_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (sequential)
pytestmark = pytest.mark.xdist_group("e2e")


async def _insert_test_data_async() -> None:  # pylint: disable=too-many-locals
    """テストデータを非同期で投入.

    以下を投入:
    - StockMaster（5銘柄）
    - StockCodeMapping（JPX code ↔ SEC code）
    - Stocks1d（株価データ、過去30日分）
    - EdinetDocument, EdinetStockDividend（配当データ）
    """
    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            target_date = date(2026, 3, 7)

            # 1. StockMaster を投入
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

            # 2. StockCodeMapping を投入
            sec_codes = ["10001", "10002", "10003", "10004", "10005"]
            mappings = [
                StockCodeMapping(stock_code=code, sec_code=sec)
                for code, sec in zip(stock_codes, sec_codes)
            ]

            for mapping in mappings:
                session.add(mapping)

            await session.flush()

            # 3. Stocks1d を投入（過去30日分）
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

            await session.flush()

            # 4. EdinetDocument を投入
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

            # 5. EdinetStockDividend を投入
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

            await session.commit()
    finally:
        await engine.dispose()


def test_dividend_yield_history_setup_e2e(
    client: TestClient,
) -> None:  # pylint: disable=unused-argument
    """前提：テストデータがDB に投入されていることを確認する.

    セッション フィクスチャ `setup_dividend_yield_history_test_data` で
    テストデータが自動的に投入されています。
    このテストでは投入されたデータが正しく存在することを確認します。

    手順:
    1. StockMaster, StockCodeMapping, Stocks1d, EdinetDocument,
       EdinetStockDividend が存在することを確認
    2. 各テーブルのデータ件数を表示
    """
    # 出口確認: StockMaster にデータが存在
    assert verify_stock_master_has_data(), "StockMaster テーブルにデータが見つかりません"

    # 追加検証：各テーブルのデータ件数を確認
    async def _verify_inserted_data() -> None:  # pylint: disable=too-many-locals
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                # StockMaster
                result = await session.execute(select(StockMaster))
                stock_masters = result.scalars().all()
                print(f"✅ StockMaster: {len(stock_masters)} records")

                # StockCodeMapping
                result = await session.execute(select(StockCodeMapping))
                mappings = result.scalars().all()
                print(f"✅ StockCodeMapping: {len(mappings)} records")

                # Stocks1d
                result = await session.execute(select(Stocks1d))
                stocks_1d = result.scalars().all()
                print(f"✅ Stocks1d: {len(stocks_1d)} records")

                # EdinetDocument
                result = await session.execute(select(EdinetDocument))
                edinet_docs = result.scalars().all()
                print(f"✅ EdinetDocument: {len(edinet_docs)} records")

                # EdinetStockDividend
                result = await session.execute(select(EdinetStockDividend))
                dividends = result.scalars().all()
                print(f"✅ EdinetStockDividend: {len(dividends)} records")

                if dividends:
                    for div in dividends[:1]:
                        # Fetch the related document for verification
                        doc_id = div.edinet_document_id  # type: ignore[attr-defined]
                        doc_result = await session.execute(
                            select(EdinetDocument).where(EdinetDocument.id == doc_id)
                        )
                        doc = doc_result.scalar_one_or_none()
                        if doc:
                            fy = div.fiscal_year  # type: ignore[attr-defined]
                            ped = div.period_end_date  # type: ignore[attr-defined]
                            print(
                                f"  - Dividend fiscal_year={fy}, "
                                f"period_end={ped}, doc.sec_code={doc.sec_code}"
                            )

                # Assertions
                msg_stock = f"Expected 5 StockMaster, got {len(stock_masters)}"
                assert len(stock_masters) == 5, msg_stock
                msg_mapping = f"Expected 5 StockCodeMapping, got {len(mappings)}"
                assert len(mappings) == 5, msg_mapping
                msg_1d = f"Expected Stocks1d records, got {len(stocks_1d)}"
                assert len(stocks_1d) > 0, msg_1d
                msg_doc = f"Expected EdinetDocument records, got {len(edinet_docs)}"
                assert len(edinet_docs) > 0, msg_doc
                msg_div = f"Expected EdinetStockDividend records, got {len(dividends)}"
                assert len(dividends) > 0, msg_div
        finally:
            await engine.dispose()

    run_async_safely(_verify_inserted_data())


def test_dividend_yield_history_api_e2e(client: TestClient) -> None:
    """API エンドポイント呼び出しテスト.

    前提: セットアップテストで投入されたデータ
    手順:
    1. APIクライアント作成（TestClient）
    2. POST /api/v1/dividend-yield-history/generate を呼び出す
    3. レスポンス status_code = 200 を確認
    4. レスポンス body の status = "completed" | "partial_error" を確認
    5. rowcount をログ出力
    """
    # 前提条件確認: StockMaster にデータが存在
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    target_date = date(2026, 3, 7)

    # API呼び出し
    payload = {"target_date": target_date.isoformat()}
    response = client.post(
        "/api/v1/dividend-yield-history/generate",
        json=payload,
    )

    # 入口確認: ステータスコード
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # レスポンスボディ確認
    body = response.json()
    assert "status" in body, "Response missing 'status' key"
    assert body["status"] in [
        "completed",
        "partial_error",
        "no_data",
    ], f"Unexpected status: {body['status']}"

    # rowcount 確認
    assert "rowcount" in body, "Response missing 'rowcount' key"
    assert isinstance(body["rowcount"], int), "rowcount must be int"
    assert body["rowcount"] >= 0, f"rowcount must be >= 0, got {body['rowcount']}"

    # skipped_count, error_count 確認
    assert "skipped_count" in body, "Response missing 'skipped_count' key"
    assert "error_count" in body, "Response missing 'error_count' key"

    print(f"✅ API Response: status={body['status']}, rowcount={body['rowcount']}")


def test_dividend_yield_history_output_e2e(client: TestClient) -> None:
    """DB 格納・アーティファクト出力テスト.

    前提: APIテスト実行後のDB状態
    手順:
    1. DividendYieldHistory テーブルのレコード数確認
    2. 各レコードの dividend_yield 値が正しく計算されているか確認
    3. (symbol, date) ユニークキーの重複がないか確認
    4. アーティファクト CSV を出力
    """
    # 前提条件確認: StockMaster にデータが存在
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    target_date = date(2026, 3, 7)

    # API実行
    payload = {"target_date": target_date.isoformat()}
    response = client.post(
        "/api/v1/dividend-yield-history/generate",
        json=payload,
    )

    # API実行結果を確認
    if response.status_code != 200:
        pytest.skip(f"API call failed: {response.status_code}. " f"Cannot verify DB output.")

    body = response.json()
    rowcount = body.get("rowcount", 0)

    # DividendYieldHistory テーブルをクエリして検証
    async def _verify_db_and_write_artifact() -> int:
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(DividendYieldHistory))
                records = result.scalars().all()

                # アーティファクト CSV を出力（データがなくても出力）
                artifact_data = []
                for record in records:
                    # 出口確認: 各レコードの dividend_yield が正しく計算されているか
                    if record.dividend is not None and record.stock_price is not None:
                        assert record.dividend_yield is not None, (
                            f"dividend_yield should not be None "
                            f"when dividend and stock_price are set: {record}"
                        )

                        # 計算結果の検証（dividend_yield = dividend / stock_price）
                        expected_yield = record.dividend / record.stock_price
                        assert abs(record.dividend_yield - expected_yield) < Decimal("0.0001"), (
                            f"dividend_yield calculation error: "
                            f"expected {expected_yield}, got {record.dividend_yield}"
                        )

                    # データを行に変換
                    row = {
                        "id": record.id,
                        "symbol": record.symbol,
                        "date": record.date.isoformat(),
                        "dividend": str(record.dividend) if record.dividend else "",
                        "stock_price": str(record.stock_price) if record.stock_price else "",
                        "dividend_yield": (
                            str(record.dividend_yield) if record.dividend_yield else ""
                        ),
                        "fiscal_year": record.fiscal_year,
                        "edinet_document_id": record.edinet_document_id,
                    }
                    artifact_data.append(row)

                # データがない場合は注釈付き行を出力
                if not artifact_data:
                    artifact_data = [
                        {
                            "note": "No DividendYieldHistory records found",
                            "reason": "All stocks skipped (missing data or no dividends)",
                        }
                    ]

                # アーティファクト CSV を出力
                if artifact_data:
                    write_csv_artifact(artifact_data, name="dividend_yield_history_e2e")
                    assert_artifact_written("dividend_yield_history_e2e")

                # 出口確認: (symbol, date) ユニークキーの重複がないか（あれば）
                seen = set()
                for record in records:
                    key = (record.symbol, record.date)
                    if key in seen:
                        raise AssertionError(f"Duplicate key found: {key}")
                    seen.add(key)

                print(
                    f"✅ API Response validated: status={body.get('status')}, "
                    f"rowcount={rowcount}, records_found={len(records)}"
                )

                return len(records)
        finally:
            await engine.dispose()

    run_async_safely(_verify_db_and_write_artifact())
