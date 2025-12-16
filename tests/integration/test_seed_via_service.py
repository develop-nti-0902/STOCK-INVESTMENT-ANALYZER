import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.models.base import Base
from app.models.stock_master import StockMaster
from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master.service import StockMasterService
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.mark.anyio
async def test_fetch_and_store_integration(monkeypatch):
    """
    統合テスト: `StockMasterService.fetch_and_store` がフェッチャーからの取得、
    正規化、リポジトリを通じた永続化まで正しく実行されることを検証する。

    前提:
    - `app.utils.database.get_database_url()` がテスト用Postgresの接続文字列を返すこと
    - テストは実ネットワーク（JPXサイト）へアクセスし、DBへ書き込みを行うため
      テスト用の分離された環境で実行すること
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

        await conn.execute(delete(StockMaster))

    # Arrange（準備）:
    # モックを使わずにエンドツーエンドで実行する（JPXからダウンロード → 正規化 → 永続化）

    # Act（実行）: まずフェッチャーで期待データ件数を取得
    from app.services.market_data.stock_master.fetcher import (
        StockMasterFetcher,
    )

    fetcher = StockMasterFetcher()
    expected_data = await fetcher.fetch_all()
    expected_count = len(expected_data)

    # Assert（事前検証）: JPXから何かしらのデータが取得できていること
    assert expected_count > 0, "JPX data should be fetched"

    # Act（実行）: セッションを作成してサービスを実行（スクリプト動作を模倣）
    session_maker = db_mod.get_session_maker()
    async with session_maker() as session:
        repo = StockMasterRepository(session=session)
        # 上で取得した `fetcher` インスタンスを再利用します。
        # これによりサービスが同一データセットで動作し、JPXへ二度アクセスして
        # データが変化することによるテストの不安定さ（期待件数とDBの差分）を防ぎます。
        service = StockMasterService(repo=repo, fetcher=fetcher)

        # bulk_upsert に自動 commit を追加したため、ここでの明示的な
        # commit は不要になりました。
        processed = await service.fetch_and_store(source="jpx", batch_size=2)

        # Assert（検証）: 処理件数がJPXから取得したデータ件数と一致すること
        processed_msg = (
            f"Expected {expected_count} records to be processed, "
            f"but got {processed}"
        )
        assert processed == expected_count, processed_msg

    # Assert（検証）: 新しいセッションで永続化が完了していることを確認する
    async with session_maker() as verify_session:
        result = await verify_session.execute(select(StockMaster))
        rows = result.scalars().all()

        # 永続化された行数がJPXから取得したデータ件数と一致すること
        rows_msg = (
            f"Expected {expected_count} rows in DB, " f"but got {len(rows)}"
        )
        assert len(rows) == expected_count, rows_msg

        # 生産物: 全件ダンプを CSV で出力（tests/integration/artifacts/ に保存）
        import csv
        import os
        from datetime import datetime, timezone

        artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(artifacts_dir, f"stock_master_dump_{ts}.csv")

        fieldnames = [
            "id",
            "stock_code",
            "stock_name",
            "market_category",
            "sector_code_33",
            "sector_name_33",
            "sector_code_17",
            "sector_name_17",
            "scale_code",
            "scale_category",
            "data_date",
            "is_active",
        ]

        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    writer.writerow(
                        {
                            "id": getattr(r, "id", None),
                            "stock_code": getattr(r, "stock_code", None),
                            "stock_name": getattr(r, "stock_name", None),
                            "market_category": getattr(
                                r, "market_category", None
                            ),
                            "sector_code_33": getattr(
                                r, "sector_code_33", None
                            ),
                            "sector_name_33": getattr(
                                r, "sector_name_33", None
                            ),
                            "sector_code_17": getattr(
                                r, "sector_code_17", None
                            ),
                            "sector_name_17": getattr(
                                r, "sector_name_17", None
                            ),
                            "scale_code": getattr(r, "scale_code", None),
                            "scale_category": getattr(
                                r, "scale_category", None
                            ),
                            "data_date": getattr(r, "data_date", None),
                            "is_active": getattr(r, "is_active", None),
                        }
                    )
            logger.info("Wrote full dump to %s", out_path)
        except Exception as e:  # pragma: no cover - artifact write
            logger.error("Failed to write artifact: %s", e)

    # Cleanup: drop tables (best-effort)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    except Exception:
        # テーブル削除失敗は無視（テスト自体は成功している）
        pass
