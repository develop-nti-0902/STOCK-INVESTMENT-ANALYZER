"""Unit tests for profit_and_loss fetcher utilities."""

from __future__ import annotations

from app.services.market_data.edinet.download_service import EdinetDownloadService


def test_download_service_available():
    """Instantiate `EdinetDownloadService` successfully."""
    svc = EdinetDownloadService()
    assert svc is not None
