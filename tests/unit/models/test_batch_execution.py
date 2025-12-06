from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_batch_execution_model_defaults_and_persistence():
    """BatchExecution モデルがテーブル作成、デフォルト値、永続化をサポートすることを確認する。"""
    # in-memory SQLite を使用して軽量にテスト（Postgres 固有型を使っていないため互換）
    engine = create_engine("sqlite:///:memory:", future=True)

    # 遅延 import：テスト実行環境で app モジュールが正しく読み込まれることを期待
    from app.models import Base, BatchExecution  # noqa: E402

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    be = BatchExecution(
        batch_type="all_stocks",
        status="running",
        total_stocks=0,
    )
    session.add(be)
    session.commit()
    session.refresh(be)

    # PK がセットされている
    assert be.id is not None

    # 集計カラムはデフォルト/指定値
    assert be.total_stocks == 0
    assert be.processed_stocks == 0
    assert be.successful_stocks == 0
    assert be.failed_stocks == 0

    # 日時系のカラムが設定されている
    assert be.start_time is not None
    assert be.created_at is not None

    session.close()
