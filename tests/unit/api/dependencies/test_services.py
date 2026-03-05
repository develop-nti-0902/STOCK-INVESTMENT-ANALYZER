"""単体テスト - Service依存性注入プロバイダ."""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import (
    get_screening_service,
    get_stock_master_repository,
    get_stock_master_service,
)
from app.repositories.market_data.stock_master import StockMasterRepository
from app.services.data_synchronization.market_data.stock_master import StockMasterService
from app.services.screening.screening_service import ScreeningService


class TestGetStockMasterRepository:
    """Verify get_stock_master_repository behavior."""

    def test_get_stock_master_repository_returns_repository_instance(self, mock_db_session):
        """Verify StockMasterRepository instance is returned."""
        # Arrange & Act
        repository = get_stock_master_repository(db=mock_db_session)

        # Assert
        assert isinstance(repository, StockMasterRepository)
        assert repository.session == mock_db_session

    def test_get_stock_master_repo_different_sessions_create_different_repos(
        self,
    ):
        """Verify different sessions produce distinct Repository instances."""
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
    """Verify get_stock_master_service behavior."""

    def test_get_stock_master_service_returns_service_instance(self, mock_db_session):
        """Verify StockMasterService instance is returned."""
        # Arrange & Act
        service = get_stock_master_service(repo=get_stock_master_repository(db=mock_db_session))

        # Assert
        assert isinstance(service, StockMasterService)
        assert isinstance(service.repo, StockMasterRepository)
        assert service.repo.session == mock_db_session

    def test_get_stock_master_svc_different_repos_create_different_services(
        self,
    ):
        """Verify different repositories produce distinct Service instances."""
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


class TestGetScreeningService:
    """Verify get_screening_service behavior."""

    def test_get_screening_service_returns_service_from_app_state(self):
        """Verify ScreeningService is retrieved from app.state."""
        # Arrange
        mock_service = MagicMock(spec=ScreeningService)
        mock_request = MagicMock()
        mock_request.app.state.screening_service = mock_service

        # Act
        result = get_screening_service(request=mock_request)

        # Assert
        assert result is mock_service

    def test_get_screening_service_raises_when_not_initialized(self):
        """Verify RuntimeError is raised when ScreeningService is not initialized."""
        # Arrange
        mock_request = MagicMock()
        mock_request.app.state.screening_service = None

        # Act & Assert
        try:
            get_screening_service(request=mock_request)
            assert False, "Expected RuntimeError to be raised"
        except RuntimeError as e:
            assert "ScreeningService not initialized" in str(e)
