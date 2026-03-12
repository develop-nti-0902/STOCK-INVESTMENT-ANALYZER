"""サービス層のユニットテストパッケージ."""


class TestBaseFetcher:
    """`BaseFetcher` のインポート確認テスト."""

    def test_imports(self):
        """BaseFetcher がインポート可能であることを確認します."""
        from app.services.data_synchronization._core.fetchers import BaseFetcher

        assert BaseFetcher is not None


class TestBaseSaver:
    """`BaseSaver` のインポート確認テスト."""

    def test_imports(self):
        """BaseSaver がインポート可能であることを確認します."""
        from app.services.data_synchronization._core.savers import BaseSaver

        assert BaseSaver is not None


class TestBaseValidator:
    """`BaseValidator` のインポート確認テスト."""

    def test_imports(self):
        """BaseValidator がインポート可能であることを確認します."""
        from app.services.data_synchronization._core.validators import BaseValidator

        assert BaseValidator is not None


class TestBaseConverter:
    """`BaseConverter` のインポート確認テスト."""

    def test_imports(self):
        """BaseConverter がインポート可能であることを確認します."""
        from app.services.data_synchronization._core.converters import BaseConverter

        assert BaseConverter is not None


class TestDecorators:
    """デコレータのインポート確認テスト."""

    def test_imports(self):
        """デコレータがインポート可能であることを確認します."""
        from app.services.core.decorators import handle_service_error, retry_on_error

        assert handle_service_error is not None
        assert retry_on_error is not None
