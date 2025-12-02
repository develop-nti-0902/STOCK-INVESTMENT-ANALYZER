"""
単体テスト - Repository依存性注入プロバイダ

app.api.dependencies.repositories モジュールの単体テストを実施する。
FastAPIのDependsパターンによるRepository提供の動作を検証する。
"""

from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.repositories import get_base_repository
from app.repositories.base import BaseRepository

# このファイルでは共通の `tests/conftest.py` に定義された
# `mock_db_session` フィクスチャを利用します。ローカル定義は削除しました。


class TestGetBaseRepository:
    """get_base_repository関数のテスト"""

    def test_get_base_repository_returns_repository_instance(
        self, mock_db_session
    ):
        """BaseRepositoryインスタンスが正しく返されることを検証"""
        # Arrange & Act
        repository = get_base_repository(db=mock_db_session)

        # Assert
        assert isinstance(repository, BaseRepository)
        assert repository.session == mock_db_session

    def test_get_base_repository_different_sessions_create_different_repos(
        self,
    ):
        """異なるセッションで異なるRepositoryインスタンスが作成されることを検証"""
        # Arrange
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        # Act
        repo1 = get_base_repository(db=mock_session1)
        repo2 = get_base_repository(db=mock_session2)

        # Assert
        assert repo1 is not repo2
        assert repo1.session == mock_session1
        assert repo2.session == mock_session2


# 将来的な拡張: 各エンティティ専用のRepositoryプロバイダのテスト
# 例: test_get_stock_repository, test_get_master_repository 等
# これらは、各Repositoryクラスの実装後に追加する
