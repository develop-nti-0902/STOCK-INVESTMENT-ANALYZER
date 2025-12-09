"""
BaseRepositoryの単体テスト

BaseRepositoryの汎用CRUD操作をテストする。
非同期セッションのモックを使用し、実際のDBに依存しないテストを実施する。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository


class MockModel:
    """テスト用のモデルクラス"""

    # BaseRepository がクラス属性へアクセスするため、クラスレベルに id を定義する
    id: int = 0

    def __init__(self, **kwargs):
        self.id: int = kwargs.get("id", 0)
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConcreteRepository(BaseRepository[MockModel]):
    """テスト用の具体的なRepository実装"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.model = MockModel

    async def get(self, record_id: int):
        """SQLAlchemyのselectをモック化したget"""
        result: Result = await self.session.execute(MagicMock())
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100):
        """SQLAlchemyのselectをモック化したget_multi"""
        result: Result = await self.session.execute(MagicMock())
        return list(result.scalars().all())

    async def count(self) -> int:
        """SQLAlchemyのselectをモック化したcount"""
        result: Result = await self.session.execute(MagicMock())
        return result.scalar_one()


class TestBaseRepository:
    """BaseRepositoryの単体テスト"""

    @pytest.fixture
    def mock_session(self):
        """非同期セッションのモックを作成"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """ConcreteRepositoryのインスタンスを作成"""
        return ConcreteRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        """新規レコード作成のテスト"""
        # Arrange
        test_data = {"id": 1, "name": "Test"}
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        result = await repository.create(test_data)

        # Assert
        assert isinstance(result, MockModel)
        assert result.id == 1
        assert result.name == "Test"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_rollback_on_error(self, repository, mock_session):
        """create で例外が発生したら rollback されることを確認"""
        mock_session.flush = AsyncMock(side_effect=SQLAlchemyError("boom"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(SQLAlchemyError):
            await repository.create({"id": 1})

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        """ID検索（レコードが見つかる場合）のテスト"""
        # Arrange
        expected_model = MockModel(id=1, name="Test")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected_model
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.get(1)

        # Assert
        assert result == expected_model
        assert result.id == 1
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """ID検索（レコードが見つからない場合）のテスト"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.get(999)

        # Assert
        assert result is None
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_all(self, repository, mock_session):
        """全件取得のテスト"""
        # Arrange
        models = [
            MockModel(id=1, name="Test1"),
            MockModel(id=2, name="Test2"),
            MockModel(id=3, name="Test3"),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = models
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.get_multi(skip=0, limit=10)

        # Assert
        assert len(result) == 3
        assert all(isinstance(model, MockModel) for model in result)
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_found(self, repository, mock_session):
        """レコード更新（レコードが見つかる場合）のテスト"""
        # Arrange
        existing_model = MockModel(id=1, name="Old Name")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        result = await repository.update(1, {"name": "New Name"})

        # Assert
        assert result is not None
        assert result.name == "New Name"
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self, repository, mock_session):
        """レコード更新（レコードが見つからない場合）のテスト"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.update(999, {"name": "New Name"})

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_rollback_on_error(self, repository, mock_session):
        """update が失敗した場合に rollback されることを確認"""
        existing_model = MockModel(id=1, name="Old Name")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock(side_effect=SQLAlchemyError("boom"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(SQLAlchemyError):
            await repository.update(1, {"name": "X"})

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_found(self, repository, mock_session):
        """レコード削除（レコードが見つかる場合）のテスト"""
        # Arrange
        existing_model = MockModel(id=1, name="Test")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # Act
        result = await repository.delete(1)

        # Assert
        assert result is True
        mock_session.delete.assert_awaited_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_rollback_on_error(self, repository, mock_session):
        """delete が失敗した場合に rollback されることを確認"""
        existing_model = MockModel(id=1, name="Test")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_model
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock(side_effect=SQLAlchemyError("boom"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(SQLAlchemyError):
            await repository.delete(1)

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """レコード削除（レコードが見つからない場合）のテスト"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.delete(999)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_bulk_create(self, repository, mock_session):
        """一括作成のテスト"""
        # 準備
        records = [
            {"id": 1, "name": "Test1"},
            {"id": 2, "name": "Test2"},
            {"id": 3, "name": "Test3"},
        ]
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        # 実行
        result = await repository.bulk_create(records)

        # 検証
        assert len(result) == 3
        assert all(isinstance(model, MockModel) for model in result)
        mock_session.add_all.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_create_rollback(self, repository, mock_session):
        """bulk_create で失敗した場合に rollback されることを確認"""
        records = [{"id": 1}, {"id": 2}]
        mock_session.flush = AsyncMock(side_effect=SQLAlchemyError("boom"))
        mock_session.rollback = AsyncMock()

        with pytest.raises(SQLAlchemyError):
            await repository.bulk_create(records)

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_all(self, repository, mock_session):
        """全件数取得のテスト"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 42
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository.count()

        # Assert
        assert result == 42
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exists_true_false(self, repository, mock_session):
        """exists が True/False を返すことを確認"""
        # BaseRepository.exists はモジュールレベルの select() を使用し、
        # SQLAlchemy のマップ済みクラスを期待します。
        # 型変換（coercion）エラーを回避するため select を差し替えます。
        import app.repositories.base as base_module

        original_select = base_module.select

        class DummyStmt:
            def where(self, *a, **k):
                return self

        base_module.select = lambda *a, **k: DummyStmt()

        try:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MockModel(id=1)
            mock_session.execute = AsyncMock(return_value=mock_result)

            assert await repository.exists(1) is True

            mock_result.scalar_one_or_none.return_value = None
            assert await repository.exists(999) is False
        finally:
            base_module.select = original_select


class RealRepository(BaseRepository[MockModel]):
    """Baseクラス実装そのままを使うリポジトリ（テスト用）"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.model = MockModel


