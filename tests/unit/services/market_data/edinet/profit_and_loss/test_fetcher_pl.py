"""fetcher の単体テスト（profit_and_loss 固有）。"""

from __future__ import annotations

from app.services.market_data.edinet.download_service import EdinetDownloadService


def test_download_service_available():
    svc = EdinetDownloadService()
    assert svc is not None
