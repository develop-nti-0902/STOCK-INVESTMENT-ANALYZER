"""Utility helpers for E2E tests."""

# flake8: noqa

from __future__ import annotations

import asyncio
import csv
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Dict, List, Optional, TypeVar, Union

ARTIFACT_DIR = os.path.join(os.getcwd(), "tests", "e2e", "artifacts")

T = TypeVar("T")


@asynccontextmanager
async def get_test_engine() -> AsyncIterator[Any]:
    """テスト用の一時エンジンを作成し、確実にクリーンアップする.

    使用例:
        async with get_test_engine() as engine:
            async with engine.connect() as conn:
                # use connection
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.utils.database import get_database_url

    engine = create_async_engine(
        get_database_url(),
        pool_pre_ping=True,
        pool_size=2,  # テスト用に小さめ
        max_overflow=3,
    )
    try:
        yield engine
    finally:
        await engine.dispose()
        # dispose完了を確実にするため短時間待機
        await asyncio.sleep(0.05)


def run_async_safely(coro: Awaitable[T]) -> T:
    """既存のイベントループを使用して非同期関数を実行する（ループを閉じない）。

    テスト内で asyncio.run() を使用すると新しいイベントループが作成され、
    完了後に閉じられてしまい、後続のテストでイベントループが使えなくなります。
    このヘルパー関数は既存のイベントループを再利用します。

    Args:
        coro: 実行する非同期関数（コルーチン）

    Returns:
        非同期関数の実行結果

    Raises:
        RuntimeError: 実行中のイベントループ内から呼び出された場合
    """
    import gc
    import warnings

    try:
        # 既に実行中のloop があるかチェック
        asyncio.get_running_loop()
        # 実行中のループが存在する場合、同期的に実行できない
        raise RuntimeError(
            "Cannot run async function from within a running event loop. " "Use await instead."
        )
    except RuntimeError as e:
        # "no running event loop" のエラーの場合は問題なし
        if "running event loop" in str(e) and "no" not in str(e).lower():
            # 実行中のループがある場合のエラーは再raise
            raise

    # 実行中のループがないので、既存のループを取得または作成
    try:
        loop = asyncio.get_event_loop()
        # ループが閉じられているかチェック
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
    except RuntimeError:
        # ループが存在しない、または閉じられている
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # ループを閉じずに実行
    try:
        result = loop.run_until_complete(coro)
        return result
    finally:
        # 実行後にリソースをクリーンアップ
        # 未完了のタスクがあればクリーンアップ（ただしengine.dispose()のような重要な処理は完了させる）
        try:
            # 保留中のタスクを確認
            pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
            if pending:
                # タスクをキャンセルしないで、完了を待つ（最大5秒）
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True), timeout=5.0
                        )
                    )
                except asyncio.TimeoutError:
                    # タイムアウトした場合のみキャンセル
                    for task in pending:
                        task.cancel()
                    try:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                gc.collect()
        except Exception:
            pass


def _ensure_dir() -> None:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)


def _safe_name(name: Optional[str]) -> str:
    if not name:
        return uuid.uuid4().hex
    # ファイル名として安全な形式に変換する
    return name.replace("@", "_").replace("/", "_")


def write_json_artifact(data: Dict[str, Any], name: Optional[str] = None) -> str:
    """JSON形式のアーティファクトを `tests/e2e/artifacts` に書き込み、ファイルパスを返す。

    Args:
        data: 書き込む JSON シリアライズ可能な辞書。
        name: ファイル名のベース（拡張子なし）。省略可。

    Returns:
        書き込んだファイルの絶対パス。
    """
    _ensure_dir()
    base = _safe_name(name)
    # name が指定されていれば固定名で上書き、なければタイムスタンプ付きで保存
    if name:
        filename = f"{base}.json"
    else:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"{ts}_{base}.json"
    path = os.path.join(ARTIFACT_DIR, filename)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path


def write_csv_artifact(data: Union[Dict[str, Any], List[Dict[str, Any]]], name: str) -> str:
    """CSV形式のアーティファクトを書き込む。常に `name`.csv の固定名で上書きする。

    Args:
        data: 辞書または辞書のリスト。辞書なら1行、リストならヘッダ付きの複数行として書き込む。
        name: 出力ファイルのベース名（拡張子なし）。実行ごとに上書きされる。

    Returns:
        書き込んだファイルの絶対パス。
    """
    _ensure_dir()
    base = _safe_name(name)
    filename = f"{base}.csv"
    path = os.path.join(ARTIFACT_DIR, filename)

    def _to_str(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    # 単一辞書 -> ヘッダ + 1行
    if isinstance(data, dict):
        keys = list(data.keys())
        # timestamp を先頭に移動する
        if "timestamp" in keys:
            keys = [k for k in keys if k != "timestamp"]
            keys.insert(0, "timestamp")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(keys)
            writer.writerow([_to_str(data.get(k)) for k in keys])
        return path

    # 辞書のリスト -> ヘッダは全キーの合計（安定化のためソート）
    if isinstance(data, list):
        if not data:
            # 空リストは空ファイルを作る
            open(path, "w", encoding="utf-8").close()
            return path
        # ヘッダを決定
        keys_set = {k for row in data for k in row.keys()}
        # timestamp を先頭に、それ以外はソートして続ける
        if "timestamp" in keys_set:
            other_keys = sorted(k for k in keys_set if k != "timestamp")
            keys = ["timestamp"] + other_keys
        else:
            keys = sorted(keys_set)
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(keys)
            for row in data:
                writer.writerow([_to_str(row.get(k)) for k in keys])
        return path

    # サポート外の型は空ファイルにする
    open(path, "w", encoding="utf-8").close()
    return path


def write_text_artifact(text: str, name: Optional[str] = None) -> str:
    """テキストのアーティファクトを書き込み、ファイルパスを返す。name 指定時は固定名で上書きする。"""
    _ensure_dir()
    base = _safe_name(name)
    if name:
        filename = f"{base}.txt"
    else:
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"{ts}_{base}.txt"
    path = os.path.join(ARTIFACT_DIR, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


async def fetch_stock_master_for_artifact() -> List[Dict[str, Any]]:
    """stock_masterテーブルから全データを取得してアーティファクト用に返す。

    Returns:
        stock_masterテーブルの全レコードを辞書のリストで返す。
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_master import StockMaster
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(StockMaster))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "stock_code": row.stock_code,
                    "stock_name": row.stock_name,
                    "market_category": row.market_category,
                    "sector_code_33": row.sector_code_33,
                    "sector_name_33": row.sector_name_33,
                    "sector_code_17": row.sector_code_17,
                    "sector_name_17": row.sector_name_17,
                    "scale_code": row.scale_code,
                    "scale_category": row.scale_category,
                    "data_date": row.data_date,
                    "is_active": row.is_active,
                    "created_at": (row.created_at.isoformat() if row.created_at else None),
                    "updated_at": (row.updated_at.isoformat() if row.updated_at else None),
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


