"""E2Eテスト: 日経225構成銘柄の統合フロー検証.

テスト内容:
1. StockMasterService.fetch_and_save() の返り値に nikkei225 フィールドが含まれること
2. Nikkei225ComponentsService.fetch_and_update() 後、nikkei225_components テーブルに
   レコードが保存されること（SQLite 実テーブル確認）

外部HTTP通信はすべてモック（unittest.mock.patch）で代替する。
"""

# flake8: noqa

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_table,
    run_async_safely,
    verify_table_has_data,
    write_csv_artifact,
    write_json_artifact,
)

# 全 E2E テストを同一 xdist ワーカーで実行
pytestmark = pytest.mark.xdist_group("e2e")

# ---------------------------------------------------------------------------
# サンプルデータ定数
# ---------------------------------------------------------------------------

# 日経225 CSV（Shift-JIS エンコード相当）のモック文字列
# 列: コード, 株価換算係数, 対象日付
_NIKKEI225_CSV_TEXT = "コード,株価換算係数,対象日付\n7203,1.0,2026/04/01\n"


# StockMaster fetch のモック返り値（最小限のデータ）
def _make_stock_master_mock_result():
    from app.schemas.market_data.stock_master import StockMasterNormalized

    mock_stocks = [
        StockMasterNormalized(
            stock_code="7203",
            stock_name="トヨタ自動車",
            market_category="Prime",
            sector_code_33="08",
            sector_name_33="自動車",
            sector_code_17="1",
            sector_name_17="自動車",
            scale_code="L",
            scale_category="大型株",
            data_date="20260418",
            is_active=1,
        )
    ]
    return {
        "market_categories": {"Prime": "Prime"},
        "sector_33": {"08": "自動車"},
        "sector_17": {"1": "自動車"},
        "scale": {"L": "大型株"},
        "stocks": mock_stocks,
    }


def _make_nikkei225_mock_session() -> MagicMock:
    """aiohttp.ClientSession のモックを生成する（e2e 用）."""
    csv_bytes = _NIKKEI225_CSV_TEXT.encode("shift_jis")

    mock_response = AsyncMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.read = AsyncMock(return_value=csv_bytes)
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_http_session = MagicMock()
    mock_http_session.get = MagicMock(return_value=mock_response)
    mock_http_session.__aenter__ = AsyncMock(return_value=mock_http_session)
    mock_http_session.__aexit__ = AsyncMock(return_value=None)
    return mock_http_session


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------


async def _run_nikkei225_fetch_and_update() -> dict:
    """Nikkei225ComponentsService.fetch_and_update() を実テーブルで実行するヘルパー."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.services.market_data.nikkei225 import Nikkei225ComponentsService
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            service = Nikkei225ComponentsService(session)
            result = await service.fetch_and_update()
            return result
    finally:
        await engine.dispose()


async def _fetch_nikkei225_components_rows() -> list:
    """nikkei225_components テーブルの全行をアーティファクト用に取得する."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.nikkei225 import Nikkei225Component
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Nikkei225Component))
            rows = result.scalars().all()
            cols = [c.name for c in Nikkei225Component.__table__.columns]
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
                    row[c] = str(v) if v is not None else None
                out.append(row)
            return out
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# テスト 1: fetch_and_save() の返り値に nikkei225 フィールドが含まれること
# ---------------------------------------------------------------------------


def test_fetch_and_save_includes_nikkei225_result(client):
    """StockMasterService.fetch_and_save() 返り値に nikkei225 フィールドが含まれること.

    手順:
    1. StockMasterFetcher.fetch_and_extract_masters を AsyncMock でモック
    2. Nikkei225ComponentsService 内の aiohttp.ClientSession をモック
    3. POST /api/v1/stock-master/fetch/sample を呼び出し
    4. レスポンスに nikkei225 フィールドが存在し、必須キーを持つことを確認
    """
    mock_fetch_result = _make_stock_master_mock_result()

    with patch(
        "app.services.data_synchronization.market_data.stock_master.fetcher.StockMasterFetcher.fetch_and_extract_masters",
        new_callable=AsyncMock,
        return_value=mock_fetch_result,
    ):
        with patch(
            "aiohttp.ClientSession",
            return_value=_make_nikkei225_mock_session(),
        ):
            response = client.post("/api/v1/stock-master/fetch/sample?sample_size=1")

    # 入口確認: ステータスコード
    assert response.status_code == 200, (
        f"Unexpected status code: {response.status_code}\n" f"Response body: {response.text}"
    )

    data = response.json()

    # nikkei225 フィールドの存在確認
    assert "nikkei225" in data, f"nikkei225 field missing in response: {data}"

    n225 = data["nikkei225"]
    assert isinstance(n225, dict), f"nikkei225 should be a dict: {n225}"
    assert "success" in n225, f"nikkei225.success missing: {n225}"
    assert "count" in n225, f"nikkei225.count missing: {n225}"
    assert "error" in n225, f"nikkei225.error missing: {n225}"

    # 日経225 更新が成功していること（モックデータで 1 件保存）
    assert n225["success"] is True, f"nikkei225 update failed: {n225}"
    assert n225["count"] > 0, f"nikkei225 count should be > 0: {n225}"

    # artifact 出力
    write_json_artifact(data, name="test_fetch_and_save_nikkei225_result")


# ---------------------------------------------------------------------------
# テスト 2: nikkei225_components テーブルへの永続化確認
# ---------------------------------------------------------------------------


def test_nikkei225_components_saved_to_db():
    """Nikkei225ComponentsService.fetch_and_update() 後、nikkei225_components に保存されること.

    手順:
    1. nikkei225_components テーブルをクリーンアップ（事前状態を明確化）
    2. requests.get をモックして CSV データを返す
    3. Nikkei225ComponentsService.fetch_and_update() を実行（実テーブルへ書き込み）
    4. サービス返り値で success=True, count>0 を確認（入口）
    5. nikkei225_components テーブルに 1 行以上存在することを確認（出口: DB 永続化確認）
    6. artifact を出力
    """
    from app.models.market_data.nikkei225 import Nikkei225Component

    # 事前: nikkei225_components テーブルをクリーンアップ
    cleanup_table(Nikkei225Component)

    # HTTP モックを適用してサービスを実行（実 SQLite DB への書き込み）
    with patch(
        "aiohttp.ClientSession",
        return_value=_make_nikkei225_mock_session(),
    ):
        result = run_async_safely(_run_nikkei225_fetch_and_update())

    # 入口確認: サービス返り値
    assert result.get("success") is True, f"fetch_and_update() returned failure: {result}"
    assert result.get("count", 0) > 0, f"No records reported as saved: {result}"

    # 出口確認: 実テーブルへの永続化
    assert verify_table_has_data(Nikkei225Component), (
        "nikkei225_components テーブルにデータが格納されていない — " "DB への永続化が確認できない"
    )

    # artifact 出力（デバッグ支援）
    try:
        rows = run_async_safely(_fetch_nikkei225_components_rows())
        if rows:
            write_csv_artifact(rows, name="test_nikkei225_components_saved_to_db")
            assert_artifact_written("test_nikkei225_components_saved_to_db")
        write_json_artifact(result, name="test_nikkei225_fetch_and_update_result")
    except Exception as e:
        import traceback

        raise AssertionError(f"Artifact 出力に失敗: {e}\n{traceback.format_exc()}") from e
