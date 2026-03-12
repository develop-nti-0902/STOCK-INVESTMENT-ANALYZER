"""Unit tests for BaseViewService utilities."""

from app.services.data_synchronization.views.base import BaseViewService


def test_base_view_service_logger():
    """BaseViewService に logger 属性が存在することを確認する."""
    s = BaseViewService()
    assert hasattr(s, "logger")
