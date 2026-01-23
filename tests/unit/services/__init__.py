"""サービス層のユニットテストパッケージ。"""


class TestBaseFetcher:
    """BaseFetcherの単体テスト"""

    def test_imports(self):
        """BaseFetcherがインポート可能であることを確認"""
        from app.services.core.fetchers import BaseFetcher

        assert BaseFetcher is not None


class TestBaseSaver:
    """BaseSaverの単体テスト"""

    def test_imports(self):
        """BaseSaverがインポート可能であることを確認"""
        from app.services.core.savers import BaseSaver

        assert BaseSaver is not None


class TestBaseValidator:
    """BaseValidatorの単体テスト"""

    def test_imports(self):
        """BaseValidatorがインポート可能であることを確認"""
        from app.services.core.validators import BaseValidator

        assert BaseValidator is not None


class TestBaseConverter:
    """BaseConverterの単体テスト"""

    def test_imports(self):
        """BaseConverterがインポート可能であることを確認"""
        from app.services.core.converters import BaseConverter

        assert BaseConverter is not None


class TestDecorators:
    """デコレータのテスト"""

    def test_imports(self):
        """デコレータがインポート可能であることを確認"""
        from app.services.core.decorators import (
            handle_service_error,
            retry_on_error,
        )

        assert handle_service_error is not None
        assert retry_on_error is not None
