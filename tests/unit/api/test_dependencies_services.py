"""
単体テスト - Service依存性注入プロバイダ

app.api.dependencies.services モジュールの単体テストを実施する。
FastAPIのDependsパターンによるService提供の動作を検証する。
"""

from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import (
    get_stock_master_repository,
    get_stock_master_service,
)
from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master import StockMasterService


class TestGetStockMasterRepository:
    """get_stock_master_repository関数のテスト"""

    def test_get_stock_master_repository_returns_repository_instance(
        self, mock_db_session
    ):
        """StockMasterRepositoryインスタンスが正しく返されることを検証"""
        # Arrange & Act
        repository = get_stock_master_repository(db=mock_db_session)

        # Assert
        assert isinstance(repository, StockMasterRepository)
        assert repository.session == mock_db_session

    def test_get_stock_master_repo_different_sessions_create_different_repos(
        self,
    ):
        """異なるセッションで異なるRepositoryインスタンスが作成されることを検証"""
        # Arrange
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        # Act
        repo1 = get_stock_master_repository(db=mock_session1)
        repo2 = get_stock_master_repository(db=mock_session2)

        # Assert
        assert repo1 is not repo2
        assert repo1.session == mock_session1
        assert repo2.session == mock_session2


class TestGetStockMasterService:
    """get_stock_master_service関数のテスト"""

    def test_get_stock_master_service_returns_service_instance(
        self, mock_db_session
    ):
        """StockMasterServiceインスタンスが正しく返されることを検証"""
        # Arrange & Act
        service = get_stock_master_service(
            repo=get_stock_master_repository(db=mock_db_session)
        )

        # Assert
        assert isinstance(service, StockMasterService)
        assert isinstance(service.repo, StockMasterRepository)
        assert service.repo.session == mock_db_session

    def test_get_stock_master_svc_different_repos_create_different_services(
        self,
    ):
        """異なるRepositoryで異なるServiceインスタンスが作成されることを検証"""
        # Arrange
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        repo1 = get_stock_master_repository(db=mock_session1)
        repo2 = get_stock_master_repository(db=mock_session2)

        # Act
        service1 = get_stock_master_service(repo=repo1)
        service2 = get_stock_master_service(repo=repo2)

        # Assert
        assert service1 is not service2
        assert service1.repo == repo1
        assert service2.repo == repo2
        assert service1.repo.session == mock_session1
        assert service2.repo.session == mock_session2