async def fetch_stock_code_mapping_for_artifact() -> List[Dict[str, Any]]:
    """stock_code_mappingテーブルから全データを取得してアーティファクト用に返す。

    Returns:
        stock_code_mappingテーブルの全レコードを辞書のリストで返す。
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_master import StockCodeMapping
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(StockCodeMapping))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "stock_code": row.stock_code,
                    "sec_code": row.sec_code,
                    "created_at": (row.created_at.isoformat() if row.created_at else None),
                    "updated_at": (row.updated_at.isoformat() if row.updated_at else None),
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


class TableCleanupManager:
    """E2Eテスト用のテーブルクリーンアップ処理を提供するマネージャークラス。"""

    # ========== EDINET関連のクリーンアップ ==========

    @staticmethod
    async def cleanup_edinet_balance_sheets() -> None:
        """edinet_balance_sheets テーブルのデータをクリーンアップする."""
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetBalanceSheet
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(EdinetBalanceSheet))
                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    async def cleanup_edinet_profit_and_loss() -> None:
        """edinet_profit_and_loss テーブルのデータをクリーンアップする."""
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetProfitAndLoss
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(EdinetProfitAndLoss))
                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    async def cleanup_edinet_stock_dividend() -> None:
        """edinet_stock_dividend テーブルのデータをクリーンアップする."""
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetStockDividend
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(EdinetStockDividend))
                await session.commit()
        finally:
            await engine.dispose()

    @staticmethod
    async def cleanup_edinet_cash_flow_statement() -> None:
        """edinet_cash_flow_statement テーブルのデータをクリーンアップする."""
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetCashFlowStatement
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                await session.execute(delete(EdinetCashFlowStatement))
                await session.commit()
        finally:
            await engine.dispose()

    # ========== EDINET関連のフェッチ ==========

    @staticmethod
    async def fetch_edinet_balance_sheet_rows() -> List[Dict[str, Any]]:
        """edinet_balance_sheets テーブルから全データを取得する.

        Returns:
            edinet_balance_sheets テーブルの全レコードを辞書のリストで返す
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetBalanceSheet
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(EdinetBalanceSheet))
                rows = result.scalars().all()
                return [
                    {
                        "id": row.id,
                        "sec_code": row.sec_code,
                        "filer_name": row.filer_name,
                        "doc_id": row.doc_id,
                        "period_end_date": (
                            row.period_end_date.isoformat() if row.period_end_date else None
                        ),
                        "submission_date": (
                            row.submission_date.isoformat() if row.submission_date else None
                        ),
                        "fiscal_year": row.fiscal_year,
                        "total_assets": float(row.total_assets) if row.total_assets else None,
                        "total_liabilities": (
                            float(row.total_liabilities) if row.total_liabilities else None
                        ),
                        "total_equity": float(row.total_equity) if row.total_equity else None,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ]
        finally:
            await engine.dispose()

    @staticmethod
    async def fetch_edinet_profit_and_loss_rows() -> List[Dict[str, Any]]:
        """edinet_profit_and_loss テーブルから全データを取得する.

        Returns:
            edinet_profit_and_loss テーブルの全レコードを辞書のリストで返す
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetProfitAndLoss
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(EdinetProfitAndLoss))
                rows = result.scalars().all()
                return [
                    {
                        "id": row.id,
                        "sec_code": row.sec_code,
                        "doc_id": row.doc_id,
                        "period_end_date": (
                            row.period_end_date.isoformat() if row.period_end_date else None
                        ),
                        "submission_date": (
                            row.submission_date.isoformat() if row.submission_date else None
                        ),
                        "fiscal_year": row.fiscal_year,
                        "report_type": row.report_type,
                        "net_sales": float(row.net_sales) if row.net_sales is not None else None,
                        "operating_income": (
                            float(row.operating_income)
                            if row.operating_income is not None
                            else None
                        ),
                        "eps": float(row.eps) if row.eps is not None else None,
                        "candidate_contexts": row.candidate_contexts,
                        "candidate_keys": row.candidate_keys,
                        "is_consolidated": row.is_consolidated,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ]
        finally:
            await engine.dispose()

    @staticmethod
    async def fetch_edinet_stock_dividend_rows() -> List[Dict[str, Any]]:
        """edinet_stock_dividend テーブルから全データを取得する.

        Returns:
            edinet_stock_dividend テーブルの全レコードを辞書のリストで返す
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetStockDividend
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(EdinetStockDividend))
                rows = result.scalars().all()
                return [
                    {
                        "id": row.id,
                        "sec_code": row.sec_code,
                        "doc_id": row.doc_id,
                        "period_end_date": (
                            row.period_end_date.isoformat() if row.period_end_date else None
                        ),
                        "submission_date": (
                            row.submission_date.isoformat() if row.submission_date else None
                        ),
                        "fiscal_year": row.fiscal_year,
                        "report_type": row.report_type,
                        "dividend_actual": (
                            float(row.dividend_actual) if row.dividend_actual is not None else None
                        ),
                        "candidate_contexts": row.candidate_contexts,
                        "candidate_keys": row.candidate_keys,
                        "is_consolidated": row.is_consolidated,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ]
        finally:
            await engine.dispose()

    @staticmethod
    async def fetch_edinet_cash_flow_statement_rows() -> List[Dict[str, Any]]:
        """edinet_cash_flow_statement テーブルから全データを取得する.

        Returns:
            edinet_cash_flow_statement テーブルの全レコードを辞書のリストで返す
        """
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.models.market_data.edinet import EdinetCashFlowStatement
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(EdinetCashFlowStatement))
                rows = result.scalars().all()
                return [
                    {
                        "id": row.id,
                        "sec_code": row.sec_code,
                        "doc_id": row.doc_id,
                        "period_end_date": (
                            row.period_end_date.isoformat() if row.period_end_date else None
                        ),
                        "submission_date": (
                            row.submission_date.isoformat() if row.submission_date else None
                        ),
                        "fiscal_year": row.fiscal_year,
                        "report_type": row.report_type,
                        "operating_cf": (
                            float(row.operating_cf) if row.operating_cf is not None else None
                        ),
                        "candidate_contexts": row.candidate_contexts,
                        "candidate_keys": row.candidate_keys,
                        "is_consolidated": row.is_consolidated,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    }
                    for row in rows
                ]
        finally:
            await engine.dispose()

    # ========== Stock Master関連のクリーンアップ ==========

    @staticmethod
    async def cleanup_batch_executions() -> None:
        """BatchExecution table removed — nothing to cleanup."""
        await asyncio.sleep(0)

    @staticmethod
    async def cleanup_stock_code_mapping() -> None:
        """stock_code_mapping テーブルをクリーンアップする."""
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from app.repositories.market_data.stock_master import StockCodeMappingRepository
        from app.utils.database import get_database_url

        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                repo = StockCodeMappingRepository(session=session)
                deleted = await repo.delete_all()
                await session.commit()
                if deleted > 0:
                    print(f"DEBUG: Cleaned up {deleted} stock_code_mapping records")
        finally:
            await engine.dispose()
