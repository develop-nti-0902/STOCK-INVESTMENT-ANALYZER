"""DividendYieldMonitoringRepository の基本構成を検証するテスト。"""

from types import SimpleNamespace

from app.models.monitoring.dividend_yield_monitoring import DividendYieldMonitoring
from app.repositories.monitoring.dividend_yield_monitoring_repository import (
    DividendYieldMonitoringRepository,
)


class DummySession(SimpleNamespace):
    """DBセッションを模したプレースホルダー。"""

    pass


def test_repository_binds_model() -> None:
    """リポジトリが正しいモデルをバインドしていることを確認する。"""
    session = DummySession()
    repo = DividendYieldMonitoringRepository(session=session)  # type: ignore[arg-type]
    assert repo.model is DividendYieldMonitoring
