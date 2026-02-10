"""バッチ実行詳細モデルの単体テスト.

`BatchExecutionDetails` が `BatchExecution` と連携して永続化できることを検証します.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_batch_execution_details_fk_and_fields():
    """BatchExecutionDetails と BatchExecution の関連付けを検証します."""
    engine = create_engine("sqlite:///:memory:", future=True)

    # 遅延 import
    from app.models import Base, BatchExecution, BatchExecutionDetails  # noqa: E402

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # まず親レコードを作成
    be = BatchExecution(batch_type="test", status="running", total_stocks=1)
    session.add(be)
    session.commit()
    session.refresh(be)

    # 子レコードを作成して関連性を確認（interval単位の集計）
    detail = BatchExecutionDetails(
        batch_execution_id=be.id,
        interval="1d",
        total_stocks=1,
        processed_stocks=1,
        successful_stocks=1,
        failed_stocks=0,
        status="completed",
    )
    session.add(detail)
    session.commit()
    session.refresh(detail)

    assert detail.id is not None
    assert detail.batch_execution_id == be.id
    assert detail.interval == "1d"
    assert detail.status == "completed"
    assert detail.processed_stocks == 1

    # relationship 経由で親を参照できること
    assert detail.batch_execution is not None
    assert detail.batch_execution.id == be.id

    session.close()