class TestBaseRepositoryImplementation:
    """BaseRepository 実装そのままの振る舞いをテスト"""

    @pytest.fixture
    def repository_real(self):
        session = AsyncMock(spec=AsyncSession)

        # モデルが SQLAlchemy にマップされていないため、module-level の
        # select をテスト用ダミーに差し替える。テスト終了後に復元する。
        import app.repositories.base as base_module

        original_select = base_module.select

        class DummyStmt:
            def where(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            def offset(self, *a, **k):
                return self

            def select_from(self, *a, **k):
                return self

        base_module.select = lambda *a, **k: DummyStmt()

        repo = RealRepository(session)
        try:
            yield repo
        finally:
            base_module.select = original_select

    @pytest.mark.asyncio
    async def test_base_get_by_id_found(self, repository_real):
        """Base実装の get_by_id が期待通り返すことを確認"""
        # Arrange
        expected = MockModel(id=10, name="Real")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = expected
        repository_real.session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository_real.get(10)

        # Assert
        assert result is expected
        repository_real.session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_base_get_all_with_limit_offset(self, repository_real):
        """Base実装の get_all が scalars().all を返すことを確認"""
        # Arrange
        models = [
            MockModel(id=1, name="A"),
            MockModel(id=2, name="B"),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = models
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        repository_real.session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository_real.get_multi(skip=1, limit=2)

        # Assert
        assert result == models
        repository_real.session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_skips_nonexistent_attributes(self, repository_real):
        """update が存在しない属性を無視することを確認"""
        # Arrange
        existing = MockModel(id=5, name="Old")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        repository_real.session.execute = AsyncMock(return_value=mock_result)
        repository_real.session.flush = AsyncMock()

        # Act
        result = await repository_real.update(
            5, {"name": "New", "does_not_exist": "X"}
        )

        # Assert
        assert result is not None
        assert result.name == "New"
        assert not hasattr(result, "does_not_exist")
        repository_real.session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self, repository_real):
        """空リストの bulk_create が空を返すことを確認"""
        # Arrange
        repository_real.session.add_all = MagicMock()
        repository_real.session.flush = AsyncMock()

        # Act
        result = await repository_real.bulk_create([])

        # Assert
        assert result == []
        repository_real.session.add_all.assert_called_once_with([])
        repository_real.session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count_all_base_impl(self, repository_real):
        """count_all が数値を返すことを確認"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 7
        repository_real.session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository_real.count()

        # Assert
        assert result == 7
        repository_real.session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found_base_impl(self, repository_real):
        """delete で対象が見つからない場合 False を返すことを確認"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repository_real.session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await repository_real.delete(9999)

        # Assert
        assert result is False
