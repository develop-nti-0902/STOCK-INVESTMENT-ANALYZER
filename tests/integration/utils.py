import csv
import os
from datetime import datetime, timezone
from typing import List, Type

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

import app.utils.database as db_mod
from app.models.base import Base
from app.models.stock_master import StockMaster


def write_csv_artifact(
    rows,
    timeframe: str,
    fieldnames: List[str],
    use_date: bool = False,
    filename: str | None = None,
    test_name: str | None = None,
) -> None:
    """テスト用アーティファクトとしてCSVを出力するユーティリティ関数。

    Args:
        rows: ORMオブジェクトのリスト
        timeframe: 時間枠ラベル（例: "1d"）
        fieldnames: CSVのヘッダ順
        use_date: 日付フィールドを使うか
        filename: 明示的な出力ファイル名（省略時はデフォルト名を使用）
        test_name: テスト名。指定するとファイル先頭に書き出されます。

    Note:
        テストユーティリティなので失敗しても例外は破棄します。
    """
    artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if filename:
        out_path = os.path.join(artifacts_dir, filename)
    else:
        if test_name:
            out_path = os.path.join(
                artifacts_dir,
                f"{test_name}_stocks_{timeframe}_multiple_{ts}.csv",
            )
        else:
            out_path = os.path.join(
                artifacts_dir, f"stocks_{timeframe}_multiple_{ts}.csv"
            )

    try:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            # 先頭にテスト名があれば書き込む（コメント行）
            if test_name:
                f.write(f"# Test: {test_name}\n")

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                row_data = {
                    "id": getattr(r, "id", None),
                    "symbol": getattr(r, "symbol", None),
                    "open": getattr(r, "open", None),
                    "high": getattr(r, "high", None),
                    "low": getattr(r, "low", None),
                    "close": getattr(r, "close", None),
                    "volume": getattr(r, "volume", None),
                    "adj_close": getattr(r, "adj_close", None),
                    "created_at": getattr(r, "created_at", None),
                    "updated_at": getattr(r, "updated_at", None),
                }
                if use_date:
                    row_data["date"] = getattr(r, "date", None)
                else:
                    row_data["timestamp"] = getattr(r, "timestamp", None)
                writer.writerow(row_data)
    except Exception:
        # テストユーティリティなので失敗してもテスト本体の結果を阻害しない
        pass


# 共通テストヘルパーと定数
TEST_SYMBOLS: List[str] = [
    "7203",
    "6758",
    "9432",
    "9984",
    "8306",
    "6861",
    "6098",
    "7974",
    "6954",
    "4063",
]


async def setup_test_database(
    monkeypatch, stock_model_class: Type
) -> AsyncEngine:
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"Skipping integration test: missing DB config ({exc})")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(delete(stock_model_class))
        await conn.execute(delete(StockMaster))

    return engine


async def register_test_symbols(symbols: List[str]) -> None:
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        for symbol in symbols:
            master = StockMaster(
                stock_code=symbol,
                stock_name=f"Test Company {symbol}",
                market_category="TSE Prime",
                sector_name_33="Test Industry",
                is_active=1,
            )
            session.add(master)
        await session.commit()


async def cleanup_database(engine: AsyncEngine) -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        pass
