"""単体テスト - データベース接続管理."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@pytest.fixture
def mock_settings():
    """モック設定を提供するフィクスチャ."""
    mock = MagicMock()
    # Provide a full DATABASE_URL for tests (SQLite)
    mock.DATABASE_URL = "sqlite+aiosqlite:///./test_db.sqlite"
    mock.DEBUG = False
    # Engine pool settings (kept for assertions, but not used for SQLite)
    mock.DB_POOL_SIZE = 5
    mock.DB_MAX_OVERFLOW = 10
    return mock


@pytest.fixture(autouse=True)
def reset_global_state():
    """各テストの前後でグローバル状態をリセットする."""
    import app.utils.database as db_module

    # テスト前: 可能であれば公開APIのキャッシュをクリアして初期状態にする
    try:
        db_module.get_engine.cache_clear()
    except Exception:
        pass

    yield

    # テスト後: 再度キャッシュをクリアして後始末
    try:
        db_module.get_engine.cache_clear()
    except Exception:
        pass


class TestGetDatabaseUrl:
    """get_database_url関数のテスト."""

    def test_get_database_url_returns_correct_format(self, mock_settings):
        """データベース接続URLが正しい形式で返されることを検証."""
        # Arrange
        with patch("app.utils.database.get_settings", return_value=mock_settings):
            from app.utils.database import get_database_url

            # Act
            url = get_database_url()

            # Assert
            assert url == mock_settings.DATABASE_URL


class TestCreateEngine:
    """create_engine関数のテスト."""

    def test_create_engine_returns_async_engine(self, mock_settings):
        """非同期エンジンが正しく作成されることを検証."""
        # Arrange
        with patch("app.utils.database.get_settings", return_value=mock_settings), patch(
            "app.utils.database.create_async_engine"
        ) as mock_create_async_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_async_engine.return_value = mock_engine

            from app.utils.database import create_engine

            # Act
            result_engine = create_engine()

            # Assert
            assert result_engine == mock_engine
            mock_create_async_engine.assert_called_once()

            # 引数の検証
            call_args = mock_create_async_engine.call_args
            assert "echo" in call_args[1]
            assert call_args[1]["echo"] is False  # DEBUG=False
            # SQLiteではpool_size/max_overflowは設定されない
            assert "pool_size" not in call_args[1]
            assert "max_overflow" not in call_args[1]
            assert call_args[1]["pool_pre_ping"] is True
            assert call_args[1]["pool_recycle"] == 3600

    def test_create_engine_with_debug_mode(self, mock_settings):
        """DEBUG=Trueの場合、echoオプションが有効になることを検証."""
        # Arrange
        mock_settings.DEBUG = True

        with patch("app.utils.database.get_settings", return_value=mock_settings), patch(
            "app.utils.database.create_async_engine"
        ) as mock_create_async_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_async_engine.return_value = mock_engine

            from app.utils.database import create_engine

            # Act
            _ = create_engine()

            # Assert
            call_args = mock_create_async_engine.call_args
            assert call_args[1]["echo"] is True  # DEBUG=True

    def test_create_engine_respects_pool_settings_from_env(self):
        """環境変数のプール設定がengine作成引数に反映されることを検証（PostgreSQL用）."""
        # Arrange - PostgreSQLのURLを使用してpool設定をテスト
        local_settings = MagicMock()
        local_settings.DB_POOL_SIZE = 20
        local_settings.DB_MAX_OVERFLOW = 40
        local_settings.DEBUG = False
        local_settings.DB_USER = "u"
        local_settings.DB_PASSWORD = "p"
        local_settings.DB_HOST = "h"
        local_settings.DB_PORT = 5432
        local_settings.DB_NAME = "n"
        # PostgreSQL URLを使用（pool設定が有効になる）
        local_settings.DATABASE_URL = "postgresql+asyncpg://u:p@h:5432/n"

        with patch("app.utils.database.get_settings", return_value=local_settings), patch(
            "app.utils.database.create_async_engine"
        ) as mock_create_async_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_async_engine.return_value = mock_engine

            from app.utils.database import create_engine

            # Act
            _ = create_engine()

            # Assert - PostgreSQLの場合はpool設定が含まれる
            call_kwargs = mock_create_async_engine.call_args[1]
            assert call_kwargs["pool_size"] == 20
            assert call_kwargs["max_overflow"] == 40


class TestGetEngine:
    """get_engine関数のテスト（シングルトンパターン）."""

    def test_get_engine_creates_engine_on_first_call(self, mock_settings):
        """初回呼び出し時にエンジンが作成されることを検証."""
        # Arrange
        with patch("app.utils.database.get_settings", return_value=mock_settings), patch(
            "app.utils.database.create_async_engine"
        ) as mock_create_async_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_async_engine.return_value = mock_engine

            from app.utils.database import get_engine

            # Act
            engine = get_engine()

            # Assert
            assert engine == mock_engine
            mock_create_async_engine.assert_called_once()

    def test_get_engine_returns_same_instance_on_subsequent_calls(self, mock_settings):
        """2回目以降の呼び出しでは同じインスタンスが返されることを検証."""
        # Arrange
        with patch("app.utils.database.get_settings", return_value=mock_settings), patch(
            "app.utils.database.create_async_engine"
        ) as mock_create_async_engine:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create_async_engine.return_value = mock_engine

            from app.utils.database import get_engine

            # Act
            engine1 = get_engine()
            engine2 = get_engine()

            # Assert
            assert engine1 is engine2  # 同じインスタンスであることを確認
            mock_create_async_engine.assert_called_once()  # 1回だけ呼ばれる


class TestGetSessionMaker:
    """get_session_maker関数のテスト."""

    @pytest.mark.asyncio
    async def test_async_sessionmaker_used_in_get_db(self, mock_settings):
        """`get_db` が内部で `async_sessionmaker` を使用して session_maker を作ることを検証."""
        mock_engine = MagicMock(spec=AsyncEngine)

        # モックの session とコンテキストマネージャを準備
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_session
        mock_context.__aexit__.return_value = None

        mock_session_maker = MagicMock(return_value=mock_context)

        with patch("app.utils.database.get_engine", return_value=mock_engine), patch(
            "app.utils.database.async_sessionmaker", return_value=mock_session_maker
        ) as mock_async_sessionmaker:
            from app.utils.database import get_db

            gen = get_db()
            # 実際にジェネレータを進めて body を実行し、async_sessionmaker 呼び出しを検証
            session = await gen.__anext__()
            assert session == mock_session
            mock_async_sessionmaker.assert_called_once()
            call_args = mock_async_sessionmaker.call_args[1]
            assert call_args["bind"] == mock_engine
            assert call_args["class_"] == AsyncSession
            assert call_args["autocommit"] is False
            assert call_args["autoflush"] is False
            assert call_args["expire_on_commit"] is False
            await gen.aclose()


@pytest.mark.asyncio
class TestGetDb:
    """get_db関数のテスト（非同期ジェネレータ）."""

    async def test_get_db_yields_session_and_commits(self, mock_settings):
        """正常系: セッションが生成され、コミットされることを検証."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__.return_value = mock_session

        with patch(
            "app.utils.database.async_sessionmaker",
            return_value=mock_session_maker,
        ):
            from app.utils.database import get_db

            # Act
            async for session in get_db():
                assert session == mock_session

            # Assert
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()

    async def test_get_db_rolls_back_on_exception(self, mock_settings):
        """異常系: 例外発生時にロールバックされることを検証."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)

        # async_sessionmaker()がasync withで使えるようにモック設定
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_session
        mock_context_manager.__aexit__.return_value = None

        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_context_manager

        with patch(
            "app.utils.database.async_sessionmaker",
            return_value=mock_session_maker,
        ):
            from app.utils.database import get_db

            # Act & Assert
            gen = get_db()
            try:
                session = await gen.__anext__()
                assert session == mock_session
                # セッション内で例外を発生させる
                await gen.athrow(RuntimeError("Test error"))
            except RuntimeError:
                pass  # 例外を捕捉

            # ロールバックが呼ばれることを検証
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


@pytest.mark.asyncio
class TestCloseDb:
    """close_db関数のテスト."""

    async def test_close_db_disposes_engine(self, mock_settings):
        """エンジンが正しくdisposeされることを検証."""
        # Arrange
        mock_engine = AsyncMock(spec=AsyncEngine)

        with patch("app.utils.database.get_settings", return_value=mock_settings), patch(
            "app.utils.database.create_async_engine", return_value=mock_engine
        ):
            from app.utils.database import close_db, get_engine

            # エンジンを取得してグローバル変数に設定
            get_engine()

            # Act
            await close_db()

            # Assert
            mock_engine.dispose.assert_called_once()

    async def test_close_db_does_nothing_when_no_engine(self, mock_settings):
        """エンジンが存在しない場合、何もしないことを検証."""
        # Arrange
        with patch("app.utils.database.get_settings", return_value=mock_settings):
            from app.utils.database import close_db

            # Act & Assert (例外が発生しないことを確認)
            await close_db()
