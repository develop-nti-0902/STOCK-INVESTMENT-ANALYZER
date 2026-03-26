"""E2E tests for Nikkei225 fetch flow."""

# flake8: noqa

import pytest

from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_table,
    run_async_safely,
    verify_table_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


async def _fetch_nikkei225_1d_rows():
    """nikkei225_1d テーブルの全行を取得してJSON化するヘルパー."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.nikkei225 import Nikkei2251d
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Nikkei2251d))
            rows = result.scalars().all()
            cols = [c.name for c in Nikkei2251d.__table__.columns]
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


def test_nikkei225_fetch_api_returns_200(client):
    """API: POST /api/v1/nikkei225/fetch が 200 を返すこと.

    手順:
    1. POST /api/v1/nikkei225/fetch を max_period=5 で呼び出し
    2. ステータスコード 200 を確認（入口）
    3. レスポンス構造を確認（success フィールドが存在すること）
    """
    payload = {"max_period": 5}
    response = client.post("/api/v1/nikkei225/fetch", json=payload)

    # 入口: ステータスコード確認
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    result = response.json()
    assert isinstance(result, dict), "Response should be a dictionary"
    assert "success" in result, "Response must have 'success' field"
    assert "records_fetched" in result, "Response must have 'records_fetched' field"
    assert "records_saved" in result, "Response must have 'records_saved' field"
    assert "errors" in result, "Response must have 'errors' field"
    assert "elapsed_time" in result, "Response must have 'elapsed_time' field"


def test_nikkei225_fetch_saves_to_db(client):
    """DB: POST /api/v1/nikkei225/fetch 後、nikkei225_1d テーブルに保存されること.

    手順:
    1. nikkei225_1d をクリーンアップ（事前状態を明確にする）
    2. POST /api/v1/nikkei225/fetch を max_period=5 で呼び出し
    3. レスポンス確認（入口）
    4. DB検証（出口） - テーブルに1行以上存在すること
    5. artifact を出力（デバッグ支援）
    """
    from app.models.market_data.nikkei225 import Nikkei2251d

    # 事前: nikkei225_1d をクリーンアップ
    cleanup_table(Nikkei2251d)

    # バッチAPIを呼び出し
    payload = {"max_period": 5}
    response = client.post("/api/v1/nikkei225/fetch", json=payload)

    # 入口: レスポンス確認
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    result = response.json()
    assert result.get("success") is True, f"fetch_and_save returned failure: {result}"

    # 出口: DB 確認
    assert verify_table_has_data(Nikkei2251d), "nikkei225_1d テーブルにデータが格納されていない"

    # artifact 出力（必須）
    rows = run_async_safely(_fetch_nikkei225_1d_rows())
    assert rows, "No nikkei225_1d data to write artifact"
    name = "test_nikkei225_fetch_saves_to_db_nikkei225_1d_artifact"
    write_csv_artifact(rows, name=name)
    assert_artifact_written(name)


def test_nikkei225_fetch_max_period_none(client):
    """API: max_period を省略した場合も 200 を返すこと.

    手順:
    1. POST /api/v1/nikkei225/fetch を空ボディで呼び出し（max_period=None）
    2. ステータスコード 200 を確認（入口）

    Note:
    全データ取得は時間がかかるため、レスポンス構造確認のみ。DBへの格納確認は省略。
    """
    response = client.post("/api/v1/nikkei225/fetch", json={})

    # 入口: ステータスコード確認のみ
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    result = response.json()
    assert isinstance(result.get("records_fetched"), int), "records_fetched must be int"
