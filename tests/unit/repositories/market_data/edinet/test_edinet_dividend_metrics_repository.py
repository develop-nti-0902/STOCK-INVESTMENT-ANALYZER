"""Tests for EdinetDividendMetricsRepository presence of core methods."""

import inspect

from app.repositories.market_data.edinet import EdinetDividendMetricsRepository


def test_repository_has_core_methods():
    """主要なメソッドがリポジトリに存在することを確認する。"""
    assert inspect.isclass(EdinetDividendMetricsRepository)
    for meth in ("upsert", "save_batch", "find_latest_by_edinet_document_id"):
        assert hasattr(EdinetDividendMetricsRepository, meth)
